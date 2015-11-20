from builtins import object
import json
import requests
import pandas
from autoprotocol import Protocol

class ProtocolPreview(object):
  def __init__(self, protocol, connection):
    self.protocol = protocol
    req = connection.post("/runs/preview", json = {
      "protocol": json.dumps(protocol.as_dict()) if isinstance(protocol, Protocol) else protocol
    }, allow_redirects = False)
    if req.status_code == 302:
      self.preview_url = req.headers['Location']
    else:
      raise Exception("Cannot preview protocol.")

  def _repr_html_(self):
    return """<iframe src="%s" frameborder="0" allowtransparency="true" style="height:500px;" seamless></iframe>""" %  \
      self.preview_url

class Instructions(object):
  '''
  An instruction object contains raw instructions as JSON as well as list of
  operations and warps generated from the raw instructions.

  Parameters
  ----------

  raw_instructions : dict
    raw instruction dictionary

  '''
  def __init__(self, raw_instructions):
    self.raw_instructions = raw_instructions
    op_name_list = []
    op_warp_list = []
    for instruction in raw_instructions:
      op_name_list.append(instruction["operation"]["op"])
      op_warp_list.append(instruction["warps"])
    instruct_dict = {}
    instruct_dict["name"] = op_name_list
    instruct_dict["warp_list"] = op_warp_list
    self.df = pandas.DataFrame(instruct_dict)

class Dataset(object):
  def __init__(self, id, attributes, connection = False):
    super(Dataset, self).__init__()
    self.id = id
    self.attributes = attributes
    self.connection = connection
    # self.df = pandas.DataFrame(attributes)

  def _repr_html_(self):
    return """<iframe src="%s" frameborder="0" allowtransparency="true" style="height:500px;" seamless></iframe>""" % \
      self.connection.url("/data/%s.embed" % self.id)

class Run(object):
  def __init__(self, id, attributes, connection = False):
    super(Run, self).__init__()
    self.id = id
    self.attributes = attributes
    self.instructions = Instructions(self.attributes["instructions"])
    self.connection = connection

  def monitoring(self, instruction_id, data_type = 'pressure'):
    req = self.connection.get("%s/runs/%s/%s/monitoring/%s" % (
      self.attributes['project']['url'],
      self.id,
      instruction_id,
      data_type
    ))
    if req.status_code == 200:
      response = req.json()
      return pandas.DataFrame(response['results'])
    else:
      raise Exception(req.text)

  def data(self):
    req = self.connection.get("%s/runs/%s/data" % (
      self.attributes['project']['url'],
      self.id
    ))
    if req.status_code == 200:
      response = req.json()
      return {k: Dataset(response[k]["id"], response[k], connection = self.connection) for k in list(response.keys())}
    elif req.status_code == 404:
      raise Exception("[404] No run found for ID " + id)
    else:
      raise Exception("[%d] %s" % (req.status_code, req.json()))

  def _repr_html_(self):
    return """<iframe src="%s" frameborder="0" allowtransparency="true" style="height:450px;" seamless></iframe>""" % \
      self.connection.url("%s/runs/%s.embed" % (self.attributes['project']['url'], self.id))

class Project(object):
  def __init__(self, id, attributes, connection = False):
    super(Project, self).__init__()
    self.id = id
    self.attributes = attributes
    self.connection = connection

  def runs(self):
    req = self.connection.get("%s/runs" % self.id)
    if req.status_code == 200:
      runs = req.json()
      return [Run(run['id'], run, self.connection) for run in runs]
    else:
      raise Exception(req.text)

  def submit(protocol, title, test_mode = False):
    from transcriptic import submit as api_submit
    req_json = api_submit(protocol, self.id, title, test_mode)
    return Run(req_json['id'], req_json)

class Aliquot(object):
  def __init__(self, id, attributes, connection = False):
    super(Aliquot, self).__init__()
    self.id = id
    self.attributes = attributes
    self.connection = connection

class Container(object):
  def __init__(self, id, attributes, connection = False):
    super(Container, self).__init__()
    self.id = id
    self.attributes = attributes
    self.connection = connection

class Resource(object):
  def __init__(self, id, attributes, connection = False):
    super(Resource, self).__init__()
    self.id = id
    self.attributes = attributes
    self.connection = connection
