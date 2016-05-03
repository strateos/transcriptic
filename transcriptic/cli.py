#!/usr/bin/env python

from __future__ import print_function
from builtins import bytes
from builtins import object
from builtins import next
from builtins import str

import click
import json
import locale
import os
import time
import sys
import xml.etree.ElementTree as ET
import zipfile

from transcriptic.english import AutoprotocolParser
from transcriptic.config import Connection
from transcriptic.objects import ProtocolPreview
from transcriptic.util import iter_json
from transcriptic import routes
from os.path import isfile
from collections import OrderedDict
from contextlib import contextmanager

# Workaround to support the correct input for both Python 2 and 3. Always use
# input() which will point to the correct builtin.
try:
    input = raw_input
except NameError:
    pass


class ContextObject(object):
    """Object passed along Click context"""
    def __init__(self):
        self._api = None

    @property
    def api(self):
        return self._api

    @api.setter
    def api(self, value):
        self._api = value


@click.group()
@click.option('--apiroot', default=None)
@click.option(
    '--config',
    envvar='TRANSCRIPTIC_CONFIG',
    default='~/.transcriptic',
    help='Specify a configuration file.'
)
@click.option('--organization', '-o', default=None)
@click.version_option(prog_name="Transcriptic Python Library (TxPy)")
@click.pass_context
def cli(ctx, apiroot, config, organization):
    """A command line tool for working with Transcriptic."""
    if ctx.invoked_subcommand in ['login']:
        # Initialize empty connection
        ctx.obj = ContextObject()
        ctx.obj.api = Connection(use_environ=False)
    elif ctx.invoked_subcommand not in ['compile', 'preview', 'summarize', 'init']:
        try:
            ctx.obj = ContextObject()
            ctx.obj.api = Connection.from_file(config)
            if organization is not None:
                ctx.obj.api.organization_id = organization
            if apiroot is not None:
                ctx.obj.api.api_root = apiroot
        except IOError:
            click.echo("Error reading config file, running "
                       "`transcriptic login` ...")
            ctx.invoke(login)


@cli.command()
@click.argument('file', default='-')
@click.option(
    '--project', '-p',
    metavar='PROJECT_ID',
    required=True,
    help=('Project id or name to submit the run to. '
          'Use `transcriptic projects` command to list existing projects.')
)
@click.option('--title', '-t', help='Optional title of your run')
@click.option('--test', help='Submit this run in test mode', is_flag=True)
@click.pass_context
def submit(ctx, file, project, title, test):
    """Submit your run to the project specified."""
    project = get_project_id(project)
    if not project:
        return
    with click.open_file(file, 'r') as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo("Error: Could not submit since your manifest.json "
                       "file is improperly formatted.")
            return

    try:
        req_json = ctx.obj.api.submit_run(protocol, project_id=project, title=title, test_mode=test)
        run_id = req_json['id']
        click.echo("Run created: %s" %
                   ctx.obj.api.url("%s/runs/%s" % (project, run_id)))
    except Exception as e:
        click.echo(str(e))


@cli.command('build-release')
@click.argument('package', required=False, metavar="PACKAGE")
@click.option('--name', '-n', help="Optional name for your zip file")
@click.pass_context
def release(ctx, name=None, package=None):
    """
    Compress the contents of the current directory to upload as a release.
    """
    deflated = zipfile.ZIP_DEFLATED
    if name:
        filename = 'release_%s' % name
    else:
        filename = 'release'
    if os.path.isfile(filename + ".zip"):
        new = click.prompt("You already have a release named %s "
                           "in this directory, make "
                           "another one? [y/n]" % filename, default="y")
        if new == "y":
            num_existing = sum([1 for x in os.listdir('.') if filename in x])
            filename = filename + "_" + str(num_existing)
        else:
            return
    click.echo("Compressing all files in this directory...")
    zf = zipfile.ZipFile(filename + ".zip", 'w', deflated)
    for (path, dirs, files) in os.walk('.'):
        for f in files:
            if ".zip" not in f:
                zf.write(os.path.join(path, f))
    zf.close()
    click.echo("Archive %s created." % (filename + ".zip"))
    if package:
        package_id = get_package_id(package) or get_package_name(package)
        ctx.invoke(
            upload_release, archive=(filename + ".zip"), package=package_id)


