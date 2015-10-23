import json
import requests
from transcriptic.objects import Run, Project

ctx = None

class AnalysisException(Exception):
  def __init__(self, message):
    self.message = message
  def __str__(self):
    return repr(self.message)

def _check_ctx(force_ctx):
  if not ctx and not force_ctx:
    raise Exception("No transcriptic.config.Connection context found!")

def _get_object(id, klass, force_ctx = None):
  _check_ctx(force_ctx)
  req = ctx.get("/-/%s" % id)
  if req.status_code == 200:
    data = req.json()
    return klass(data['id'], data)
  elif req.status_code == 404:
    raise Exception("[404] No object found for ID " + id)
  else:
    raise Exception("[%d] %s" % (req.status_code, req.text))

def run(id, force_ctx = None):
  _get_object(id, Run, force_ctx = force_ctx)

def project(id, force_ctx = None):
  _get_object(id, Project, force_ctx = force_ctx)

def container(id, force_ctx = None):
  _check_ctx(force_ctx)
  req = ctx.get("containers/%s" % id)
  if req.status_code == 200:
    return req.json()
  else:
    raise Exception(req.json())

def analyze(protocol, test_mode = False, force_ctx = None):
  _check_ctx(force_ctx)
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
