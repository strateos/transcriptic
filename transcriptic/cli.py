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
from transcriptic.util import iter_json, flatmap, ascii_encode
from transcriptic import routes
from os.path import isfile
from collections import OrderedDict
from contextlib import contextmanager

import sys
if sys.version_info[0] < 3:
    input = raw_input
    PermissionError = RuntimeError
    # not exactly identical, but similar enough for this case
    FileNotFoundError= IOError


class FeatureGroup(click.Group):
    """Custom group to handle hiding of commands based on the `feature` tag
    TODO: Deprecate once Click 7 lands and use `hidden` parameter in commands
    """
    def __init__(self, **attrs):
        click.Group.__init__(self, **attrs)

    def format_commands(self, ctx, formatter):
        """Custom formatter to control whether a command is displayed
        Note: This is only called when formatting the help message.
        """
        ctx.obj = ContextObject()
        try:
            ctx.obj.api = Connection.from_file('~/.transcriptic')
        except (FileNotFoundError, OSError):
            # This defaults to feature_groups = []
            ctx.obj.api = Connection()

        rows = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            try:
                if cmd.feature is not None and \
                        cmd.feature in ctx.obj.api.feature_groups:
                    help = cmd.short_help or ''
                    rows.append((subcommand, help))
                else:
                    continue
            except AttributeError:
                help = cmd.short_help or ''
                rows.append((subcommand, help))

        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)


class FeatureCommand(click.Command):
    """Extend off Command to add `feature` attribute
    TODO: Deprecate once Click 7 lands and use `hidden` parameter in commands
    """
    def __init__(self, feature=None, **attrs):
        click.Command.__init__(self, **attrs)
        self.feature = feature


class HiddenOption(click.Option):
    """Monkey patch of click Option to enable hidden options
    TODO: Deprecate once Click 7 lands and use `hidden` option instead
    """
    def __init__(self, *param_decls, **attrs):
        __hidden__ = attrs.pop('hidden', True)
        click.Option.__init__(self, *param_decls, **attrs)
        self.__hidden__ = __hidden__

    def get_help_record(self, ctx):
        """This hijacks the help record so that a hidden option does not show 
        up in the help text
        """
        if self.__hidden__:
            return
        click.Option.get_help_record(self, ctx)


class ContextObject(object):
    """Object passed along Click context
    Note: `ctx` is passed along whenever the @click.pass_context decorator is
    present. This object is referenced using `ctx.obj`
    """
    def __init__(self):
        self._api = None

    @property
    def api(self):
        return self._api

    @api.setter
    def api(self, value):
        self._api = value


_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=_CONTEXT_SETTINGS, cls=FeatureGroup)
@click.option('--api-root', default=None, hidden=True, cls=HiddenOption)
@click.option('--email', default=None, hidden=True, cls=HiddenOption)
@click.option('--token', default=None, hidden=True, cls=HiddenOption)
@click.option('--organization', '-o', default=None, hidden=True, cls=HiddenOption)
@click.option(
    '--config',
    envvar='TRANSCRIPTIC_CONFIG',
    default='~/.transcriptic',
    help='Specify a configuration file.'
)
@click.version_option(prog_name="Transcriptic Python Library (TxPy)")
@click.pass_context
def cli(ctx, api_root, email, token, organization, config):
    """A command line tool for working with Transcriptic.
    
    Note: This is the main entry point of the CLI. If specifying credentials,
    note that the order of preference is: --flag, environment then config file.
    
    Example: `transcriptic --organization "my_org" projects` >> 
    `export USER_ORGANIZATION="my_org"` >> `"organization_id": "my_org" in ~/.transcriptic
    """
    if ctx.invoked_subcommand in ['login', 'compile', 'preview', 'summarize', 'init']:
        # For login/local commands, initialize empty connection
        ctx.obj = ContextObject()
        ctx.obj.api = Connection()
    else:
        try:
            ctx.obj = ContextObject()
            api = Connection.from_file(config)
            api.api_root = (
                api_root or os.environ.get('BASE_URL', None) or api.api_root
            )
            api.organization_id = (
                organization or os.environ.get('USER_ORGANIZATION', None) or
                api.organization_id
            )
            api.email = (
                email or os.environ.get('USER_EMAIL', None) or api.email
            )
            api.token = (
                token or os.environ.get('USER_TOKEN', None) or api.token
            )
            ctx.obj.api = api
        except (OSError, IOError):
            click.echo("Welcome to TxPy! It seems like your `.transcriptic` config file is missing or out of date")
            analytics = click.confirm("Send TxPy CLI usage information to improve the CLI user "
                                      "experience?", default=True)
            ctx.obj.api = Connection()  # Initialize empty connection
            ctx.invoke(login, api_root=api_root, analytics=analytics)
    if ctx.obj.api.analytics:
        try:
            ctx.obj.api._post_analytics(event_action=ctx.invoked_subcommand, event_category="cli")
        except:
            pass