@cli.command("upload-release")
@click.argument('archive', required=True, type=click.Path(exists=True),
                metavar="ARCHIVE")
@click.argument('package', required=True, metavar="PACKAGE")
@click.pass_context
def upload_release(ctx, archive, package):
    """Upload a release archive to a package."""
    try:
        package_id = get_package_id(
            package.lower()) or get_package_name(package.lower())
        click.echo("Uploading %s to %s" %
                   (archive,
                    (get_package_name(package_id.lower()) or
                     get_package_id(package_id.lower()))
                    )
                   )
    except AttributeError:
        click.echo("Error: Invalid package id or name.")
        return
    with click.progressbar(None, 100, "Upload Progress",
                           show_eta=False, width=70,
                           fill_char="|", empty_char="-") as bar:
        bar.update(10)
        info = ctx.obj.api.get(ctx.obj.api.get_route('upload_sign'), params={'name': archive})
        bar.update(30)
        aws_url = ctx.obj.api.get_route('aws_upload')
        files = {'file': open(os.path.basename(archive), 'rb')}
        data = OrderedDict([
            ('key', info['key']),
            ('AWSAccessKeyId', 'AKIAJVJ67EJYCQXO7ZSQ'),
            ('acl', 'private'),
            ('success_action_status', '201'),
            ('policy', info['policy']),
            ('signature', info['signature']),
        ])
        response = ctx.obj.api.post(aws_url, data=data, files=files, headers={},
                            status_response={'201': lambda resp: resp})
        bar.update(20)
        response_tree = ET.fromstring(response.content)
        loc = dict((i.tag, i.text) for i in response_tree)
        try:
            up = ctx.obj.api.post_release(
                data=json.dumps({"release":
                                {"binary_attachment_url": loc["Key"]}}
                                ),
                package_id=package_id
                )
            re = up['id']
        except ValueError:
            click.echo("\nError: There was a problem uploading your release."
                       "\nVerify that your manifest.json file is properly  "
                       "formatted and that all previews in your manifest "
                       "produce valid Autoprotocol by using the "
                       "`transcriptic preview` and/or `transcriptic analyze` "
                       "commands.")
            return
        bar.update(20)
        time.sleep(10)
        status = ctx.obj.api.get_release_status(package_id=package_id, release_id=re,
                                            timestamp=int(time.time()))
        published = status['published']
        errors = status['validation_errors']
        bar.update(30)
        if errors:
            click.echo("\nPackage upload to %s unsuccessful. "
                       "The following error(s) was returned: \n%s" %
                       (get_package_name(package_id),
                        ('\n').join(e.get('message', '[Unknown]') for
                                    e in errors))
                       )
        else:
            click.echo("\nPackage uploaded successfully! \n"
                       "Visit %s to publish." % ctx.obj.api.url('packages/%s' %
                                                            package_id))


@cli.command()
def protocols():
    """List protocols within your manifest."""

    manifest = load_manifest()
    if 'protocols' not in list(manifest.keys()) or not manifest['protocols']:
        click.echo("Your manifest.json file doesn't contain any protocols or"
                   " is improperly formatted.")
        return
    else:
        click.echo('\n{:^60}'.format("Protocols within this manifest:"))
        click.echo('{:-^60}'.format(''))
        [click.echo("%s%s\n%s" % (p['name'],
                                  (" (" + p.get('display_name') + ")")
                                  if p.get('display_name') else "",
                                  ('{:-^60}'.format(""))))
         for p in manifest["protocols"]]


