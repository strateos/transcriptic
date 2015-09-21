import sys
import json
from os.path import expanduser, isfile
import locale
import ap2en
import click
import requests
from collections import OrderedDict
import zipfile
import os
import time
import xml.etree.ElementTree as ET
import re
from collections import OrderedDict


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
        self.default_headers = {
            'X-User-Email': self.email,
            'X-User-Token': self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            }


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
        default_headers = self.default_headers
        default_headers.update(kwargs.pop('headers', {}))
        return requests.post(self.url(path), headers=default_headers, **kwargs)


    def get(self, path, **kwargs):
        default_headers = self.default_headers
        default_headers.update(kwargs.pop('headers', {}))
        return requests.get(self.url(path), headers=default_headers, **kwargs)


    def delete(self, path, **kwargs):
        default_headers = self.default_headers
        default_headers.update(kwargs.pop('headers', {}))
        return requests.delete(self.url(path), headers=default_headers, **kwargs)


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
    project = get_project_id(project)
    if not project:
        return

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
@click.argument('package', required=False)
@click.option('--name', '-n', help="Optional name for your zip file")
@click.pass_context
def release(ctx, name=None, package=None):
    '''Compress the contents of the current directory to upload as a release'''
    deflated = zipfile.ZIP_DEFLATED
    def makezip(d, archive):
        for (path, dirs, files) in os.walk(d):
            for f in files:
                if ".zip" not in f:
                    archive.write(os.path.join(path, f))
        return archive

    with open('manifest.json', 'rU') as manifest:
        filename = 'release_v%s' %json.load(manifest)['version'] or name
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
    click.echo("Compressing all files in this directory...")
    zf = zipfile.ZipFile(filename + ".zip", 'w', deflated)
    archive = makezip('.', zf)
    zf.close()
    click.echo("Archive %s created." % (filename + ".zip"))
    if package:
        package_id = get_package_id(package) or get_package_name(package)
        ctx.invoke(upl, archive=(filename + ".zip"), package=package_id)


@cli.command("upload")
@click.argument('archive', required=True, type=click.Path(exists=True))
@click.argument('package', required=True)
@click.pass_context
def upl(ctx, archive, package):
    """Upload an existing archive to an existing package"""
    try:
        package_id = get_package_id(package.lower()) or get_package_name(package.lower())
        click.echo("Uploading %s to %s" % (archive,
                                           (get_package_name(package_id.lower()) or
                                            get_package_id(package_id.lower()))))
    except AttributeError:
        click.echo("Error: Invalid package id or name.")
        return

    with click.progressbar(None, 100, "Upload Progress",
                            show_eta = False, width=70,
                            fill_char = "|", empty_char= "-") as bar:
        bar.update(10)
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
        bar.update(30)
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
        bar.update(20)
        response_tree = ET.fromstring(response.content)
        loc = dict((i.tag, i.text) for i in response_tree)
        try:
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
        except ValueError:
            click.echo("\nError: There was a problem uploading your release. \nVerify"
                       " that your manifest.json file is properly formatted and"
                       " that all previews in your manifest produce valid "
                       "Autoprotocol by using the `transcriptic preview` "
                       "and/or `transcriptic analyze` commands.")
            return
        bar.update(20)
        time.sleep(10)
        status = ctx.obj.get('/packages/%s/releases/%s?_=%s' % (package_id, re,
                                                                int(time.time())))
        published = json.loads(status.content)['published']
        errors = status.json()['validation_errors']
        bar.update(30)
        if errors:
            click.echo("\nPackage upload to %s unsuccessful. "
                       "The following error was "
                       "returned: %s" %
                       (get_package_name(package_id),
                        (',').join(e.get('message', '[Unknown]') for
                                   e in errors)))
        else:
            click.echo("\nPackage uploaded successfully! \n"
                       "Visit %s to publish." % ctx.obj.url('packages/%s' %
                                                             package_id))

@cli.command()
@click.pass_context
@click.option("-i")
def packages(ctx, i):
    '''List packages in your organizaiton'''
    response = ctx.obj.get('/packages/')
    # there's probably a better way to do this
    package_names = OrderedDict(sorted({"yours": {}, "theirs": {}}.items(), key=lambda t: len(t[0])))

    if response.status_code == 200:
        for pack in response.json():
            if pack.get('owner'):
                if pack['owner']['email'] == ctx.obj.email:
                    package_names['yours'][str(pack['name']).lower().replace("com.%s." % ctx.obj.organization, "")] = str(pack['id'])
            else:
                package_names['theirs'][str(pack['name']).lower().replace("com.%s." % ctx.obj.organization, "")] = str(pack['id'])
    if i:
        return dict(package_names['yours'].items() + package_names['theirs'].items())
    else:
        for category, packages in package_names.items():
            if category == "yours":
                click.echo('\n{:^80}'.format("YOUR PACKAGES:"))
            else:
                click.echo('\n{:^80}'.format("OTHER PACKAGES IN YOUR ORG:"))
            click.echo('{:^40}'.format("PACKAGE NAME") + "|" +
                       '{:^40}'.format("PACKAGE ID"))
            click.echo('{:-^80}'.format(''))
            for name, id in packages.items():
                click.echo('{:<40}'.format(name) + "|" +
                           '{:^40}'.format(id))
                click.echo('{:-^80}'.format(''))

@cli.command("new-package")
@click.argument('name')
@click.argument('description')
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
                                               "name": "%s%s" % ("com.%s." % ctx.obj.organization, name)
                                              }))
    if new_pack.status_code == 201:
        click.echo("New package %s created with id %s \n"
                   "View it at %s" % (name, new_pack.json()['id'],
                                       ctx.obj.url('packages/%s' %
                                                    new_pack.json()['id'])))
    else:
        click.echo("There was an error creating this package.")


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
            return {k.lower(): v for k,v in proj_names.items()}
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