@cli.command(cls=FeatureCommand, feature='can_submit_autoprotocol')
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
@click.option('--pm',
              metavar='PAYMENT_METHOD_ID',
              required=False,
              help='Payment id to be used for run submission. '
                   'Use `transcriptic payments` command to list existing '
                   'payment methods.')
@click.pass_context
def submit(ctx, file, project, title=None, test=None, pm=None):
    """Submit your run to the project specified."""
    if pm is not None and not is_valid_payment_method(pm):
        print_stderr("Payment method is invalid. Please specify a payment "
                     "method from `transcriptic payments` or not specify the "
                     "`--payment` flag to use the default payment method.")
        return
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
        req_json = ctx.obj.api.submit_run(
            protocol, project_id=project, title=title, test_mode=test,
            payment_method_id=pm
        )
        run_id = req_json['id']
        click.echo("Run created: %s" %
                   ctx.obj.api.url("%s/runs/%s" % (project, run_id)))
    except Exception as err:
        click.echo("\n" + str(err))


@cli.command('build-release', cls=FeatureCommand, feature='can_upload_packages')
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


@cli.command('upload-release', cls=FeatureCommand,
             feature='can_upload_packages')
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
        bar.update(40)
        file = open(os.path.basename(archive), 'rb')
        url = ctx.obj.api.upload_to_uri(
            file, 'application/zip, application/octet-stream', archive, archive
        )
        bar.update(20)
        try:
            up = ctx.obj.api.post_release(
                data=json.dumps({"release":
                                 {"binary_attachment_url": url}}
                                ),
                package_id=package_id
            )
            re = up['id']
        except (ValueError, PermissionError) as err:
            if type(err) == ValueError:
                click.echo("\nError: There was a problem uploading your release."
                           "\nVerify that your manifest.json file is properly  "
                           "formatted and that all previews in your manifest "
                           "produce valid Autoprotocol by using the "
                           "`transcriptic preview` and/or `transcriptic analyze` "
                           "commands.")
            elif type(err) == PermissionError:
                click.echo("\n" + str(err))
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


@cli.command('upload-dataset')
@click.argument('file_path', type=click.Path(exists=True),
                metavar="FILE")
@click.argument('title', metavar="TITLE")
@click.argument('run_id', metavar="RUN-ID")
@click.option('--tool', '-t', required=True,
              help="Name of analysis tool used for generating the dataset")
@click.option('--version', '-v', required=True,
              help="Version of analysis tool used for generating the dataset")
@click.pass_context
def upload_dataset(ctx, file_path, title, run_id, tool, version):
    """Uploads specified file as an analysis dataset to the specified run."""
    resp = ctx.obj.api.upload_dataset_from_filepath(
        file_path=file_path,
        title=title,
        run_id=run_id,
        analysis_tool=tool,
        analysis_tool_version=version
    )
    try:
        data_id = resp['data']['id']
        run_route = ctx.obj.api.url(
            "/api/runs/{}?fields[runs]=project_id".format(run_id)
        )
        run_resp = ctx.obj.api.get(run_route)
        project = run_resp['data']['attributes']['project_id']
        data_url = "{}/analysis/{}".format(
            ctx.obj.api.get_route(
                'datasets',
                project_id=project,
                run_id=run_id
            ),
            data_id
        )
        click.echo("Dataset uploaded to {}".format(data_url))
    except KeyError:
        click.echo("An unexpected response was returned from the server. ")


