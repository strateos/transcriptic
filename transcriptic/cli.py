#!/usr/bin/env python3
import json
import os
import sys

import click
import requests

from transcriptic import commands
from transcriptic.config import Connection


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
            ctx.obj.api = Connection.from_file("~/.transcriptic")
        except (FileNotFoundError, OSError):
            # This defaults to feature_groups = []
            ctx.obj.api = Connection()

        rows = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            try:
                if (
                    cmd.feature is not None
                    and cmd.feature in ctx.obj.api.feature_groups
                ):
                    help = cmd.short_help or ""
                    rows.append((subcommand, help))
                else:
                    continue
            except AttributeError:
                help = cmd.short_help or ""
                rows.append((subcommand, help))

        if rows:
            with formatter.section("Commands"):
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
        __hidden__ = attrs.pop("hidden", True)
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


_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=_CONTEXT_SETTINGS, cls=FeatureGroup)
@click.option("--api-root", default=None, hidden=True, cls=HiddenOption)
@click.option("--email", default=None, hidden=True, cls=HiddenOption)
@click.option("--token", default=None, hidden=True, cls=HiddenOption)
@click.option("--organization", "-o", default=None, hidden=True, cls=HiddenOption)
@click.option(
    "--config",
    envvar="TRANSCRIPTIC_CONFIG",
    default="~/.transcriptic",
    help="Specify a configuration file.",
)
@click.version_option(prog_name="Transcriptic Python Library (TxPy)")
@click.pass_context
def cli(ctx, api_root, email, token, organization, config):
    """A command line tool for working with Transcriptic.

    Note: This is the main entry point of the CLI. If specifying credentials,
    note that the order of preference is: --flag, environment then config file.

    Example: `transcriptic --organization "my_org" projects` >>
    `export USER_ORGANIZATION="my_org"` >> `"organization_id": "my_org" in
     ~/.transcriptic
    """
    # Initialize ContextObject to be used for storing api object
    ctx.obj = ContextObject()

    if ctx.invoked_subcommand in ["compile", "preview", "summarize", "init"]:
        # For local commands, initialize empty connection
        ctx.obj.api = Connection()
    elif ctx.invoked_subcommand == "login":
        # Load analytics option from existing dotfile if present, else prompt
        try:
            api = Connection.from_file(config)
            api.api_root = api_root or os.environ.get("BASE_URL", None) or api.api_root
            ctx.obj.api = api
        except (OSError, IOError):
            ctx.obj.api = Connection()
        # Echo a warning if other options are defined for login
        if organization or email or token:
            click.echo(
                "Only the `--api-root` option is applicable for the "
                "`login` command. All other options are ignored."
            )
    else:
        try:
            api = Connection.from_file(config)
            api.api_root = api_root or os.environ.get("BASE_URL", None) or api.api_root
            api.organization_id = (
                organization
                or os.environ.get("USER_ORGANIZATION", None)
                or api.organization_id
            )
            api.email = email or os.environ.get("USER_EMAIL", None) or api.email
            api.token = token or os.environ.get("USER_TOKEN", None) or api.token
            ctx.obj.api = api
        except (OSError, IOError):
            click.echo(
                "Welcome to TxPy! It seems like your `.transcriptic` "
                "config file is missing or out of date"
            )
            analytics = click.confirm(
                "Send TxPy CLI usage information to "
                "improve the CLI user "
                "experience?",
                default=True,
            )
            ctx.obj.api = Connection()  # Initialize empty connection
            ctx.invoke(login_cmd, api_root=api_root, analytics=analytics)
    if ctx.obj.api.analytics:
        try:
            ctx.obj.api._post_analytics(
                event_action=ctx.invoked_subcommand, event_category="cli"
            )
        except requests.exceptions.RequestException:
            pass