@cli.command()
@click.pass_context
@click.option("-i")
def packages(ctx, i):
    """List packages in your organization."""
    response = ctx.obj.api.packages()
    # there's probably a better way to do this
    package_names = OrderedDict(
        sorted(list({"yours": {}, "theirs": {}}.items()),
               key=lambda t: len(t[0]))
        )

    for pack in response:
        n = str(pack['name']).lower().replace(
            "com.%s." % ctx.obj.api.organization_id, "")
        latest = str(pack['latest_version']) if pack[
            'latest_version'] else "-"
        if pack.get('owner') and pack['owner']['email'] == ctx.obj.api.email:
            package_names['yours'][n] = {}
            package_names['yours'][n]['id'] = str(pack['id'])
            package_names['yours'][n]['latest'] = latest
        else:
            package_names['theirs'][n] = {}
            package_names['theirs'][n]['id'] = str(pack['id'])
            package_names['theirs'][n]['latest'] = latest
    if i:
        return dict(list(package_names['yours'].items()) +
                    list(package_names['theirs'].items()))
    else:
        for category, packages in list(package_names.items()):
            if category == "yours":
                click.echo('\n{:^90}'.format("YOUR PACKAGES:\n"))
                click.echo('{:^30}'.format("PACKAGE NAME") + "|" +
                           '{:^30}'.format("PACKAGE ID") +
                           "|" + '{:^30}'.format("LATEST PUBLISHED RELEASE"))
                click.echo('{:-^90}'.format(''))
            elif category == "theirs" and list(packages.values()):
                click.echo('\n{:^90}'.format("OTHER PACKAGES IN YOUR ORG:\n"))
                click.echo('{:^30}'.format("PACKAGE NAME") + "|" +
                           '{:^30}'.format("PACKAGE ID") + "|" +
                           '{:^30}'.format("LATEST PUBLISHED RELEASE"))
                click.echo('{:-^90}'.format(''))
            for name, p in list(packages.items()):
                click.echo('{:<30}'.format(name) + "|" +
                           '{:^30}'.format(p['id']) + "|" +
                           '{:^30}'.format(p['latest']))
                click.echo('{:-^90}'.format(''))


@cli.command("create-package")
@click.argument('name')
@click.argument('description')
@click.pass_context
def create_package(ctx, description, name):
    """Create a new empty protocol package"""
    existing = ctx.obj.api.packages()
    for p in existing:
        if name == p['name'].split('.')[-1]:
            click.echo("You already have an existing package with the name "
                       "\"%s\". Please choose a different package name." %
                       name)
            return
    new_pack = ctx.obj.api.create_package(name, description)
    if new_pack:
        click.echo("New package '%s' created with id %s \n"
                   "View it at %s" % (name, new_pack['id'],
                                      ctx.obj.api.url('packages/%s' %
                                                  new_pack['id'])
                                      )
                   )
    else:
        click.echo("There was an error creating this package.")


@cli.command("delete-package")
@click.argument('name')
@click.option('--force', '-f', help="force delete a package without being \
              prompted if you're sure", is_flag=True)
@click.pass_context
def delete_package(ctx, name, force):
    """Delete an existing protocol package"""
    package_id = get_package_id(name)
    if package_id:
        if not force:
            click.confirm(
                "Are you sure you want to permanently delete the package "
                "'%s'?  All releases within will be lost." %
                get_package_name(package_id), default=False, abort=True
            )
            click.confirm("Are you really really sure?", default=True)
        del_pack = ctx.obj.api.delete_package(package_id=package_id)
        if del_pack:
            click.echo("Package deleted.")
        else:
            click.echo("There was a problem deleting this package.")


@cli.command()
@click.pass_context
@click.option("-i")
def projects(ctx, i):
    """List the projects in your organization"""
    try:
        projects = ctx.obj.api.projects()
        proj_names = {}
        all_proj = {}
        for proj in projects:
            status = " (archived)" if proj['archived_at'] else ""
            proj_names[proj["name"]] = proj["id"]
            all_proj[proj["name"] + status] = proj["id"]
        if i:
            return proj_names
        else:
            click.echo('\n{:^80}'.format("PROJECTS:\n"))
            click.echo('{:^40}'.format("PROJECT NAME") + "|" +
                       '{:^40}'.format("PROJECT ID"))
            click.echo('{:-^80}'.format(''))
            for name, i in list(all_proj.items()):
                click.echo('{:<40}'.format(name) + "|" +
                           '{:^40}'.format(i))
                click.echo('{:-^80}'.format(''))
    except RuntimeError:
        click.echo("There was an error listing the projects in your "
                   "organization.  Make sure your login details are correct.")


