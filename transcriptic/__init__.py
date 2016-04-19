from transcriptic.objects import Run, Project, Aliquot, Resource
from transcriptic.objects import Container, Dataset, ProtocolPreview

ctx = None


def _get_object(obj_id, klass):
    data = ctx._get_object(obj_id)
    return klass(data['id'], data, connection=ctx)


def run(obj_id):
    return _get_object(obj_id, Run)


def project(obj_id):
    return _get_object(obj_id, Project)


def resource(obj_id):
    return _get_object(obj_id, Resource)


def aliquot(obj_id):
    return _get_object(obj_id, Aliquot)


def container(obj_id):
    return _get_object(obj_id, Container)


def preview(protocol):
    return ProtocolPreview(protocol, connection=ctx)


def analyze(protocol, test_mode=False):
    return ctx.analyze_run(protocol, test_mode)


def submit(protocol, project_id, title=None, test_mode=False):
    return ctx.submit_run(protocol, project_id=project_id, title=title, test_mode=test_mode)


def dataset(obj_id, key="*"):
    return ctx.dataset(obj_id=obj_id, key=key)
