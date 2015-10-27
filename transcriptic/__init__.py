import json
import requests
from transcriptic.objects import Run, Project, Aliquot, Resource

ctx = None

class AnalysisException(Exception):
  def __init__(self, message):
    self.message = message
  def __str__(self):
    return self.message

def _check_ctx():
  if not ctx:
    raise Exception("No transcriptic.config.Connection context found!")

def _get_object(id, klass):
  _check_ctx()
  req = ctx.get("/-/%s" % id)
  if req.status_code == 200:
    data = req.json()
    return klass(data['id'], data, connection = ctx)
  elif req.status_code == 404:
    raise Exception("[404] No object found for ID " + id)
  else:
    raise Exception("[%d] %s" % (req.status_code, req.text))

def run(id):
  return _get_object(id, Run)

def project(id):
  return _get_object(id, Project)

def resource(id):
  return _get_object(id, Resource)

def aliquot(id):
  return _get_object(id, Aliquot)

def container(id):
  _check_ctx()
  req = ctx.get("containers/%s" % id)
  if req.status_code == 200:
    return req.json()
  else:
    raise Exception(req.json())

def analyze(protocol, test_mode = False):
  _check_ctx()
  req = ctx.post('analyze_run', data = json.dumps({
    "protocol": protocol,
    "test_mode": test_mode
  }))
  if req.status_code == 200:
    return req.json()
  elif req.status_code == 422:
    raise AnalysisException(("Error%s in protocol:\n%s" %
      (("s" if len(req.json()['protocol']) > 1 else ""),
        "".join(["- " + e['message'] + "\n" for
        e in req.json()['protocol']]))))
  else:
    raise Exception("[%d] %s" % (req.status_code, req.text))

def dataset(id, key = "*"):
  _check_ctx()
  req = ctx.get("data/%s.json?key=%s" % (id, key))
  if req.status_code == 200:
    return req.json()
  else:
    raise Exception(req.json())