@cli.command()
@click.pass_context
@click.argument('project_name')
def runs(ctx, project_name):
    """List the runs that exist in a project"""
    project_id = get_project_id(project_name)
    run_list = []
    if project_id:
        req = ctx.obj.api.runs(project_id=project_id)
        if not req:
            click.echo("Project '%s' is empty." % project_name)
            return
        for r in req:
            run_list.append([r['title'] or "(Untitled)",
                             r['id'],
                             r['completed_at'].split("T")[0] if r['completed_at']
                             else r['created_at'].split("T")[0],
                             r['status'].replace("_", " ")])

        click.echo(
            '\n{:^120}'.format("Runs in Project '%s':\n" %
                               get_project_name(project_name))
            )
        click.echo('{:^30}'.format("RUN TITLE") + "|" +
                   '{:^30}'.format("RUN ID") + "|" +
                   '{:^30}'.format("RUN DATE") + "|" +
                   '{:^30}'.format('RUN STATUS'))
        click.echo('{:-^120}'.format(''))
        for run in run_list:
            click.echo('{:^30}'.format(run[0]) + "|" +
                       '{:^30}'.format(run[1]) + "|" +
                       '{:^30}'.format(run[2]) + "|" +
                       '{:^30}'.format(run[3]))
            click.echo('{:-^120}'.format(''))


@cli.command("create-project")
@click.argument('name', metavar="PROJECT_NAME")
@click.option('--dev', '-d', '-pilot', help="Create a pilot project",
              is_flag=True)
@click.pass_context
def create_project(ctx, name, dev):
    """Create a new empty project."""
    existing = ctx.obj.api.projects()
    for p in existing:
        if name == p['name'].split('.')[-1]:
            click.echo("You already have an existing project with the name "
                       "\"%s\".  Please choose a different project name." %
                       name)
            return
    try:
        new_proj = ctx.obj.api.create_project(name)
        click.echo(
            "New%s project '%s' created with id %s  \nView it at %s" % (
                " pilot" if dev else "", name, new_proj['id'], ctx.obj.api.url('%s' % (new_proj['id']))
            )
        )
    except RuntimeError:
        click.echo("There was an error creating this project.")


@cli.command("delete-project")
@click.argument('name', metavar="PROJECT_NAME")
@click.option('--force', '-f', help="force delete a project without being \
              prompted if you're sure", is_flag=True)
@click.pass_context
def delete_project(ctx, name, force):
    """Delete an existing project."""
    project_id = get_project_id(name)
    if project_id:
        if not force:
            click.confirm(
                "Are you sure you want to permanently delete '%s'?" %
                get_project_name(project_id),
                default=False,
                abort=True
            )
        if ctx.obj.api.delete_project(project_id=str(project_id)):
            click.echo("Project deleted.")
        else:
            click.confirm(
                "Could not delete project. This may be because it contains \
                runs. Try archiving it instead?",
                default=False,
                abort=True
            )
            if ctx.obj.api.archive_project(project_id=str(project_id)):
                click.echo("Project archived.")
            else:
                click.echo("Could not archive project!")


@cli.command()
@click.argument('query', default='*')
@click.pass_context
def resources(ctx, query):
    """Search catalog of provisionable resources"""
    req = ctx.obj.api.resources(query)
    if req["results"]:
        click.echo("Results for '%s':" % query)
        click.echo('{:^40}'.format("Resource Name") + '|' +
                   '{:^40}'.format("Vendor") + '|' +
                   '{:^40}'.format("Resource ID"))
        click.echo('{:-^120}'.format(''))
    else:
        click.echo("No results for '%s'." % query)
    for i in req["results"]:
        if i["provisionable"] and not i["reservable"]:
            name = i['name'].encode('ascii', errors='ignore')
            resource_id = i['kit_items'][0]['resource_id']
            click.echo('{:^40}'.format(name) + '|' +
                       '{:^40}'.format(i['vendor']['name'] if 'vendor' in
                                       list(i.keys()) else ''
                                       ) +
                       '|' + '{:^40}'.format(resource_id))
            click.echo('{:-^120}'.format(''))


@cli.command()
@click.argument('path', default='.')
def init(path):
    """Initialize a directory with a manifest.json file."""
    manifest_data = OrderedDict(
        format="python",
        license="MIT",
        protocols=[{
            "name": "SampleProtocol",
            "version": "0.0.1",
            "display_name": "Sample Protocol",
            "description": "This is a protocol.",
            "command_string": "python sample_protocol.py",
            "inputs": {},
            "preview": {"refs": {}, "parameters": {}},
        }]
    )
    try:
        os.makedirs(path)
    except OSError:
        click.echo("Specified directory already exists.")
    if isfile('%s/manifest.json' % path):
        click.confirm("This directory already contains a manifest.json file, "
                      "would you like to overwrite it with an empty one? ",
                      default=False,
                      abort=True)
    with open('%s/manifest.json' % path, 'w+') as f:
        click.echo('Creating empty manifest.json...')
        f.write(json.dumps(dict(manifest_data), indent=2))
        click.echo("manifest.json created")


