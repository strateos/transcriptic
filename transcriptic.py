import sys
import json
from os.path import expanduser, isfile
import locale
import click
import requests
from collections import OrderedDict
import zipfile
import os
import time
import xml.etree.ElementTree as ET

# Workaround to support the correct input for both Python 2 and 3. Always use
# input() which will point to the correct builtin.
try:
    input = raw_input
except NameError:
    pass

class Config:
    def __init__(self, api_root, email, token, organization):
        self.api_root = api_root
        self.email = email
        self.token = token
        self.organization = organization

    @staticmethod
    def from_file(path):
        with click.open_file(expanduser(path), 'r') as f:
            cfg = json.loads(f.read())
            return Config(**cfg)

    def save(self, path):
        with click.open_file(expanduser(path), 'w') as f:
            f.write(json.dumps({
                'email': self.email,
                'token': self.token,
                'organization': self.organization,
                'api_root': self.api_root,
                }, indent=2))

    def url(self, path):
        return "%s/%s/%s" % (self.api_root, self.organization, path)

    def post(self, path, **kwargs):
        default_headers = {
            'X-User-Email': self.email,
            'X-User-Token': self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            }
        default_headers.update(kwargs.pop('headers', {}))
        return requests.post(self.url(path), headers=default_headers, **kwargs)

    def get(self, path, **kwargs):
        default_headers = {
            'X-User-Email': self.email,
            'X-User-Token': self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            }
        default_headers.update(kwargs.pop('headers', {}))
        return requests.get(self.url(path), headers=default_headers, **kwargs)


@click.group()
@click.option('--apiroot', default=None)
@click.option('--config',
              envvar='TRANSCRIPTIC_CONFIG',
              default='~/.transcriptic',
              help='Specify a configuration file')
@click.option('--organization', '-o', default=None, help='The organization to associate your login with')
@click.pass_context
def cli(ctx, apiroot, config, organization):
    '''A command line tool for submitting protocols to Transcriptic and more'''
    if ctx.invoked_subcommand not in ['login', 'preview', 'run']:
        try:
            ctx.obj = Config.from_file(config)
            if organization is not None:
                ctx.obj.organization = organization
            if apiroot is not None:
                ctx.obj.api_root = apiroot
        except IOError:
            click.echo("Error reading config file, running "
                       "`transcriptic login` ...")
            ctx.invoke(login)

@cli.command()
@click.argument('file', default='-')
@click.option('--project', '-p',
              metavar='PROJECT_ID',
              required=True, help='Project id or name to submit the run to. '
                                   'use transcriptic projects command to list'
                                   ' existing projects.')
@click.option('--title', '-t', help='Optional title of your run')
@click.option('--test', help='Submit this run in test mode', is_flag=True)
@click.pass_context
def submit(ctx, file, project, title, test):
    '''Submit your run to the project specified'''
    project = get_project_id(ctx, project)
    with click.open_file(file, 'r') as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo("Error: Could not submit since your manifest.json file is "
                       "improperly formatted.")
            return
    if test:
        test = True
    response = ctx.obj.post(
        '%s/runs' % project,
        data=json.dumps({
            "title": title,
            "protocol": protocol,
            "test_mode": test
            }))
    if response.status_code == 201:
        click.echo(
            "Run created: %s" %
            ctx.obj.url("%s/runs/%s" % (project, response.json()['id'])))
        return response.json()['id']
    elif response.status_code == 404:
        click.echo("Error: Couldn't create run (404). \nAre you sure the project %s "
                   "exists, and that you have access to it?" %
                   ctx.obj.url(project))
    elif response.status_code == 422:
        click.echo("Error creating run: %s" % response.text)
    else:
        click.echo("Unknown error: %s" % response.text)


