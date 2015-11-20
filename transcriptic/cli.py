from builtins import next
from builtins import str
#!/usr/bin/env python

import sys
import json
import requests
import click
import locale
import zipfile
import os
import time
import xml.etree.ElementTree as ET
import re
from transcriptic import AnalysisException, analyze as api_analyze, submit as api_submit
from transcriptic.english import AutoprotocolParser
from transcriptic.config import Connection
from transcriptic.objects import ProtocolPreview
from transcriptic.util import iter_json
from os.path import isfile
from collections import OrderedDict

# Workaround to support the correct input for both Python 2 and 3. Always use
# input() which will point to the correct builtin.
try:
  input = raw_input
except NameError:
  pass

@click.group()
@click.option('--apiroot', default=None)
@click.option(
  '--config',
   envvar = 'TRANSCRIPTIC_CONFIG',
   default = '~/.transcriptic',
   help = 'Specify a configuration file.'
)
@click.option('--organization', '-o', default=None)
@click.pass_context
def cli(ctx, apiroot, config, organization):
  '''A command line tool for working with Transcriptic.'''
  if ctx.invoked_subcommand not in ['login']:
    try:
      ctx.obj = Connection.from_file(config)
      if organization is not None:
        ctx.obj.organization_id = organization
      if apiroot is not None:
        ctx.obj.api_root = apiroot
    except IOError:
      click.echo("Error reading config file, running "
                 "`transcriptic login` ...")
      ctx.invoke(login)

@cli.command()
@click.argument('file', default='-')
@click.option(
  '--project', '-p',
  metavar = 'PROJECT_ID',
  required = True,
  help = 'Project id or name to submit the run to. Use `transcriptic projects` command to list existing projects.'
)
@click.option('--title', '-t', help='Optional title of your run')
@click.option('--test', help='Submit this run in test mode', is_flag=True)
@click.pass_context
def submit(ctx, file, project, title, test):
  '''Submit your run to the project specified.'''
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

  try:
    req_json = api_submit(protocol, project, title, test_mode = test)
    run_id = req_json['id']
    click.echo("Run created: %s" % ctx.obj.url("%s/runs/%s" % (project, run_id)))
  except Exception as e:
    click.echo(str(e))

@cli.command('build-release')
@click.argument('package', required=False, metavar="PACKAGE")
@click.option('--name', '-n', help="Optional name for your zip file")
@click.pass_context
def release(ctx, name=None, package=None):
  '''Compress the contents of the current directory to upload as a release.'''
  deflated = zipfile.ZIP_DEFLATED
  with open('manifest.json', 'rU') as manifest:
    filename = 'release_v%s' %json.load(manifest)['version'] or name
  if os.path.isfile(filename + ".zip"):
    new = click.prompt("You already have a release for this "
                       "version number in this directory, make "
                       "another one? [y/n]", default = "y")
    if new == "y":
      num_existing = sum([1 for x in os.listdir('.') if filename in x])
      filename = filename + "-" + str(num_existing)
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
    ctx.invoke(upload_release, archive=(filename + ".zip"), package=package_id)

@cli.command("upload-release")
@click.argument('archive', required=True, type=click.Path(exists=True),
                 metavar="ARCHIVE")