@cli.command()
@click.argument('file', default='-')
@click.option('--test', help='Analyze this run in test mode', is_flag=True)
@click.pass_context
def analyze(ctx, file, test):
    """Analyze a block of Autoprotocol JSON."""
    with click.open_file(file, 'r') as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo("Error: The Autoprotocol you're trying to analyze is "
                       "not properly formatted. \n"
                       "Check that your manifest.json file is "
                       "valid JSON and/or your script "
                       "doesn't print anything other than pure Autoprotocol "
                       "to standard out.")
            return

    try:
        analysis = ctx.obj.api.analyze_run(protocol, test_mode=test)
        click.echo(u"\u2713 Protocol analyzed")
        price(analysis)
    except Exception as e:
        click.echo(str(e))


def price(response):
    def count(thing, things, num):
        click.echo("  %s %s" % (num, thing if num == 1 else things))
    count("instruction", "instructions", len(response['instructions']))
    count("container", "containers", len(response['refs']))
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    click.echo("  Total Cost: %s" %
               locale.currency(float(response['total_cost']), grouping=True))
    for quote_item in response['quote']['items']:
        click.echo("  %s: %s" % (
            quote_item["title"],
            locale.currency(float(quote_item["cost"]), grouping=True)))
    for w in response['warnings']:
        message = w['message']
        if 'instruction' in w['context']:
            context = "instruction %s" % w['context']['instruction']
        else:
            context = json.dumps(w['context'])
        click.echo("WARNING (%s): %s" % (context, message))


@cli.command()
@click.argument('protocol_name', metavar="PROTOCOL_NAME")
@click.option('--view', is_flag=True)
@click.pass_context
def preview(ctx, protocol_name, view):
    """Preview the Autoprotocol output of protocol in the current package."""
    manifest, protocol = load_manifest_and_protocol(protocol_name)

    try:
        inputs = protocol['preview']
    except KeyError:
        click.echo("Error: The manifest.json you're trying to preview doesn't "
                   "contain a \"preview\" section")
        return

    run_protocol(manifest, protocol, inputs, view)


@cli.command()
@click.argument('file', default='-')
@click.pass_context
def summarize(ctx, file):
    """Summarize Autoprotocol as a list of plain English steps."""
    with click.open_file(file, 'r') as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo(
                "The autoprotocol you're trying to summarize is invalid.")
            return
    AutoprotocolParser(protocol)


@cli.command()
@click.argument('protocol_name', metavar="PROTOCOL_NAME")
@click.argument('args', nargs=-1)
def compile(protocol_name, args):
    """Compile a protocol by passing it a config file (without submitting or
     analyzing)."""
    manifest, protocol = load_manifest_and_protocol(protocol_name)

    try:
        command = protocol['command_string']
    except KeyError:
        click.echo(
            "Error: Your manifest.json file does not have a \"command_string\" \
            key.")
        return
    from subprocess import call
    call(["bash", "-c", command + " " + ' '.join(args)])


