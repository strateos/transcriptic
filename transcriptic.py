import sys
import json
from os.path import expanduser
import locale

import click
import requests


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
        kwargs['headers'] = \
            dict(default_headers.items() + kwargs.get('headers', {}).items())
        return requests.post(self.url(path), **kwargs)

    def get(self, path, **kwargs):
        default_headers = {
            'X-User-Email': self.email,
            'X-User-Token': self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            }
        kwargs['headers'] = \
            dict(default_headers.items() + kwargs.get('headers', {}).items())
        return requests.get(self.url(path), **kwargs)


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
              required=True, help='Project to submit the run to')
@click.option('--title', '-t', help='Optional title of your run')
@click.option('--test', help='Submit this run in test mode', is_flag=True)
@click.pass_context
def submit(ctx, file, project, title, test):
    '''Submit your run to the project specified'''
    with click.open_file(file, 'r') as f:
        protocol = json.loads(f.read())
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
        click.echo("Couldn't create run (404). Are you sure the project %s "
                   "exists, and that you have access to it?" %
                   ctx.obj.url(project))
    elif response.status_code == 422:
        click.echo("Error creating run: %s" % response.text)
    else:
        click.echo("Unknown error: %s" % response.text)

@cli.command()
@click.pass_context
def projects(ctx):
    '''List the projects in your organization'''
    response = ctx.obj.get('')
    if response.status_code == 200:
        click.echo('{:^35}'.format("PROJECT NAME") + "|" +
                   '{:^35}'.format("PROJECT ID"))
        click.echo('{:-^70}'.format(''))
        for proj in response.json()['projects']:
            click.echo('{:<35}'.format(proj['name']) + "|" +
                       '{:^35}'.format(proj['url']))
            click.echo('{:-^70}'.format(''))

@cli.command()
@click.argument('file', default='-')
@click.option('--test', help='Analyze this run in test mode', is_flag=True)
@click.pass_context
def analyze(ctx, file, test):
    '''Analyze your run'''
    with click.open_file(file, 'r') as f:
        protocol = json.loads(f.read())
    response = \
        ctx.obj.post(
            'analyze_run',
            data=json.dumps({"protocol": protocol, "test_mode": test})
        )
    if response.status_code == 200:
        click.echo(u"\u2713 Protocol analyzed")

        def count(thing, things, num):
            click.echo("  %s %s" % (num, thing if num == 1 else things))
        result = response.json()
        count("instruction", "instructions", len(result['instructions']))
        count("container", "containers", len(result['refs']))
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        click.echo("  %s" %
                   locale.currency(float(result['total_cost']), grouping=True))
        for w in result['warnings']:
            message = w['message']
            if 'instruction' in w['context']:
                context = "instruction %s" % w['context']['instruction']
            else:
                context = json.dumps(w['context'])
            click.echo("WARNING (%s): %s" % (context, message))
    elif response.status_code == 422:
        click.echo("Error in protocol: %s" % response.text)
    else:
        click.echo("Unknown error: %s" % response.text)


@cli.command()
@click.argument('protocol_name')
def preview(protocol_name):
    '''Preview the Autoprotocol output of a run (without submitting or analyzing)'''
    with click.open_file('manifest.json', 'r') as f:
        manifest = json.loads(f.read())
    p = next(p for p in manifest['protocols'] if p['name'] == protocol_name)
    command = p['command_string']
    from subprocess import call
    import tempfile
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(json.dumps(p['preview']))
        fp.flush()
        call(["bash", "-c", command + " " + fp.name])


@cli.command()
@click.argument('protocol_name')
@click.argument('args', nargs=-1)
def run(protocol_name, args):
    '''Run a protocol by passing it a config file (without submitting or analyzing)'''
    with click.open_file('manifest.json', 'r') as f:
        manifest = json.loads(f.read())
    p = next(p for p in manifest['protocols'] if p['name'] == protocol_name)
    command = p['command_string']
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
        click.echo("You don't appear to belong to any organizations. Visit %s "
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
