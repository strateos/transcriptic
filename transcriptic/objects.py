import json
import requests
import pandas
from transcriptic.ipython import Render

class Instructions(object):
  def __init__(self, raw_instructions):
    self.raw_instructions = raw_instructions
    op_name_list = []
    op_warp_list = []
    for instruction in raw_instructions:
      op_name_list.append(instruction["operation"]["op"])
      """
      if instruction["operation"]["op"] == "pipette":
          temp_list = []
          for warp in instruction["warps"]:
              temp_list.append(Pipette_Warp(warp))
      else:
          op_warp_list.append(instruction["warps"])
      """
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

class Run(object):
  def __init__(self, id, props, connection = False):
    super(Run, self).__init__()
    self.id = id
    self.attributes = props
    self.instructions = Instructions(self.attributes["instructions"])
    self.connection = connection

  def monitoring(self, instruction_id, data_type = 'pressure'):
    req = self.connection.get("%s/runs/%s/%s/monitoring/%s" % (
      self.attributes['project']['url'],
      self.id,
      self.attributes['instructions'][1]['id'],
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
      return {k: Dataset(k, v) for k, v in response.iteritems()}
    elif req.status_code == 404:
      raise Exception("[404] No run found for ID " + id)
    else:
      raise Exception("[%d] %s" % (req.status_code, req.json()))

  def _repr_html_(self):
    return Render(self)._repr_html_()

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
      return [Run(run['id'], run) for run in runs]
    else:
      raise Exception(req.text)

  def launch(protocol, title, test_mode = False):
    req = self.connection.post("%s/runs" % self.id, data = json.dumps({
      "title": title,
      "protocol": protocol.as_dict(),
      "test_mode": test_mode
    }))
    if req.status_code == 201:
      data = req.json()
      return Run(data['id'], data)
    else:
      raise Exception(req.text)

class Aliquot(object):
  def __init__(self, id, attributes, connection = False):
    super(Aliquot, self).__init__()
    self.id = id
    self.attributes = attributes
    self.connection = connection

class Resource(object):
  def __init__(self, id, attributes, connection = False):
    super(Resource, self).__init__()
    self.id = id
    self.attributes = attributes
    self.connection = connection