@cli.command()
@click.argument('protocol')
@click.option(
    '--project', '-p',
    metavar='PROJECT_ID',
    required=True,
    help='Project id or name context for configuring the protocol. Use \
         `transcriptic projects` command to list existing projects.'
)
@click.option(
    '--save_input',
    metavar='FILE',
    required=False,
    help='Save the protocol input JSON in a file. This is useful for debugging \
         a protocol.'
)
@click.pass_context
def launch(ctx, protocol, project, save_input):
    """Configure and execute your protocol using your web browser to select
     your inputs"""
    project = get_project_id(project)
    if not project:
        return

    manifest, protocol = load_manifest_and_protocol(protocol)

    quick_launch = ctx.obj.api.create_quick_launch(data=json.dumps({"manifest": protocol}), project_id=project)
    quick_launch_mtime = quick_launch["updated_at"]

    format_str = "\nOpening %s"
    url = ctx.obj.api.get_route('get_quick_launch', project_id=project, quick_launch_id=quick_launch["id"])
    print_stderr(format_str % url)

    """
    Open the URL in the webbrowser. We have to temporarily suppress stdout/
    stderr because the webbrowser module dumps some garbage which gets into
    out stdout and corrupts the generated autoprotocol
    """
    import webbrowser

    with stdchannel_redirected(sys.stderr, os.devnull):
        with stdchannel_redirected(sys.stdout, os.devnull):
            webbrowser.open_new_tab(url)

    def on_json_received(protocol_inputs, error):
        if protocol_inputs is not None:
            print("Protocol inputs (%s)" % (protocol_inputs))
        elif error is not None:
            click.echo('Invalid json: %s' % e)
            return None

    # Wait until the quick launch inputs are updated (max 15 minutes)
    count = 1
    while (count <= 180 and quick_launch["inputs"] is None or
           quick_launch_mtime >= quick_launch["updated_at"]):
        sys.stderr.write(
            "\rWaiting for inputs to be configured%s" % ('.' * count))
        sys.stderr.flush()
        time.sleep(5)

        quick_launch = ctx.obj.api.get_quick_launch(project_id=project,
                                                quick_launch_id=quick_launch["id"])
        count += 1

    # Save the protocol input locally if the user specified the save_input
    # option
    if save_input:
        try:
            with click.open_file(save_input, 'w') as f:
                f.write(json.dumps(quick_launch["inputs"], indent=2))
        except Exception as e:
            print_stderr("\nUnable to save inputs: %s" % str(e))

    print_stderr("\nGenerating Autoprotocol....\n")
    run_protocol(manifest, protocol, quick_launch["inputs"])


@cli.command()
@click.option('--api-root', default='https://secure.transcriptic.com')
@click.pass_context
def login(ctx, api_root):
    """Authenticate to your Transcriptic account."""
    email = click.prompt('Email')
    password = click.prompt('Password', hide_input=True)
    r = ctx.obj.api.post(routes.login(api_root=api_root), data=json.dumps({
        'user': {
            'email': email,
            'password': password,
        },
    }), headers={
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }, status_response = {
        '200': lambda resp: resp,
        'default': lambda resp: resp
    },
     custom_request=False)
    if r.status_code != 200:
        click.echo("Error logging into Transcriptic: %s" % r.json()['error'])
        sys.exit(1)
    user = r.json()
    token = (user.get('authentication_token') or
             user['test_mode_authentication_token'])
    if len(user['organizations']) < 1:
        click.echo("Error: You don't appear to belong to any organizations. \n"
                   "Visit %s and create an organization." % api_root)
        sys.exit(1)
    if len(user['organizations']) == 1:
        organization = user['organizations'][0]['subdomain']
    else:
        click.echo("You belong to %s organizations:" %
                   len(user['organizations']))
        for indx, o in enumerate(user['organizations']):
            click.echo("%s.  %s (%s)" % (indx+1, o['name'], o['subdomain']))

        def parse_valid_org(indx):
            try:
                return user['organizations'][int(indx)-1]['subdomain']
            except:
                click.echo("Please enter an integer between 1 and %s" %
                           (len(user['organizations'])))
                sys.exit(1)

        organization = click.prompt(
            'Which organization would you like to login as',
            default=1,
            prompt_suffix='? ', type=int,
            value_proc=lambda x: parse_valid_org(x)
        )

    r = ctx.obj.api.get(routes.get_organizations(api_root=api_root, org_id=organization), headers={
        'X-User-Email': email,
        'X-User-Token': token,
        'Accept': 'application/json',
    }, status_response={
        '200': lambda resp: resp,
        'default': lambda resp: resp
    },
        custom_request=True)
    if r.status_code != 200:
        click.echo("Error accessing organization: %s" % r.text)
        sys.exit(1)
    ctx.obj.api = Connection(email=email, token=token, organization_id=organization, api_root=api_root)
    ctx.obj.api.save(ctx.parent.params['config'])
    click.echo('Logged in as %s (%s)' % (user['email'], organization))


@click.pass_context
def get_project_id(ctx, name):
    projs = ctx.invoke(projects, i=True)
    project_id = projs.get(name)
    if not project_id:
        project_id = name if name in list(projs.values()) else None
        if not project_id:
            click.echo(
                "The project '%s' was not found in your organization." % name)
            return
    return project_id