@cli.command("submit", cls=FeatureCommand, feature="can_submit_autoprotocol")
@click.argument("file", default="-")
@click.option(
    "--project",
    "-p",
    metavar="PROJECT_ID",
    required=True,
    help=(
        "Project id or name to submit the run to. "
        "Use `transcriptic projects` command to list existing projects."
    ),
)
@click.option("--title", "-t", help="Optional title of your run")
@click.option("--test", help="Submit this run in test mode", is_flag=True)
@click.option(
    "--pm",
    metavar="PAYMENT_METHOD_ID",
    required=False,
    help="Payment id to be used for run submission. "
    "Use `transcriptic payments` command to list existing "
    "payment methods.",
)
@click.pass_context
def submit_cmd(ctx, file, project, title=None, test=None, pm=None):
    """Submit your run to the project specified."""
    api = ctx.obj.api
    try:
        run_url = commands.submit(api, file, project, title=title, test=test, pm=pm)
        click.echo(f"Run created: {run_url}")
    except RuntimeError as err:
        click.echo(f"{err}", err=True)
        sys.exit(1)


@cli.command("build-release", cls=FeatureCommand, feature="can_upload_packages")
@click.argument("package", required=False, metavar="PACKAGE")
@click.option("--name", "-n", help="Optional name for your zip file")
@click.pass_context
def release_cmd(ctx, name=None, package=None):
    """Compress the contents of the current directory to upload as a release."""
    api = ctx.obj.api
    commands.release(api, name=name, package=package)


@cli.command("upload-release", cls=FeatureCommand, feature="can_upload_packages")
@click.argument(
    "archive", required=True, type=click.Path(exists=True), metavar="ARCHIVE"
)
@click.argument("package", required=True, metavar="PACKAGE")
@click.pass_context
def upload_release_cmd(ctx, archive, package):
    """Upload a release archive to a package."""
    api = ctx.obj.api
    commands.upload_release(api, archive, package)


@cli.command("upload-dataset")
@click.argument("file_path", type=click.Path(exists=True), metavar="FILE")
@click.argument("title", metavar="TITLE")
@click.argument("run_id", metavar="RUN-ID")
@click.option(
    "--tool",
    "-t",
    required=True,
    help="Name of analysis tool used for generating the dataset",
)
@click.option(
    "--version",
    "-v",
    required=True,
    help="Version of analysis tool used for generating the dataset",
)
@click.pass_context
def upload_dataset_cmd(ctx, file_path, title, run_id, tool, version):
    """Uploads specified file as an analysis dataset to the specified run."""
    api = ctx.obj.api
    commands.upload_dataset(api, file_path, title, run_id, tool, version)


@cli.command("protocols")
@click.pass_context
@click.option(
    "--local",
    is_flag=True,
    required=False,
    default=False,
    help="Shows available local protocols instead of remote protocols",
)
@click.option("--json", "json_flag", help="print JSON response", is_flag=True)
def protocols_cmd(ctx, local, json_flag):
    """List protocols within your manifest or organization."""
    api = ctx.obj.api
    commands.protocols(api, local, json_flag)


@cli.command("packages")
@click.pass_context
@click.option("-i")
def packages_cmd(ctx, i):
    """List packages in your organization."""
    api = ctx.obj.api
    commands.packages(api, i)


@cli.command("create-package", cls=FeatureCommand, feature="can_upload_packages")
@click.argument("name")
@click.argument("description")
@click.pass_context
def create_package_cmd(ctx, description, name):
    """Create a new empty protocol package"""
    api = ctx.obj.api
    commands.create_package(api, description, name)


@cli.command("delete-package", cls=FeatureCommand, feature="can_upload_packages")
@click.argument("name")
@click.option(
    "--force",
    "-f",
    help="force delete a package without being \
              prompted if you're sure",
    is_flag=True,
)
@click.pass_context
def delete_package_cmd(ctx, name, force):
    """Delete an existing protocol package"""
    api = ctx.obj.api
    commands.delete_package(api, name, force)


@cli.command("generate-protocol")
@click.pass_context
@click.argument("name")
def generate_protocol_cmd(ctx, name):
    """Generate a python protocol scaffold"""
    commands.generate_protocol(name)


