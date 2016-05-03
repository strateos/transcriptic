from __future__ import print_function
from transcriptic.objects import Run, Project, Aliquot, Resource
from transcriptic.objects import Container, Dataset, ProtocolPreview
from transcriptic.config import Connection
from .version import __version__

api = None


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
    return ProtocolPreview(protocol, connection=api)


def analyze(protocol, test_mode=False):
    return api.analyze_run(protocol, test_mode)


def submit(protocol, project_id, title=None, test_mode=False):
    return api.submit_run(protocol, project_id=project_id, title=title, test_mode=test_mode)


def dataset(data_id, key="*"):
    return api.dataset(data_id=data_id, key=key)


def connect(transcriptic_path="~/.transcriptic"):
    #TODO: Mirror login code from CLI
    try:
        api = Connection.from_file(transcriptic_path)
    except:
        print ("Unable to find .transcriptic file, please ensure the right path is provided")