@cli.command()
@click.pass_context
@click.option(
    '--local',
    is_flag=True,
    required=False,
    default=False,
    help='Shows available local protocols instead of remote protocols'
)
@click.option("--json", "json_flag", help="print JSON response", is_flag=True)
def protocols(ctx, local, json_flag):
    """List protocols within your manifest or organization."""
    if not local:
        protocol_objs = ctx.obj.api.get_protocols()
    else:
        manifest = load_manifest()
        if 'protocols' not in list(manifest.keys()) or not manifest['protocols']:
            click.echo("Your manifest.json file doesn't contain any protocols or"
                       " is improperly formatted.")
            return
        protocol_objs = manifest['protocols']
    if json_flag:
        click.echo(json.dumps(protocol_objs))
    else:
        click.echo('\n{:^60}'.format("Protocols within this {}:".format("organization" if not local else "manifest")))
        click.echo('{:-^60}'.format(''))
        for p in protocol_objs:
            if p.get('display_name'):
                display_str = u"{} ({})".format(p[u'name'], p.get(u'display_name'))
            else:
                display_str = p[u'name']
            click.echo(u"{}\n{}".format(display_str, u'{:-^60}'.format("")))


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


@cli.command('create-package', cls=FeatureCommand,
             feature='can_upload_packages')
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
    try:
        new_pack = ctx.obj.api.create_package(name, description)
        if new_pack:
            click.echo(
                "New package '%s' created with id %s \n"
                "View it at %s" % (
                    name, new_pack['id'],
                    ctx.obj.api.url('packages/%s' % new_pack['id'])
                )
            )
        else:
            click.echo("There was an error creating this package.")
    except Exception as err:
        click.echo("\n" + str(err))


@cli.command('delete-package', cls=FeatureCommand,
             feature='can_upload_packages')
@click.argument('name')
@click.option('--force', '-f', help="force delete a package without being \
              prompted if you're sure", is_flag=True)
@click.pass_context
def delete_package(ctx, name, force):
    """Delete an existing protocol package"""
    package_id = get_package_id(name)
    if package_id:
        try:
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
        except Exception as err:
            click.echo("\n" + str(err))


@cli.command()
@click.pass_context
@click.option("-i")
@click.option("--json", "json_flag", help="print JSON response", is_flag=True)
def projects(ctx, i, json_flag):
    """List the projects in your organization"""
    try:
        projects = ctx.obj.api.projects()
        proj_id_names = {}
        all_proj = {}
        for proj in projects:
            status = " (archived)" if proj['archived_at'] else ""
            proj_id_names[proj["id"]] = proj["name"]
            all_proj[proj["id"]] = proj["name"] + status
        if i:
            return proj_id_names
        elif json_flag:
            return click.echo(json.dumps(projects))
        else:
            click.echo('\n{:^80}'.format("PROJECTS:\n"))
            click.echo('{:^40}'.format("PROJECT NAME") + "|" +
                       '{:^40}'.format("PROJECT ID"))
            click.echo('{:-^80}'.format(''))
            for proj_id, name in list(all_proj.items()):
                click.echo('{:<40}'.format(name) + "|" +
                           '{:^40}'.format(proj_id))
                click.echo('{:-^80}'.format(''))
    except RuntimeError:
        click.echo("There was an error listing the projects in your "
                   "organization.  Make sure your login details are correct.")