@cli.command("projects")
@click.pass_context
@click.option("-i", help="DEPRECATED option. Use `--names` instead.")
@click.option("--json", "json_flag", help="print JSON response", is_flag=True)
@click.option(
    "--names",
    "names_only",
    help="returns a mapping of `project_id`: `project_name`",
    is_flag=True,
)
def projects_cmd(ctx, i, json_flag, names_only):
    """List the projects in your organization"""
    api = ctx.obj.api
    try:
        response = commands.projects(api, i, json_flag, names_only)
        if i or names_only:
            click.echo(response)
        elif json_flag:
            click.echo(json.dumps(response))
        else:
            click.echo("\n{:^80}".format("PROJECTS:\n"))
            click.echo(f"{'PROJECT NAME':^40}" + "|" + f"{'PROJECT ID':^40}")
            click.echo(f"{'':-^80}")
            for proj_id, name in list(response.items()):
                click.echo(f"{name:<40}" + "|" + f"{proj_id:^40}")
                click.echo(f"{'':-^80}")
    except RuntimeError:
        click.echo(
            "There was an error listing the projects in your "
            "organization. Make sure your login details are correct.",
            err=True,
        )


@cli.command("runs")
@click.pass_context
@click.argument("project_name")
@click.option("--json", "json_flag", help="print JSON response", is_flag=True)
def runs_cmd(ctx, project_name, json_flag):
    """List the runs that exist in a project"""
    api = ctx.obj.api
    commands.runs(api, project_name, json_flag)


@cli.command("create-project")
@click.argument("name", metavar="PROJECT_NAME")
@click.option("--dev", "-d", "-pilot", help="Create a pilot project", is_flag=True)
@click.pass_context
def create_project_cmd(ctx, name, dev):
    """Create a new empty project."""
    api = ctx.obj.api
    commands.create_project(api, name, dev)


@cli.command("delete-project")
@click.argument("name", metavar="PROJECT_NAME")
@click.option(
    "--force",
    "-f",
    help="force delete a project without being \
              prompted if you're sure",
    is_flag=True,
)
@click.pass_context
def delete_project_cmd(ctx, name, force):
    """Delete an existing project."""
    api = ctx.obj.api
    commands.delete_project(api, name, force)


@cli.command("resources")
@click.argument("query", default="*")
@click.pass_context
def resources_cmd(ctx, query):
    """Search catalog of provisionable resources"""
    api = ctx.obj.api
    commands.resources(api, query)


@cli.command("inventory")
@click.argument("query", default="*")
@click.option(
    "--include_aliquots", help="include containers with matching aliquots", is_flag=True
)
@click.option("--show_status", help="show container status", is_flag=True)
@click.option(
    "--retrieve_all", help="retrieve all samples, this may take a while", is_flag=True
)
@click.pass_context
def inventory_cmd(ctx, include_aliquots, show_status, retrieve_all, query):
    """Search organization for inventory"""
    api = ctx.obj.api
    commands.inventory(api, include_aliquots, show_status, retrieve_all, query)


@cli.command("payments")
@click.pass_context
def payments_cmd(ctx):
    """Lists available payment methods"""
    api = ctx.obj.api
    commands.payments(api)


@cli.command("init", cls=FeatureCommand, feature="can_upload_packages")
@click.argument("path", default=".")
def init_cmd(path):
    """Initialize a directory with a manifest.json file."""
    commands.init(path)


@cli.command("analyze")
@click.argument("file", default="-")
@click.option("--test", help="Analyze this run in test mode", is_flag=True)
@click.pass_context
def analyze_cmd(ctx, file, test):
    """Analyze a block of Autoprotocol JSON."""
    api = ctx.obj.api
    commands.analyze(api, file, test)


@cli.command("preview", cls=FeatureCommand, feature="can_upload_packages")
@click.argument("protocol_name", metavar="PROTOCOL_NAME")
@click.option("--view", is_flag=True)
@click.option("--dye_test", is_flag=True)
@click.pass_context
def preview_cmd(ctx, protocol_name, view, dye_test):
    """Preview the Autoprotocol output of protocol in the current package."""
    api = ctx.obj.api
    commands.preview(api, protocol_name, view, dye_test)


