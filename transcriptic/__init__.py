from past.builtins import basestring
import os
import json
import requests
from transcriptic.objects import Run, Project, Aliquot, Resource, Container, Dataset, ProtocolPreview
from autoprotocol import Protocol
import sys

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
  return _get_object(id, Container)

def preview(protocol):
  _check_ctx()
  return ProtocolPreview(protocol, connection = ctx)

def analyze(protocol, test_mode = False):
  _check_ctx()
  if isinstance(protocol, Protocol):
      protocol = protocol.as_dict()
  if "errors" in protocol:
      raise AnalysisException(("Error%s in protocol:\n%s" %
      (("s" if len(protocol["errors"]) > 1 else ""),
        "".join(["- " + e['message'] + "\n" for
        e in protocol["errors"]]))))

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

def submit(protocol, project, title = None, test_mode = False):
  _check_ctx()
  if isinstance(protocol, Protocol):
      protocol = protocol.as_dict()
  req = ctx.post('%s/runs' % project, data = json.dumps({
    "title": title,
    "protocol": protocol,
    "test_mode": test_mode
  }))
  if req.status_code == 201:
    return req.json()
  elif req.status_code == 404:
    raise AnalysisException("Error: Couldn't create run (404). \nAre you sure the project %s "
               "exists, and that you have access to it?" % ctx.url(project))
  elif req.status_code == 422:
    raise AnalysisException("Error creating run: %s" % req.text)
  else:
    raise Exception("[%d] %s" % (req.status_code, req.text))

def dataset(id, key = "*"):
  _check_ctx()
  req = ctx.get("/data/%s.json?key=%s" % (id, key))
  if req.status_code == 200:
    data = req.json()
    return Dataset(id, data, connection = ctx)
  else:
    raise Exception("[%d] %s" % (req.status_code, req.text))