@cli.command("new-project")
@click.argument('name')
@click.option('dev', '-d', help="Create a pilot project", is_flag=True)
@click.pass_context
def new_project(ctx, name, dev):
    '''Create a new empty project'''
    existing = ctx.obj.get('')
    for p in existing.json()['projects']:
        if name == p['name'].split('.')[-1]:
            click.echo("You already have an existing project with the name \"%s\"."
                       "  Please choose a different project name." % name)
            return
    proj_data = {"name": name}
    if dev:
        proj_data["is_developer"] = True
    new_proj = ctx.obj.post('', data= json.dumps(proj_data))
    if new_proj.status_code == 201:
        click.echo("New%s project '%s' created with id %s  \nView it at %s" %
                    (" pilot" if dev else "", name, new_proj.json()['id'],
                    ctx.obj.url('%s' % (new_proj.json()['id']))))
    else:
        click.echo("There was an error creating this package.")


@cli.command("delete-project")
@click.argument('name')
@click.option('force', '-f', help="force delete a project without being prompted if you're sure", is_flag=True)
@click.pass_context
def delete_project(ctx, name, force):
    '''Delete an existing package'''
    id = get_project_id(name)
    if id:
        if not force:
            click.confirm("Are you sure you want to permanently delete '%s'?" % get_project_name(id),
                          default=False,
                          abort=True)
        dele = ctx.obj.delete('%s' % id, data=json.dumps({"id": id}))

        click.echo("Project deleted.")



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
@click.argument('file', default='-')
@click.pass_context
def summarize(ctx, file):
    with click.open_file(file, 'r') as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo("The autoprotocol you're trying to summarize is invalid.")
            return
    ap2en.AutoprotocolParser(protocol)


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
        click.echo("Error logging into Transcriptic: %s" % r.json()['error'])
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
    id = projs.get(name.lower())
    if not id:
        id = name if name in projs.values() else None
        if not id:
            click.echo("A project with the name '%s' was not found in your "
                       "organization." % name)
            return
    return id


@click.pass_context
def get_project_name(ctx, id):
    projs = {v:k for k,v in ctx.invoke(projects, i=True).items()}
    name = projs.get(id)
    if not name:
        name = id if name in projs.keys() else None
        if not name:
            click.echo("A project with the id '%s' was not found in your "
                       "organization." % name)
            return
    return name


@click.pass_context
def get_package_id(ctx, name):
    package_names = ctx.invoke(packages, i=True)
    package_names = {k.lower(): v for k,v in package_names.items()}
    package_id = package_names.get(name)
    if not package_id:
        package_id = name if name in package_names.values() else None
    if not package_id and __name__ == "__main__":
        click.echo("The package %s does not exist in your organization." % name)
        return
    return package_id


@click.pass_context
def get_package_name(ctx, id):
    package_names = {v: k for k, v in ctx.invoke(packages, i=True).items()}
    package_name = package_names.get(id)
    if not package_name:
        package_name = id if id in package_names.values() else None
    if not package_name and __name__ == "__main__":
        click.echo("The id %s does not match any package in your organization."
                   % id)
        return
    return package_name


def parse_json(json_file):
    try:
        return json.load(open(json_file))
    except ValueError as e:
        click.echo('Invalid json: %s' % e)
        return None


def get_protocol_list(json_file):
    manifest = parse_json(json_file)
    protocol_list = [p['name'] for p in manifest['protocols']]
    return protocol_list


def pull(nested_dict):
    if "type" in nested_dict and "inputs" not in nested_dict:
        return nested_dict
    else:
        inputs = {}
        if "type" in nested_dict and "inputs" in nested_dict:
            for param, input in nested_dict["inputs"].items():
                inputs[str(param)] = pull(input)
            return inputs
        else:
            return nested_dict


def regex_manifest(protocol, input):
    '''Special input types, gets updated as more input types are added'''
    if "type" in input and input["type"] == "choice":
        if "options" in input:
            pattern = '\[(.*?)\]'
            match = re.search(pattern, str(input["options"]))
            if not match:
                click.echo("Error in %s: input type \"choice\" options must be in the "
                           "form of: \n[\n  {\n  \"value\": <choice value>, \n  \"label\": "
                           "<choice label>\n  },\n  ...\n]" % protocol['name'])
                raise RuntimeError
        else:
            click.echo("Must have options for 'choice' input type." +
                               " Error in: " + protocol["name"])
            raise RuntimeError


def iter_json(manifest):
    all_types = {}
    try:
        protocol = manifest['protocols']
    except TypeError:
        click.echo("Error: Your manifest.json file doesn't contain valid JSON and"
                   " cannot be formatted.")
        raise RuntimeError
    for protocol in manifest["protocols"]:
        types = {}
        for param, input in protocol["inputs"].items():
            types[param] = pull(input)
            if isinstance(input, dict):
                if input["type"] == "group" or input["type"] == "group+":
                    for i, j in input.items():
                        if isinstance(j, dict):
                            for k, l in j.items():
                                regex_manifest(protocol, l)
                else:
                    regex_manifest(protocol, input)
        all_types[protocol["name"]] = types
    return all_types


@cli.command()
@click.argument('manifest', default='manifest.json')
def format(manifest):
    '''Check autoprotocol format of manifest.json'''
    manifest = parse_json(manifest)
    try:
        iter_json(manifest)
        click.echo("No manifest formatting errors found.")
    except RuntimeError:
        pass