@cli.command("summarize")
@click.argument("file", default="-")
@click.pass_context
@click.option(
    "--html", "-x", is_flag=True, help="Generates an html view of the autoprotocol"
)
@click.option(
    "--tree",
    "-t",
    is_flag=True,
    help="Prints a job tree with instructions as leaf nodes",
)
@click.option(
    "--lookup",
    "-l",
    is_flag=True,
    help="Queries Transcriptic to convert resourceID to string",
)
# time allowance is on order of seconds
@click.option("--runtime", type=click.INT, default=5)
def summarize_cmd(ctx, file, html, tree, lookup, runtime):
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

    python my_script.py | transcriptic summarize --html
    """
    if lookup or html:
        try:
            config = "~/.transcriptic"
            ctx.obj = ContextObject()
            ctx.obj.api = Connection.from_file(config)
        except:
            click.echo(
                "Connection with Transcriptic failed. Summarizing without lookup.",
                err=True,
            )

    api = ctx.obj.api
    commands.summarize(api, file, html, tree, lookup, runtime)


@cli.command("compile", cls=FeatureCommand, feature="can_upload_packages")
@click.argument("protocol_name", metavar="PROTOCOL_NAME")
@click.argument("args", nargs=-1)
def compile_cmd(protocol_name, args):
    """Compile a protocol by passing it a config file (without submitting or
    analyzing)."""
    commands.compile(protocol_name, args)


@cli.command("launch")
@click.argument("protocol")
@click.argument(
    "params", metavar="PARAMETERS_FILE", type=click.File("r"), required=False
)
@click.option(
    "--project",
    "-p",
    metavar="PROJECT_ID",
    required=False,
    help="Project id or name context for configuring the protocol. Use "
    "`transcriptic projects` command to list existing projects.",
)
@click.option(
    "--title",
    "-t",
    metavar="RUN_TITLE",
    required=False,
    help="If specified, will apply custom title to run created, default run title"
    "will be the DISPLAY-NAME_MM_DD_YYYY of the protocol selected.",
)
@click.option(
    "--save_input",
    metavar="FILE",
    required=False,
    help="Save the protocol or parameters input JSON in a file. This is "
    "useful for debugging a protocol.",
)
@click.option(
    "--local",
    is_flag=True,
    required=False,
    help="If specified, the protocol will launch a local protocol and submit a run.",
)
@click.option(
    "--accept_quote",
    is_flag=True,
    required=False,
    help="If specified, the quote will automatically be accepted, and a run "
    "will be directly submitted.",
)
@click.option(
    "--pm",
    metavar="PAYMENT_METHOD_ID",
    required=False,
    help="Payment id to be used for run submission. "
    "Use `transcriptic payments` command to list existing "
    "payment methods.",
)
@click.option("--test", help="Submit this run in test mode", is_flag=True)
@click.option(
    "--pkg",
    metavar="PACKAGE_ID",
    required=False,
    help="Package ID for discriminating between protocols with identical names",
)
@click.option(
    "--save_preview",
    "-sp",
    is_flag=True,
    required=False,
    help="Save the protocol preview parameters and refs selected as input and merge into local "
    "manifest.json. This is useful for debugging a protocol.",
)
@click.pass_context
def launch_cmd(
    ctx,
    protocol,
    project,
    title,
    save_input,
    local,
    accept_quote,
    params,
    pm=None,
    test=None,
    pkg=None,
    save_preview=False,
):
    """Configure and launch a protocol either using the local manifest file or remotely.
    If no parameters are specified, uses the webapp to select the inputs."""
    api = ctx.obj.api
    commands.launch(
        api,
        protocol,
        project,
        title,
        save_input,
        local,
        accept_quote,
        params,
        pm=None,
        test=None,
        pkg=None,
        save_preview=save_preview,
    )


@cli.command("select-org")
@click.argument("organization", metavar="ORGANIZATION_NAME", type=str, required=False)
@click.pass_context
def select_org_cmd(ctx, organization=None):
    """Allows you to switch organizations. If the organization argument
    is provided, this will directly select the specified organization.
    """
    api = ctx.obj.api
    config = ctx.parent.params["config"]
    commands.select_org(api, config, organization)


@cli.command("login")
@click.option(
    "--rsa-key",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to RSA key used for signing requests",
)
@click.pass_context
def login_cmd(ctx, api_root=None, analytics=True, rsa_key=None):
    """Authenticate to your Transcriptic account."""
    api = ctx.obj.api
    config = ctx.parent.params["config"]
    commands.login(api, config, api_root, analytics, rsa_key)


@cli.command("format", cls=FeatureCommand, feature="can_upload_packages")
@click.argument("manifest", default="manifest.json")
def format_cmd(manifest):
    """Check Autoprotocol format of manifest.json."""
    commands.format(manifest)


@cli.command("exec")
@click.argument("autoprotocol", type=click.File("r"), default=sys.stdin)
@click.option(
    "--api",
    "-a",
    help="The api endpoint of your test dashboard, or the scle test workcell instance (if used with --no-redirect).",
    required=True,
)
@click.option(
    "--no-redirect",
    help="If set, the api endpoint given is the scle test workcell instance.",
    is_flag=True,
)
@click.option(
    "--workcell-id",
    "-w",
    help="The workcell id to use for the device set (wc4-mcx1, tst-01-mcx-01, etc.). This is not permitted along with the `device-set` or `session-id` option.",
)
@click.option(
    "--device-set",
    "-d",
    type=click.File("r"),
    help="A DeviceSet json file to use for scheduling. This is not permitted along with the `workcell-id` or `session-id` options.",
)
@click.option(
    "--session-id",
    "-s",
    help="The session id of the session that should be used for scheduling this run. This is not permitted along with the `workcell-id` or `device-set` options.",
)
@click.option(
    "--time-limit",
    "-t",
    type=click.INT,
    default=30,
    help="The maximum time in seconds to spend scheduling. The scheduler will use all the time until an optimal solution is found.",
)
@click.option(
    "--schedule-at",
    default=None,
    help="The absolute time at which the given protocol should start (at the earliest). Absolute time format YYYY-MM-DDThh:mm in the local time of the target workcell (if year, month, or day is missing, it will be auto filled with the current values).",
)
@click.option(
    "--schedule-delay",
    type=click.INT,
    default=None,
    help="Delay in minutes at which the given protocol should start (at the earliest).",
)
@click.option(
    "--time-constraints-are-suggestion",
    "-tc-suggestion",
    help="If set, the time constraints will be considered only a suggestion.",
    is_flag=True,
)
@click.option(
    "--exclude",
    "-e",
    metavar="FILTER",
    help="Remove those instructions from the payload. e.g.: 0, 0-5, x_human, op:povision, x_human!:false",
    multiple=True,
)
@click.option(
    "--include",
    "-i",
    metavar="FILTER",
    help="Add those instructions to the payload after the --exclude has been applied.",
    multiple=True,
)
@click.option(
    "--partition-group-size",
    type=click.INT,
    default=None,
    help="The number of x_partition groups to be scheduled together.",
)
@click.option(
    "--partition-horizon",
    type=click.INT,
    default=None,
    help="The time in seconds to overlap partitions by.",
)
@click.option(
    "--partitioning-swap-device-id",
    default=None,
    help="The device id to use as a swap space when partitioning.",
)
@click.pass_context
def execute(
    ctx,
    autoprotocol,
    api,
    no_redirect,
    workcell_id,
    device_set,
    session_id,
    time_limit,
    schedule_at,
    schedule_delay,
    time_constraints_are_suggestion,
    exclude,
    include,
    partition_group_size,
    partition_horizon,
    partitioning_swap_device_id,
):
    """Send autoprotocol to a test workcell (no hardware) for scheduling."""
    commands.execute(
        autoprotocol,
        api,
        no_redirect,
        workcell_id,
        device_set,
        session_id,
        time_limit,
        schedule_at,
        schedule_delay,
        time_constraints_are_suggestion,
        exclude,
        include,
        partition_group_size,
        partition_horizon,
        partitioning_swap_device_id,
        ctx.obj.api.email,
    )