@click.pass_context
def get_project_name(ctx, id):
    projs = {v: k for k, v in list(ctx.invoke(projects, i=True).items())}
    name = projs.get(id)
    if not name:
        name = id if name in list(projs.keys()) else None
        if not name:
            click.echo(
                "The project '%s' was not found in your organization." % name)
            return
    return name


@click.pass_context
def get_package_id(ctx, name):
    package_names = ctx.invoke(packages, i=True)
    package_names = {k.lower(): v['id']
                     for k, v in list(package_names.items())}
    package_id = package_names.get(name)
    if not package_id:
        package_id = name if name in list(package_names.values()) else None
    if not package_id:
        click.echo(
            "The package '%s' does not exist in your organization." % name)
        return
    return package_id


@click.pass_context
def get_package_name(ctx, package_id):
    package_names = {
        v['id']: k for k, v in list(ctx.invoke(packages, i=True).items())}
    package_name = package_names.get(package_id)
    if not package_name:
        package_name = package_id if package_id in list(package_names.values()) else None
    if not package_name:
        click.echo("The id '%s' does not match any package in your \
                    organization." % package_id)
        return
    return package_name


def load_manifest():
    try:
        with click.open_file('manifest.json', 'r') as f:
            manifest = json.loads(f.read(), object_pairs_hook=OrderedDict)
    except IOError:
        click.echo(
            "The current directory does not contain a manifest.json file.")
        sys.exit(1)
    except ValueError:
        click.echo("Error: Your manifest.json file is improperly formatted. "
                   "Please double check your brackets and commas!")
        sys.exit(1)
    return manifest


def load_protocol(manifest, protocol_name):
    try:
        p = next(
            p for p in manifest['protocols'] if p['name'] == protocol_name)
    except KeyError:
        click.echo(
            "Error: Your manifest.json file does not have a \"protocols\" \
             key.")
        sys.exit(1)
    except StopIteration:
        click.echo("Error: The protocol name '%s' does not match any "
                   "protocols that can be previewed from within this "
                   "directory.  \nCheck either your protocol's spelling or "
                   "your manifest.json file "
                   "and try again." % protocol_name)
        sys.exit(1)
    return p


@click.pass_context
def load_manifest_and_protocol(ctx, protocol_name):
    manifest = load_manifest()
    protocol = load_protocol(manifest, protocol_name)
    return (manifest, protocol)


@click.pass_context
def run_protocol(ctx, manifest, protocol, inputs, view=False):
    try:
        command = protocol['command_string']
    except KeyError:
        click.echo(
            "Error: Your manifest.json file does not have a \"command_string\" \
             key.")
        return

    from subprocess import check_output, CalledProcessError
    import tempfile
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(bytes(json.dumps(inputs), 'UTF-8'))
        fp.flush()
        try:
            protocol = check_output(["bash", "-c", command + " " + fp.name])
            click.echo(protocol)
            if view:
                click.echo("View your protocol's raw JSON above or see the "
                           "instructions rendered at the following link: \n%s" %
                           ProtocolPreview(protocol, ctx.obj.api).preview_url)
        except CalledProcessError as e:
            click.echo(e.output)
            return


@cli.command()
@click.argument('manifest', default='manifest.json')
def format(manifest):
    """Check Autoprotocol format of manifest.json."""
    manifest = parse_json(manifest)
    try:
        iter_json(manifest)
        click.echo("No manifest formatting errors found.")
    except RuntimeError:
        pass


def parse_json(json_file):
    try:
        return json.load(open(json_file))
    except ValueError as e:
        click.echo('Invalid json: %s' % e)
        return None


def print_stderr(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


@contextmanager
def stdchannel_redirected(stdchannel, dest_filename):
    """
    A context manager to temporarily redirect stdout or stderr

    e.g.:


    with stdchannel_redirected(sys.stderr, os.devnull):
        if compiler.has_function('clock_gettime', libraries=['rt']):
            libraries.append('rt')
    """
    try:
        oldstdchannel = os.dup(stdchannel.fileno())
        dest_file = open(dest_filename, 'w')
        os.dup2(dest_file.fileno(), stdchannel.fileno())

        yield
    finally:
        if oldstdchannel is not None:
            os.dup2(oldstdchannel, stdchannel.fileno())
        if dest_file is not None:
            dest_file.close()