@cli.command()
@click.pass_context
@click.argument('project_name')
@click.option("--json", "json_flag", help="print JSON response", is_flag=True)
def runs(ctx, project_name, json_flag):
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
        if json_flag:
            return click.echo(json.dumps(map(lambda x: {
                                 'title': x['title'] or "(Untitled)",
                                 'id': x['id'],
                                 'completed_at': x['completed_at']
                                 if x['completed_at'] else None,
                                 'created_at': x['created_at'],
                                 'status': x['status']}, req)))
        else:
            click.echo(
                '\n{:^120}'.format("Runs in Project '%s':\n" %
                                   get_project_name(project_id))
            )
            click.echo('{:^30}'.format("RUN TITLE") + "|" +
                       '{:^30}'.format("RUN ID") + "|" +
                       '{:^30}'.format("RUN DATE") + "|" +
                       '{:^30}'.format('RUN STATUS'))
            click.echo('{:-^120}'.format(''))
            for run in run_list:
                click.echo(u'{:^30}'.format(run[0]) + "|" +
                           u'{:^30}'.format(run[1]) + "|" +
                           u'{:^30}'.format(run[2]) + "|" +
                           u'{:^30}'.format(run[3]))
                click.echo(u'{:-^120}'.format(''))


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
            click.confirm(
                "You already have an existing project with the name '{}'. "
                "Are you sure you want to create another one?".format(name),
                default=False,
                abort=True
            )
            break
    try:
        new_proj = ctx.obj.api.create_project(name)
        click.echo(
            "New%s project '%s' created with id %s  \nView it at %s" % (
                " pilot" if dev else "", name, new_proj[
                    'id'], ctx.obj.api.url('%s' % (new_proj['id']))
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
    resource_req = ctx.obj.api.resources(query)
    if resource_req["results"]:
        kit_req = ctx.obj.api.kits(query)
        if not kit_req["results"]:
            common_name = resource_req["results"][0]["name"]
            kit_req = ctx.obj.api.kits(common_name)
        flat_items = list(flatmap(lambda x: [{"name": y["resource"]["name"],
                                              "id": y["resource"]["id"],
                                              "vendor": x["vendor"]["name"] if "vendor" in list(x.keys()) else ''}
                                             for y in x["kit_items"] if
                                             (y["provisionable"] and not y["reservable"])],
                                  kit_req["results"]))
        rs_id_list = [rs["id"] for rs in resource_req["results"]]

        matched_resources = []
        for item in flat_items:
            if item["id"] in rs_id_list and item not in matched_resources:
                matched_resources.append(item)

        if matched_resources:
            click.echo("Results for '%s':" % query)
            click.echo('{:^40}'.format("Resource Name") + '|' +
                       '{:^40}'.format("Vendor") + '|' +
                       '{:^40}'.format("Resource ID"))
            click.echo('{:-^120}'.format(''))
            for resource in matched_resources:
                click.echo('{:^40}'.format(ascii_encode(resource["name"])) + '|' +
                           '{:^40}'.format(ascii_encode(resource["vendor"])) + '|' +
                           '{:^40}'.format(ascii_encode(resource["id"])))
            click.echo('{:-^120}'.format(''))
        else:
            click.echo("No usable resource for '{}'.".format(query))
    else:
        click.echo("No results for '{}'.".format(query))


@cli.command()
@click.argument('query', default='*')
@click.option('--include_aliquots', help='include containers with matching aliquots', is_flag=True)
@click.option('--show_status', help='show container status', is_flag=True)
@click.option('--retrieve_all', help='retrieve all samples, this may take a while', is_flag=True)
@click.pass_context
def inventory(ctx, include_aliquots, show_status, retrieve_all, query):
    """Search organization for inventory"""
    inventory_req = ctx.obj.api.inventory(query)
    num_pages = inventory_req["num_pages"]
    per_page = inventory_req["per_page"]
    results = inventory_req["results"]
    max_results_bound = num_pages * per_page

    num_prefiltered = len(results)

    if retrieve_all:
        for i in range(1, num_pages):
            click.echo("Retrieved {} records"
                       " out of {} total for '{}'...\r".
                       format(i * per_page,
                              max_results_bound, query), nl=False)
            inventory_req = ctx.obj.api.inventory(query, page=i)
            results.extend(inventory_req["results"])
        click.echo()

    if include_aliquots:
        results = [c if "label" in c else c["container"] for c in results]
    else:
        results = [c for c in results if "label" in c]
    results = [i for n, i in enumerate(results) if i not in results[n + 1:]]

    if results:
        def truncate_time(d, k):
            old_time = d[k]
            d[k] = old_time.split("T")[0]
            return d

        results = [truncate_time(c, "created_at") for c in results]
        barcode_present = any(c["barcode"] for c in results)
        keys = ["label", "id", "container_type_id", "storage_condition", "created_at"]
        if barcode_present:
            keys.insert(2, "barcode")
        if show_status:
            keys.append("status")
        friendly_keys = {k: k.split("_")[0] for k in keys}
        spacing = {k: max(len(friendly_keys[k]),
                          max([len(str(c[k])) for c in results])) for k in keys}
        spacing = {k: (v // 2 + 1) * 2 + 1 for k, v in spacing.items()}
        sum_spacing = sum(spacing.values()) + (len(keys) - 1) * 3 + 1
        spacing = {k: "{:^%s}" % v for k, v in spacing.items()}
        sum_spacing = "{:-^%s}" % sum_spacing
        click.echo("Results for '%s':" % query)
        click.echo(' | '.join([spacing[k].
                              format(friendly_keys[k]) for k in keys]))
        click.echo(sum_spacing.format(''))
        for c in results:
            click.echo(' | '.join([spacing[k].
                                  format(ascii_encode(c[k])) for k in keys]))
            click.echo(sum_spacing.format(''))
        if not retrieve_all:
            if num_pages > 1:
                click.echo("Retrieved {} records out of "
                           "{} total (use the --retrieve_all flag "
                           "to request all records).".
                           format(num_prefiltered, max_results_bound))
    else:
        if retrieve_all:
            click.echo("No results for '{}'.".format(query))
        else:
            if num_pages > 1:
                click.echo("Retrieved {} records out of "
                           "{} total but all were filtered out. "
                           "Use the --retrieve_all flag "
                           "to request all records.".
                           format(num_prefiltered, max_results_bound))
            else:
                click.echo("All records were filtered out. "
                           "Use flags to modify your search")


@cli.command()
@click.pass_context
def payments(ctx):
    """Lists available payment methods"""
    methods = ctx.obj.api.payment_methods()
    click.echo('{:^50}'.format("Method") + '|' +
               '{:^20}'.format("Expiry") + '|' +
               '{:^20}'.format("Id"))
    click.echo('{:-^90}'.format(''))
    if len(methods) == 0:
        print_stderr("No payment methods found.")
        return
    for method in methods:
        if method['type'] == "CreditCard":
            description = "{} ending with {}".format(
                method["credit_card_type"], method["credit_card_last_4"]
            )
        elif method['type'] == "PurchaseOrder":
            description = "Purchase Order \"{}\"".format(
                method["description"]
            )
        else:
            description = method["description"]
        if method['is_default?']:
            description += " (Default)"
        if not method['is_valid']:
            description += " (Invalid)"
        click.echo('{:^50}'.format(ascii_encode(description)) + '|' +
                       '{:^20}'.format(ascii_encode(method['expiry'])) + '|' +
                       '{:^20}'.format(ascii_encode(method['id'])))


@click.pass_context
def is_valid_payment_method(ctx, id):
    """Determines if payment is valid"""
    methods = ctx.obj.api.payment_methods()
    return any([id == method['id'] and method['is_valid'] for method in methods])


@cli.command(cls=FeatureCommand, feature='can_upload_packages')
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


@cli.command(cls=FeatureCommand, feature='can_submit_autoprotocol')
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
        format_analysis(analysis)
    except Exception as err:
        click.echo("\n" + str(err))


def format_analysis(response):
    def count(thing, things, num):
        click.echo("  %s %s" % (num, thing if num == 1 else things))

    count("instruction", "instructions", len(response['instructions']))
    count("container", "containers", len(response['refs']))
    price(response)
    for w in response['warnings']:
        message = w['message']
        if 'instruction' in w['context']:
            context = "instruction %s" % w['context']['instruction']
        else:
            context = json.dumps(w['context'])
        click.echo("WARNING (%s): %s" % (context, message))


def price(response):
    """Prints out price based on response"""
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    separator_len = 24
    for quote_item in response['quote']['items']:
        quote_str = "  %s: %s" % (
            quote_item["title"],
            locale.currency(float(quote_item["cost"]), grouping=True))
        click.echo(quote_str)
        separator_len = max(separator_len, len(quote_str))
    click.echo('-' * separator_len)
    click.echo("  Total Cost: %s" %
               locale.currency(float(response['total_cost']),
                               grouping=True))


@cli.command(cls=FeatureCommand, feature='can_upload_packages')
@click.argument('protocol_name', metavar="PROTOCOL_NAME")
@click.option('--view', is_flag=True)
@click.option('--dye_test', is_flag=True)
@click.pass_context
def preview(ctx, protocol_name, view, dye_test):
    """Preview the Autoprotocol output of protocol in the current package."""
    manifest, protocol = load_manifest_and_protocol(protocol_name)

    try:
        inputs = protocol['preview']
    except KeyError:
        click.echo("Error: The manifest.json you're trying to preview doesn't "
                   "contain a \"preview\" section")
        return

    run_protocol(manifest, protocol, inputs, view, dye_test)


@cli.command()
@click.argument('file', default='-')
@click.pass_context
@click.option('--tree', '-t', is_flag=True,
              help='Prints a job tree with instructions as leaf nodes')
@click.option('--lookup', '-l', is_flag=True,
              help='Queries Transcriptic to convert resourceID to string')
# time allowance is on order of seconds
@click.option('--runtime', type=click.INT, default=5)
def summarize(ctx, file, tree, lookup, runtime):
    """Summarize Autoprotocol as a list of plain English steps, as well as a
    visualized Job Tree contingent upon desired runtime allowance (in seconds).
    A Job Tree refers to a structure of protocol based on container dependency,
    where each node, and its corresponding number, represents an instruction of
    the protocol. More specifically, the tree structure contains process branches,
    in which the x-axis refers to the dependency depth in a given branch, while
    the y-axis refers to the traversal of branches themselves.

    Example usage is as follows:

    python my_script.py | transcriptic summarize --tree

    python my_script.py | transcriptic summarize --tree --runtime 20
    """
    with click.open_file(file, 'r') as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo(
                "The autoprotocol you're trying to summarize is invalid.")
            return

    if lookup:
        try:
            config = '~/.transcriptic'
            ctx.obj = ContextObject()
            ctx.obj.api = Connection.from_file(config)
            parser = AutoprotocolParser(protocol, ctx=ctx)
        except:
            click.echo("Connection with Transcriptic failed. "
                       "Summarizing without lookup.", err=True)
            parser = AutoprotocolParser(protocol)
    else:
        parser = AutoprotocolParser(protocol)

    if tree:
        import multiprocessing

        print("\nGenerating Job Tree...")
        p = multiprocessing.Process(target=parser.job_tree)
        p.start()

        # Wait for <runtime_allowance> seconds or until process finishes
        p.join(runtime)

        # If thread is still active
        if p.is_alive():
            print("Still running... Aborting tree construction.")
            print(
                "Please allow for more runtime allowance, or opt for no tree construction.\n")

            # Terminate
            p.terminate()
            p.join()
        else:
            print("\nYour Job Tree is complete!\n")


@cli.command(cls=FeatureCommand, feature='can_upload_packages')
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
@click.argument(
    'params',
    metavar='PARAMETERS_FILE',
    type=click.File('r'),
    required=False
)
@click.option(
    '--project', '-p',
    metavar='PROJECT_ID',
    required=False,
    help='Project id or name context for configuring the protocol. Use '
         '`transcriptic projects` command to list existing projects.'
)
@click.option(
    '--save_input',
    metavar='FILE',
    required=False,
    help='Save the protocol or parameters input JSON in a file. This is '
          'useful for debugging a protocol.'
)
@click.option(
    '--local',
    is_flag=True,
    required=False,
    help='If specified, the protocol will launch a local protocol and submit a run.'
)
@click.option(
    '--accept_quote',
    is_flag=True,
    required=False,
    help='If specified, the quote will automatically be accepted, and a run '
         'will be directly submitted.'
)
@click.option('--pm',
              metavar='PAYMENT_METHOD_ID',
              required=False,
              help='Payment id to be used for run submission. '
                   'Use `transcriptic payments` command to list existing '
                   'payment methods.')
@click.pass_context
def launch(ctx, protocol, project, save_input, local, accept_quote, params, pm=None):
    """Configure and launch a protocol either using the local manifest file or remotely.
    If no parameters are specified, uses the webapp to select the inputs."""
    # Validate payment method
    if pm is not None and not is_valid_payment_method(pm):
        print_stderr("Payment method is invalid. Please specify a payment "
                     "method from `transcriptic payments` or not specify the "
                     "`--payment` flag to use the default payment method.")
        return
    # Load protocol from local file if not remote and load from listed protocols otherwise
    if local:
        manifest, protocol_obj = load_manifest_and_protocol(protocol)
    else:
        print_stderr("Searching for {}...".format(protocol))
        protocol_list = ctx.obj.api.get_protocols()
        matched_protocols = [protocol_obj for protocol_obj in protocol_list if protocol_obj['name'] == protocol]
        if len(matched_protocols) == 0:
            print_stderr("Protocol {} was not found.".format(protocol))
            return
        elif len(matched_protocols) > 1:
            print_stderr("More than one match found. Using the first match.")
        else:
            print_stderr("Protocol found.")
        protocol_obj = matched_protocols[0]

    # If parameters are not specified, use quick launch to get inputs
    if not params:
        # Project is required for quick launch
        if not project:
            click.echo("Project field is required if parameters file is not specified.")
            return
        project = get_project_id(project)
        if not project:
            return

        # Creates web browser and generates inputs for quick_launch
        quick_launch = _get_quick_launch(ctx, protocol_obj, project)

        # Save the protocol input locally if the user specified the save_input option
        if save_input:
            try:
                with click.open_file(save_input, 'w') as f:
                    f.write(json.dumps(quick_launch["inputs"], indent=2))
            except Exception as e:
                print_stderr("\nUnable to save inputs: %s" % str(e))

    if not local:
        # For remote execution, use input params file if specified, else use quick_launch inputs
        if not params:
            params = dict(parameters=quick_launch["raw_inputs"])
            # Save parameters to file if specified
            if save_input:
                try:
                    with click.open_file(save_input, 'w') as f:
                        f.write(json.dumps(params, indent=2))
                except Exception as e:
                    print_stderr("\nUnable to save inputs: %s" % str(e))
        else:
            try:
                params = json.loads(params.read())
            except ValueError:
                print_stderr("Unable to load parameters given. "
                             "File is probably incorrectly formatted.")
                return

        req_id, launch_protocol = _get_launch_request(ctx, params, protocol_obj)

        # Check for generation errors
        generation_errs = launch_protocol["generation_errors"]
        if len(generation_errs) > 0:
            for errors in generation_errs:
                click.echo("\n\n" + str(errors["message"]))
            click.echo("\nPlease fix the above errors and try again.")
            return

        # Confirm proceeding with purchase
        if not accept_quote:
            click.echo("\n\nCost Breakdown")
            resp = ctx.obj.api.analyze_launch_request(req_id)
            click.echo(price(resp))
            confirmed = click.confirm(
                'Would you like to continue with launching the protocol',
                prompt_suffix='? ', default=False
            )
            if not confirmed:
                return

        # Project is required for run submission
        if not project:
            click.echo("\nProject field is required for run submission.")
            return
        project = get_project_id(project)
        if not project:
            return

        from time import strftime, gmtime
        default_title = "{}_{}".format(protocol, strftime("%b_%d_%Y", gmtime()))

        try:
            req_json = ctx.obj.api.submit_launch_request(
                req_id, protocol_id=protocol_obj["id"],
                project_id=project, title=default_title, test_mode=None,
                payment_method_id=pm
            )
            run_id = req_json['id']
            click.echo("\nRun created: %s" %
                       ctx.obj.api.url("%s/runs/%s" % (project, run_id)))
        except Exception as err:
            click.echo("\n" + str(err))
    else:
        print_stderr("\nGenerating Autoprotocol....\n")
        if not params:
            run_protocol(manifest, protocol_obj, quick_launch["inputs"])
        else:
            run_protocol(manifest, protocol_obj, json.load(params))


def _create_launch_request(params, bsl=1, test_mode=False):
    """Creates launch_request from input params"""
    params_dict = dict()
    params_dict["launch_request"] = params
    params_dict["launch_request"]["bsl"] = bsl
    params_dict["launch_request"]["test_mode"] = test_mode
    return json.dumps(params_dict)


def _get_launch_request(ctx, params, protocol):
    """Launches protocol from parameters"""
    launch_request = _create_launch_request(params)
    launch_protocol = ctx.obj.api.launch_protocol(launch_request,
                                                  protocol_id=protocol["id"])
    launch_request_id = launch_protocol["id"]

    # Wait until launch request is updated (max 5 minutes)
    count = 1
    while count <= 150 and launch_protocol['progress'] != 100:
        sys.stderr.write(
            "\rWaiting for launch request to be configured%s" % ('.' * count))
        sys.stderr.flush()
        time.sleep(2)
        launch_protocol = ctx.obj.api.get_launch_request(protocol_id=protocol["id"],
                                                         launch_request_id=launch_request_id)
        count += 1

    return launch_request_id, launch_protocol


def _get_quick_launch(ctx, protocol, project):
    """Creates quick launch object and opens it in a new tab"""
    quick_launch = ctx.obj.api.create_quick_launch(
        data=json.dumps({"manifest": protocol}),
        project_id=project
    )
    quick_launch_mtime = quick_launch["updated_at"]

    format_str = "\nOpening %s"
    url = ctx.obj.api.get_route(
        'get_quick_launch', project_id=project, quick_launch_id=quick_launch["id"])
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
    return quick_launch

@cli.command()
@click.pass_context
def select_org(ctx):
    """Allows you to switch organizations"""
    org_list = [{"name": org['name'], "subdomain": org['subdomain']} for org in ctx.obj.api.organizations()]
    organization = org_prompt(org_list)

    r = ctx.obj.api.get_organization(org_id=organization)
    if r.status_code != 200:
        click.echo("Error accessing organization: %s" % r.text)
        sys.exit(1)

    ctx.obj.api.organization_id = organization
    ctx.obj.api.save(ctx.parent.params['config'])
    click.echo('Logged in with organization: {}'.format(organization))


def org_prompt(org_list):
    """Organization prompt for helping with selecting organization"""
    if len(org_list) < 1:
        click.echo("Error: You don't appear to belong to any organizations. \n"
                   "Visit {} and create an organization.".format('https://secure.transcriptic.com'))
        sys.exit(1)
    if len(org_list) == 1:
        organization = org_list[0]['subdomain']
    else:
        click.echo("You belong to %s organizations:" %
                   len(org_list))
        for indx, o in enumerate(org_list):
            click.echo("{}.  {} ({})".format(indx + 1, o['name'], o['subdomain']))

        def parse_valid_org(indx):
            from click.exceptions import BadParameter
            try:
                org_indx = int(indx) - 1
                if org_indx < 0 or org_indx >= len(org_list):
                    raise ValueError("Value out of range")
                return org_list[org_indx]['subdomain']
            except:
                raise BadParameter("Please enter an integer between 1 and %s" %
                                   (len(org_list)))

        organization = click.prompt(
            'Which organization would you like to log in as',
            default=1,
            prompt_suffix='? ', type=int,
            value_proc=lambda x: parse_valid_org(x)
        )
        # Catch since `value_proc` doesn't properly parse default
        if organization == 1:
            organization = org_list[0]['subdomain']
    return organization


@cli.command()
@click.pass_context
def login(ctx, api_root=None, analytics=True):
    """Authenticate to your Transcriptic account."""
    # For logging in, we should default to the transcriptic domain
    if api_root is None:
        api_root = "https://secure.transcriptic.com"
    email = click.prompt('Email')
    password = click.prompt('Password', hide_input=True)
    r = ctx.obj.api.post(
        routes.login(api_root=api_root),
        data=json.dumps({
            'user': {
                'email': email,
                'password': password,
            },
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        },
        status_response={
            '200': lambda resp: resp,
            '401': lambda resp: resp,
            'default': lambda resp: resp
        },
        custom_request=False
    )
    if r.status_code != 200:
        click.echo("Error logging into Transcriptic: %s" % r.json()['error'])
        sys.exit(1)
    user = r.json()
    token = (user.get('authentication_token') or
             user['test_mode_authentication_token'])
    user_id = user.get("id")
    feature_groups = user.get('feature_groups')
    organization = org_prompt(user['organizations'])

    r = ctx.obj.api.get(routes.get_organization(api_root=api_root, org_id=organization), headers={
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
    ctx.obj.api = Connection(email=email, token=token,
                             organization_id=organization, api_root=api_root,
                             user_id=user_id, analytics=analytics,
                             feature_groups=feature_groups)
    ctx.obj.api.save(ctx.parent.params['config'])
    click.echo('Logged in as %s (%s)' % (user['email'], organization))


@click.pass_context
def get_project_id(ctx, name):
    projs = ctx.invoke(projects, i=True)
    if name in projs:
        return name
    else:
        project_ids = [k for k, v in projs.items() if v == name]
        if not project_ids:
            click.echo(
                "The project '%s' was not found in your organization." % name)
            return
        elif len(project_ids) > 1:
            click.echo(
                "Found multiple projects: {} that match '{}'.".format(
                    project_ids, name))
            # TODO: Add project selector with dates and number of runs
            return
        else:
            return project_ids[0]


@click.pass_context
def get_project_name(ctx, id):
    projs = ctx.invoke(projects, i=True)
    name = projs.get(id)
    if not name:
        name = id if id in projs.values() else None
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
        package_name = package_id if package_id in list(
            package_names.values()) else None
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
def run_protocol(ctx, manifest, protocol, inputs, view=False, dye_test=False):
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
            if dye_test:
                protocol = check_output(["bash", "-c", command + " " + fp.name + " --dye_test"])
            else:
                protocol = check_output(["bash", "-c", command + " " + fp.name])
            click.echo(protocol)
            if view:
                click.echo("View your protocol's raw JSON above or see the "
                           "instructions rendered at the following link: \n%s" %
                           ProtocolPreview(protocol, ctx.obj.api).preview_url)
        except CalledProcessError as e:
            click.echo(e.output)
            return


@cli.command(cls=FeatureCommand, feature='can_upload_packages')
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