@cli.command()
@click.option('--name', '-n', help="Optional name for your zip file")
@click.option('--upload', '-u', help="Upload release to specifid package")
@click.pass_context
def release(ctx, name, upload):
    '''Compress the contents of the current directory to upload as a release'''
    deflated = zipfile.ZIP_DEFLATED
    def makezip(d, archive):
        for (path, dirs, files) in os.walk(d):
            for f in files:
                if ".zip" not in f:
                    archive.write(os.path.join(path, f))
        return archive

    with open('manifest.json', 'rU') as manifest:
        filename = 'release_v%s' %json.load(manifest)['version']
    if os.path.isfile(filename + ".zip"):
        new = click.prompt("You already have a release for this "
                           "version number in this directory, make "
                           "another one? [y/n]",
                     default = "y")
        if new == "y":
            num_existing = sum([1 for x in os.listdir('.') if filename in x])
            filename = filename + "-" + str(num_existing)
        else:
            return
    click.echo("Compressing all files in this directory for upload...")
    zf = zipfile.ZipFile(filename + ".zip", 'w', deflated)
    archive = makezip('.', zf)
    zf.close()
    if upload:
        package_id = get_package_id(ctx, upload)
        ctx.invoke(upl, package=package_id, archive=filename + ".zip")


@cli.command("upload")
@click.argument('archive', required=True, type=click.Path(exists=True))
@click.argument('package', required=True)
@click.pass_context
def upl(ctx, package, archive):
    """Upload an existing archive to an existing package"""
    package_id = get_package_id(ctx, package)
    if package_id:
        sign = requests.get('https://secure.transcriptic.com/upload/sign',
                            params={
                                'name': archive
                            },
                            headers={
                                'X-User-Email': ctx.obj.email,
                                'X-User-Token': ctx.obj.token,
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                            })

        info = json.loads(sign.content)

        url    = 'https://transcriptic-uploads.s3.amazonaws.com'
        files  = {'file': open(os.path.basename(archive), 'rb')}
        data   = OrderedDict([
                ('key', info['key']),
                ('AWSAccessKeyId', 'AKIAJVJ67EJYCQXO7ZSQ'),
                ('acl', 'private'),
                ('success_action_status', '201'),
                ('policy', info['policy']),
                ('signature', info['signature']),
            ])

        response = requests.post(url, data=data, files=files)
        response_tree = ET.fromstring(response.content)
        loc = dict((i.tag, i.text) for i in response_tree)
        up = ctx.obj.post('/packages/%s/releases/' % package_id,
                          data = json.dumps({"release":
                                             {
                                              "binary_attachment_url": loc["Key"]
                                              }
                                            }),
                          headers= {
                            "Origin": "https://secure.transcriptic.com/",
                            "Content-Type": "application/json"
                          })
        re = json.loads(up.content)['id']
        click.echo("Validating package...")
        time.sleep(20)
        status = ctx.obj.get('/packages/%s/releases/%s?_=%s' % (package_id, re,
                                                                int(time.time())))
        published = json.loads(status.content)['published']
        errors = status.json()['validation_errors']
        if errors:
            click.echo("Package upload to %s unsuccessful. "
                       "The following error was "
                       "returned: %s" %
                       (get_package_name(ctx, package_id),
                        (',').join(e.get('message', '[Unknown]') for
                                   e in errors)))
        else:
            click.echo("Package uploaded successfully! \n"
                       "Visit %s to publish." % ctx.obj.url('packages/%s' %
                                                             package_id))
    else:
        return


@cli.command()
@click.pass_context
@click.option("-i")
def packages(ctx, i):
    '''List packages in your organizaiton'''
    response = ctx.obj.get('/packages/')
    package_names = {}
    if response.status_code == 200:
        for pack in response.json():
            package_names[pack['name']] = pack['id']
    if i:
        return package_names
    else:
        click.echo('{:^40}'.format("PACKAGE NAME") + "|" +
                   '{:^40}'.format("PACKAGE ID"))
        click.echo('{:-^80}'.format(''))
        for name, id in package_names.items():
            click.echo('{:<40}'.format(name) + "|" +
                       '{:^40}'.format(id))
            click.echo('{:-^80}'.format(''))

@cli.command("new-package")
@click.option('--description', '-d', required=True, help="A description for your package.")
@click.option('--name', '-n', required=True, help="Title of your package "
                                                  "(no special characters or "
                                                  "spaces allowed).")
@click.pass_context
def new_package(ctx, description, name):
    '''Create a new empty protocol package'''
    existing = ctx.obj.get('/packages/')
    for p in existing.json():
        if name == p['name'].split('.')[-1]:
            click.echo("You already have an existing package with the name \"%s\"."
                       "  Please choose a different package name." % name)
            return
    new_pack = ctx.obj.post('/packages/',
                            data = json.dumps({"description": description,
                                               "name": name
                                              }))
    if new_pack.status_code == 201:
        click.echo("New package %s created with id %s. \n"
                   "View it at %s" % (name, new_pack.json()['id'],
                                       ctx.obj.url('packages/%s' %
                                                    new_pack.json()['id'])))
    else:
        click.echo("There was an error creating this package.")


