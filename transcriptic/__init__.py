from __future__ import print_function
from transcriptic.objects import Run, Project, Aliquot, Resource, _check_ctx
from transcriptic.objects import Container, Dataset, ProtocolPreview
from transcriptic.config import Connection

ctx = None
__version__ = "2.2.1"

def run(obj_id):
    return Run(obj_id)


def project(obj_id):
    return Project(obj_id)


def resource(obj_id):
    return Resource(obj_id)


def aliquot(obj_id):
    return Aliquot(obj_id)


def container(obj_id):
    return Container(obj_id)


def preview(protocol):
    return ProtocolPreview(protocol, connection=ctx)


def analyze(protocol, test_mode=False):
    return ctx.analyze_run(protocol, test_mode)


def submit(protocol, project_id, title=None, test_mode=False):
    return ctx.submit_run(protocol, project_id=project_id, title=title, test_mode=test_mode)


def dataset(data_id, key="*"):
    return ctx.dataset(data_id=data_id, key=key)


def connect(transcriptic_path="~/.transcriptic"):
    #TODO: Mirror login code from CLI
    try:
        ctx = Connection.from_file(transcriptic_path)
    except:
        print ("Unable to find .transcriptic file, please ensure the right path is provided")