@click.argument('package', required=True, metavar="PACKAGE")
@click.pass_context
def upload_release(ctx, archive, package):
  """Upload a release archive to a package."""
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
    sign = requests.get('https://secure.transcriptic.com/upload/sign', params = {
      'name': archive
    }, headers = {
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
      up = ctx.obj.post('packages/%s/releases/' % package_id, data = json.dumps({
        "release": {
          "binary_attachment_url": loc["Key"]
        }
      }), headers= {
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
    status = ctx.obj.get('packages/%s/releases/%s?_=%s' % (package_id, re, int(time.time())))
    published = json.loads(status.content)['published']
    errors = status.json()['validation_errors']
    bar.update(30)
    if errors:
      click.echo("\nPackage upload to %s unsuccessful. The following error(s) was returned: \n%s" % (
        get_package_name(package_id), ('\n').join(e.get('message', '[Unknown]') for e in errors)))
    else:
      click.echo("\nPackage uploaded successfully! \n"
                 "Visit %s to publish." % ctx.obj.url('packages/%s' % package_id))

@cli.command()
def protocols():
  '''List protocols within your manifest.'''
  try:
    with click.open_file('manifest.json', 'r') as f:
      try:
        manifest = json.loads(f.read())
      except ValueError:
        click.echo("Error: Your manifest.json file is improperly formatted. "
                   "Please double check your brackets and commas!")
        return
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
  except IOError:
    click.echo("The current directory does not contain a manifest.json file.")
    return

@cli.command()
@click.pass_context
@click.option("-i")
def packages(ctx, i):
  '''List packages in your organization.'''
  response = ctx.obj.get('packages/')
  # there's probably a better way to do this
  package_names = OrderedDict(sorted(list({"yours": {}, "theirs": {}}.items()), key=lambda t: len(t[0])))
  if response.status_code == 200:
    for pack in response.json():
      n = str(pack['name']).lower().replace("com.%s." % ctx.obj.organization_id, "")
      latest = str(pack['latest_version']) if pack['latest_version'] else "-"
      if pack.get('owner') and pack['owner']['email'] == ctx.obj.email:
        package_names['yours'][n] = {}
        package_names['yours'][n]['id'] = str(pack['id'])
        package_names['yours'][n]['latest'] = latest
      else:
        package_names['theirs'][n] = {}
        package_names['theirs'][n]['id'] = str(pack['id'])
        package_names['theirs'][n]['latest'] = latest
  if i:
    return dict(list(package_names['yours'].items()) + list(package_names['theirs'].items()))
  else:
    for category, packages in list(package_names.items()):
      if category == "yours":
        click.echo('\n{:^90}'.format("YOUR PACKAGES:\n"))
        click.echo('{:^30}'.format("PACKAGE NAME") + "|" +
               '{:^30}'.format("PACKAGE ID")
               + "|" + '{:^30}'.format("LATEST PUBLISHED VERSION"))
        click.echo('{:-^90}'.format(''))
      elif category == "theirs" and list(packages.values()):
        click.echo('\n{:^90}'.format("OTHER PACKAGES IN YOUR ORG:\n"))
        click.echo('{:^30}'.format("PACKAGE NAME") + "|" +
                   '{:^30}'.format("PACKAGE ID") + "|" +
                   '{:^30}'.format("LATEST PUBLISHED VERSION"))
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
  '''Create a new empty protocol package'''
  existing = ctx.obj.get('packages/')
  for p in existing.json():
    if name == p['name'].split('.')[-1]:
      click.echo("You already have an existing package with the name \"%s\"."
                 "  Please choose a different package name." % name)
      return
  new_pack = ctx.obj.post('packages/', data = json.dumps({
    "description": description,
    "name": "%s%s" % ("com.%s." % ctx.obj.organization_id, name)
  }))
  if new_pack.status_code == 201:
    click.echo("New package '%s' created with id %s \n"
               "View it at %s" % (name, new_pack.json()['id'], ctx.obj.url('packages/%s' % new_pack.json()['id'])))
  else:
    click.echo("There was an error creating this package.")

@cli.command("delete-package")
@click.argument('name')
@click.option('--force', '-f', help="force delete a package without being prompted if you're sure", is_flag=True)
@click.pass_context
def delete_package(ctx, name, force):
  '''Delete an existing protocol package'''
  id = get_package_id(name)
  if id:
    if not force:
      click.confirm(
        "Are you sure you want to permanently delete the package '%s'?  All releases within will be lost." %
        get_package_name(id), default = False, abort = True
      )
      click.confirm("Are you really really sure?", default = True)
    del_pack = ctx.obj.delete_package(id)
    if del_pack:
      click.echo("Package deleted.")
    else:
      click.echo("There was a problem deleting this package.")


@cli.command()
@click.pass_context
@click.option("-i")
def projects(ctx, i):
  '''List the projects in your organization'''
  try:
    projects = ctx.obj.projects()
    proj_names = {}
    proj_cats = {"reg": {}, "pilot": {}}
    for proj in projects:
      proj_names[proj.attributes['name']] =  proj.id
      if proj.attributes["is_developer"]:
        proj_cats["pilot"][proj.attributes['name']] =  proj.id
      else:
        proj_cats["reg"][proj.attributes['name']] =  proj.id
    if i:
      return {k.lower(): v for k,v in list(proj_names.items())}
    else:
      for cat, packages in list(proj_cats.items()):
        if cat == "reg":
          click.echo('\n{:^80}'.format("PROJECTS:\n"))
          click.echo('{:^40}'.format("PROJECT NAME") + "|" +
                     '{:^40}'.format("PROJECT ID"))
          click.echo('{:-^80}'.format(''))
        elif cat == "pilot" and list(packages.values()):
          click.echo('\n{:^80}'.format("PILOT PROJECTS:\n"))
          click.echo('{:^40}'.format("PROJECT NAME") + "|" +
                     '{:^40}'.format("PROJECT ID"))
          click.echo('{:-^80}'.format(''))
        for name, i in list(packages.items()):
          click.echo('{:<40}'.format(name) + "|" +
                     '{:^40}'.format(i))
          click.echo('{:-^80}'.format(''))
  except RuntimeError:
    click.echo("There was an error listing the projects in your "
               "organization.  Make sure your login details are correct.")

@cli.command("create-project")
@click.argument('name', metavar = "PROJECT_NAME")
@click.option('--dev', '-d', '-pilot', help = "Create a pilot project", is_flag = True)
@click.pass_context
def create_project(ctx, name, dev):
  '''Create a new empty project.'''
  existing = ctx.obj.projects()
  for p in existing:
    if name == p.attributes['name'].split('.')[-1]:
      click.echo("You already have an existing project with the name \"%s\"."
                 "  Please choose a different project name." % name)
      return
  try:
    new_proj = ctx.obj.create_project(name, is_developer = dev)
    click.echo(
      "New%s project '%s' created with id %s  \nView it at %s" % (
        " pilot" if dev else "", name, new_proj.attributes['id'], ctx.obj.url('%s' % (new_proj.attributes['id']))
      )
    )
  except RuntimeError:
    click.echo("There was an error creating this project.")

@cli.command("delete-project")
@click.argument('name', metavar = "PROJECT_NAME")
@click.option('--force', '-f', help = "force delete a project without being prompted if you're sure", is_flag = True)
@click.pass_context
def delete_project(ctx, name, force):
  '''Delete an existing project.'''
  id = get_project_id(name)
  if id:
    if not force:
      click.confirm(
        "Are you sure you want to permanently delete '%s'?" % get_project_name(id),
        default = False,
        abort = True
      )
    if ctx.obj.delete_project(str(id)):
      click.echo("Project deleted.")
    else:
      click.confirm(
        "Could not delete project. This may be because it contains runs. Try archiving it instead?",
        default = False,
        abort = True
      )
      if ctx.obj.archive_project(str(id)):
        click.echo("Project archived.")
      else:
        click.echo("Could not archive project!")

@cli.command()
@click.argument('query', default='*')
@click.pass_context
def resources(ctx, query):
    '''Search catalog of provisionable resources'''
    req = ctx.obj.resources(query)
    if req["results"]:
      click.echo("Results for '%s':" % query)
      click.echo('{:^40}'.format("Resource Name") + '|' +
                   '{:^40}'.format("Vendor") + '|' + '{:^40}'.format("Resource ID"))
      click.echo('{:-^120}'.format(''))
    else:
      click.echo("No results for '%s'." % query)
    for i in req["results"]:
      if i["provisionable"] and not i["reservable"]:
        name = i['name'].encode('ascii', errors='ignore')
        id = i['kit_items'][0]['resource_id']
        click.echo('{:^40}'.format(name) + '|' +
                   '{:^40}'.format(i['vendor']['name'] if 'vendor' in list(i.keys()) else '') + '|' + '{:^40}'.format(id))
        click.echo('{:-^120}'.format(''))


@cli.command()
@click.argument('path', default='.')
def init(path):
  '''Initialize a directory with a manifest.json file.'''
  manifest_data = OrderedDict(
    version="1.0.0",
    format="python",
    license="MIT",
    protocols = [{
      "name": "SampleProtocol",
      "display_name" :"Sample Protocol",
      "description" :"This is a protocol.",
      "command_string" :"python sample_protocol.py",
      "inputs":{},
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
                  default = False,
                  abort = True)
  with open('%s/manifest.json' % path, 'w+') as f:
    click.echo('Creating empty manifest.json...')
    f.write(json.dumps(dict(manifest_data), indent=2))
    click.echo("manifest.json created")


@cli.command()
@click.argument('file', default='-')
@click.option('--test', help='Analyze this run in test mode', is_flag=True)
@click.pass_context
def analyze(ctx, file, test):
  '''Analyze a block of Autoprotocol JSON.'''
  with click.open_file(file, 'r') as f:
    try:
      protocol = json.loads(f.read())
    except ValueError:
      click.echo("Error: The Autoprotocol you're trying to analyze is not "
                 "properly formatted.  "
                 "\nCheck that your manifest.json file is "
                 "valid JSON \nand/or your script "
                 "doesn't print anything other than pure Autoprotocol "
                 "to standard out.")
      return

  try:
    analysis = api_analyze(protocol, test_mode = test)
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
  click.echo("  Total Cost: %s" % locale.currency(float(response['total_cost']), grouping=True))
  for quote_item in response['quote']['items']:
      click.echo("  %s: %s" % (quote_item["title"], locale.currency(float(quote_item["cost"]), grouping=True)))
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
  '''Preview the Autoprotocol output of protocol in the current package.'''
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
    click.echo("Error: Your manifest.json file does not have a \"command_string\" key.")
    return
  from subprocess import call, check_output, CalledProcessError
  import tempfile
  with tempfile.NamedTemporaryFile() as fp:
    try:
      fp.write(json.dumps(p['preview']))
    except KeyError:
      click.echo("Error: The manifest.json you're trying to preview doesn't "
                 "contain a \"preview\" section")
      return
    fp.flush()
    try:
      protocol = check_output(["bash", "-c", command + " " + fp.name])
      click.echo(protocol)
      if view:
         click.echo("View your protocol's raw JSON above or see the intructions "
                    "rendered at the following link: \n%s" %
                    ProtocolPreview(protocol, ctx.obj).preview_url)
    except CalledProcessError as e:
      click.echo(e.output)
      return

@cli.command()
@click.argument('file', default='-')
@click.pass_context
def summarize(ctx, file):
  """Summarize Autoprotocol as a list of plain English steps."""
  with click.open_file(file, 'r') as f:
    try:
      protocol = json.loads(f.read())
    except ValueError:
      click.echo("The autoprotocol you're trying to summarize is invalid.")
      return
  AutoprotocolParser(protocol)

@cli.command()
@click.argument('protocol_name', metavar="PROTOCOL_NAME")
@click.argument('args', nargs=-1)
def compile(protocol_name, args):
  '''Compile a protocol by passing it a config file (without submitting or analyzing).'''
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
    click.echo("Error: Your manifest.json file does not have a \"command_string\" key.")
    return
  from subprocess import call
  call(["bash", "-c", command + " " + ' '.join(args)])

@cli.command()
@click.option('--api-root', default='https://secure.transcriptic.com')
@click.pass_context
def login(ctx, api_root):
  '''Authenticate to your Transcriptic account.'''
  email = click.prompt('Email')
  password = click.prompt('Password', hide_input=True)
  r = requests.post("%s/users/sign_in" % api_root, data = json.dumps({
    'user': {
      'email': email,
      'password': password,
    },
  }), headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  })
  if r.status_code != 200:
    click.echo("Error logging into Transcriptic: %s" % r.json()['error'])
    sys.exit(1)
  user = r.json()
  token = (user.get('authentication_token') or user['test_mode_authentication_token'])
  if len(user['organizations']) < 1:
    click.echo("Error: You don't appear to belong to any organizations. \nVisit %s "
               "and create an organization." % api_root)
    sys.exit(1)
  if len(user['organizations']) == 1:
    organization = user['organizations'][0]['subdomain']
  else:
    click.echo("You belong to %s organizations:" % len(user['organizations']))
    for o in user['organizations']:
      click.echo("  %s (%s)" % (o['name'], o['subdomain']))
    organization = click.prompt(
      'Which would you like to login as',
      default = user['organizations'][0]['subdomain'],
      prompt_suffix='? '
    )
  r = requests.get('%s/%s' % (api_root, organization), headers = {
    'X-User-Email': email,
    'X-User-Token': token,
    'Accept': 'application/json',
  })
  if r.status_code != 200:
    click.echo("Error accessing organization: %s" % r.text)
    sys.exit(1)
  ctx.obj = Connection(email, token, organization, api_root = api_root)
  ctx.obj.save(ctx.parent.params['config'])
  click.echo('Logged in as %s (%s)' % (user['email'], organization))

@click.pass_context
def get_project_id(ctx, name):
  projs = ctx.invoke(projects, i=True)
  id = projs.get(name.lower())
  if not id:
    id = name if name in list(projs.values()) else None
    if not id:
      click.echo("A project with the name '%s' was not found in your organization." % name)
      return
  return id

@click.pass_context
def get_project_name(ctx, id):
  projs = {v:k for k,v in list(ctx.invoke(projects, i=True).items())}
  name = projs.get(id)
  if not name:
    name = id if name in list(projs.keys()) else None
    if not name:
      click.echo("A project with the id '%s' was not found in your organization." % name)
      return
  return name

@click.pass_context
def get_package_id(ctx, name):
  package_names = ctx.invoke(packages, i=True)
  package_names = {k.lower(): v['id'] for k,v in list(package_names.items())}
  package_id = package_names.get(name)
  if not package_id:
    package_id = name if name in list(package_names.values()) else None
  if not package_id:
    click.echo("The package '%s' does not exist in your organization." % name)
    return
  return package_id

@click.pass_context
def get_package_name(ctx, id):
  package_names = {v['id']: k for k, v in list(ctx.invoke(packages, i=True).items())}
  package_name = package_names.get(id)
  if not package_name:
    package_name = id if id in list(package_names.values()) else None
  if not package_name:
    click.echo("The id '%s' does not match any package in your organization."
               % id)
    return
  return package_name

@cli.command()
@click.argument('manifest', default='manifest.json')
def format(manifest):
  '''Check Autoprotocol format of manifest.json.'''
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