@click.pass_context
def get_package_id(ctx, name):
    package_names = ctx.invoke(packages, i=True)
    if package_names.get(name):
        package_id = package_names[name]
    elif name in package_names.values():
        package_id = name
    else:
        click.echo("The package %s does not exist in your organization." % name)
        return
    return package_id


@click.pass_context
def get_package_name(ctx, id):
    package_names = ctx.invoke(packages, i=True)
    if package_names.get(id):
        package_name = id
    elif id in package_names.values():
        package_name = [n for n, i in package_names.items() if i == id][0]
    else:
        click.echo("The id you've entered (%s) is invalid." % id)
        return
    return package_name


@cli.command()
@click.pass_context
@click.option("-i")
def projects(ctx, i):
    '''List the projects in your organization'''
    response = ctx.obj.get('')
    proj_names = {}
    if response.status_code == 200:
        for proj in response.json()['projects']:
            proj_names[proj['name']] =  proj['id']
        if i:
            return proj_names
        else:
            click.echo('{:^35}'.format("PROJECT NAME") + "|" +
                       '{:^35}'.format("PROJECT ID"))
            click.echo('{:-^70}'.format(''))
            for name, i in proj_names.items():
                click.echo('{:<35}'.format(name) + "|" +
                           '{:^35}'.format(i))
                click.echo('{:-^70}'.format(''))
    else:
        click.echo("There was an error listing the projects in your "
                   "organization.  Make sure your login details are correct.")



@cli.command()
def init():
    '''Initialize directory with blank manifest.json file'''
    manifest_data = {
        "version": "1.0.0",
        "format": "python",
        "license": "MIT",
        "protocols": [
            {
                "name": "SampleProtocol",
                "description": "This is a protocol.",
                "command_string": "python sample_protocol.py",
                "preview": {
                    "refs":{},
                    "parameters": {}
                },
                "inputs": {},
                "dependencies": []
            }
        ]
    }
    if isfile('manifest.json'):
        click.confirm("This directory already contains a manifest.json file, "
                      "would you like to overwrite it with an empty one? ",
                      default = False,
                      abort = True)
    with open('manifest.json', 'w+') as f:
        click.echo('Creating empty manifest.json...')
        f.write(json.dumps(manifest_data, indent=2))
        click.echo("manifest.json created")


@cli.command()
@click.argument('file', default='-')
@click.option('--test', help='Analyze this run in test mode', is_flag=True)
@click.pass_context
def analyze(ctx, file, test):
    '''Analyze autoprotocol'''
    with click.open_file(file, 'r') as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo("Error: Could not analyze since your manifest.json file is "
                       "improperly formatted.")
            return
    response = \
        ctx.obj.post(
            'analyze_run',
            data=json.dumps({"protocol": protocol, "test_mode": test})
        )
    if response.status_code == 200:
        click.echo(u"\u2713 Protocol analyzed")
        price(response.json())
    elif response.status_code == 422:
        click.echo("Error in protocol: %s" % response.text)
    else:
        click.echo("Unknown error: %s" % response.text)


def price(response):
    def count(thing, things, num):
        click.echo("  %s %s" % (num, thing if num == 1 else things))
    count("instruction", "instructions", len(response['instructions']))
    count("container", "containers", len(response['refs']))
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    click.echo("  %s" %
               locale.currency(float(response['total_cost']), grouping=True))
    for w in response['warnings']:
        message = w['message']
        if 'instruction' in w['context']:
            context = "instruction %s" % w['context']['instruction']
        else:
            context = json.dumps(w['context'])
        click.echo("WARNING (%s): %s" % (context, message))

@cli.command()
@click.argument('protocol_name')
def preview(protocol_name):
    '''Preview the Autoprotocol output of a script'''
    with click.open_file('manifest.json', 'r') as f:
        try:
            manifest = json.loads(f.read())
        except ValueError:
            click.echo("Error: Your manifest.json file is improperly formatted. "
                       "Please double check your brackets and commas!")
            return
    try:
        p = next(p for p in manifest['protocols'] if p['name'] == protocol_name)
    except StopIteration:
        click.echo("Error: The protocol name '%s' does not match any protocols "
                   "that can be previewed from within this directory.  \nCheck "
                   "either your protocol's spelling or your manifest.json file "
                   "and try again." % protocol_name)
        return
    try:
        command = p['command_string']
    except KeyError:
        click.echo("Error: Your manifest.json file does not have a \"command_string\""
                   " key.")
        return
    from subprocess import call
    import tempfile
    with tempfile.NamedTemporaryFile() as fp:
        try:
            fp.write(json.dumps(p['preview']))
        except KeyError:
            click.echo("Error: The manifest.json you're trying to preview doesn't "
                       "contain a \"preview\" section")
            return
        fp.flush()
        call(["bash", "-c", command + " " + fp.name])


@cli.command()
@click.argument('protocol_name')
@click.argument('args', nargs=-1)
def run(protocol_name, args):
    '''Run a protocol by passing it a config file (without submitting or analyzing)'''
    with click.open_file('manifest.json', 'r') as f:
        try:
            manifest = json.loads(f.read())
        except ValueError:
            click.echo("Error: Your manifest.json file is improperly formatted. "
                       "Please double check your brackets and commas!")
            return
    try:
        p = next(p for p in manifest['protocols'] if p['name'] == protocol_name)
    except StopIteration:
        click.echo("Error: The protocol name '%s' does not match any protocols "
                   "that can be previewed from within this directory.  \nCheck "
                   "either your spelling or your manifest.json file and try "
                   "again." % protocol_name)
        return
    try:
        command = p['command_string']
    except KeyError:
        click.echo("Error: Your manifest.json file does not have a \"command_string\""
                   " key.")
        return
    from subprocess import call
    call(["bash", "-c", command + " " + ' '.join(args)])


@cli.command()
@click.option('--api-root', default='https://secure.transcriptic.com')
@click.pass_context
def login(ctx, api_root):
    '''Log in to your Transcriptic account'''
    email = click.prompt('Email')
    password = click.prompt('Password', hide_input=True)
    r = requests.post(
        "%s/users/sign_in" % api_root,
        data=json.dumps({
            'user': {
                'email': email,
                'password': password,
                },
            }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            })
    if r.status_code != 200:
        click.echo("Error logging into Transcriptic: %s" % r.text)
        sys.exit(1)
    user = r.json()
    token = (
        user.get('authentication_token') or
        user['test_mode_authentication_token']
    )

    if len(user['organizations']) < 1:
        click.echo("Error: You don't appear to belong to any organizations. \nVisit %s "
                   "and create an organization." % api_root)
        sys.exit(1)
    if len(user['organizations']) == 1:
        organization = user['organizations'][0]['subdomain']
    else:
        click.echo("You belong to %s organizations:" %
                   len(user['organizations']))
        for o in user['organizations']:
            click.echo("  %s (%s)" % (o['name'], o['subdomain']))
        organization = click.prompt(
            'Which would you like to login as',
            default=user['organizations'][0]['subdomain'],
            prompt_suffix='? ')

    r = requests.get('%s/%s' % (api_root, organization), headers={
        'X-User-Email': email,
        'X-User-Token': token,
        'Accept': 'application/json',
        })
    if r.status_code != 200:
        click.echo("Error accessing organization: %s" % r.text)
        sys.exit(1)
    ctx.obj = Config(api_root, email, token, organization)
    ctx.obj.save(ctx.parent.params['config'])
    click.echo('Logged in as %s (%s)' % (user['email'], organization))


@click.pass_context
def get_project_id(ctx, name):
    projs = ctx.invoke(projects, i=True)
    id = projs.get(name) or name
    if id:
        return id
    else:
        click.echo("A project with the name %s was not found in your "
                   "organization." % name)
        return


@click.pass_context
def get_package_id(ctx, name):
    package_names = ctx.invoke(packages, i=True)
    if package_names.get(name):
        package_id = package_names[name]
    elif name in package_names.values():
        package_id = name
    else:
        click.echo("The package %s does not exist in your organization." % name)
        return
    return package_id


@click.pass_context
def get_package_name(ctx, id):
    package_names = ctx.invoke(packages, i=True)
    if package_names.get(id):
        package_name = id
    elif id in package_names.values():
        package_name = [n for n, i in package_names.items() if i == id][0]
    else:
        click.echo("The id you've entered (%s) is invalid." % id)
        return
    return package_name
