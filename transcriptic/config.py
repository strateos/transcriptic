from __future__ import print_function
from builtins import object
import requests
import json
import transcriptic
import os
from os.path import expanduser
from transcriptic.objects import Project


class Connection(object):
  def __init__(
      self, email = None, token = None, organization_id = False, api_root = "https://secure.transcriptic.com", organization = False,
      cookie = False, verbose = False
    ):
    if email is None:
      email = os.environ['USER_EMAIL']
      token = os.environ['USER_TOKEN']
      organization_id = os.environ['USER_ORGANIZATION']
    self.api_root = api_root
    self.email = email
    self.token = token
    self.organization_id = organization_id or organization
    self.verbose = verbose
    self.default_headers = {
      "X-User-Email": email,
      "X-User-Token": token,
      "Content-Type": "application/json",
      "Accept": "application/json"
    }
    transcriptic.ctx = self

  @staticmethod
  def from_file(path):
    with open(expanduser(path), 'r') as f:
      cfg = json.loads(f.read())
      return Connection(**cfg)

  def save(self, path):
    with open(expanduser(path), 'w') as f:
      f.write(json.dumps({
        'email': self.email,
        'token': self.token,
        'organization_id': self.organization_id,
        'api_root': self.api_root,
      }, indent=2))

  def url(self, path):
    if path.startswith("/"):
      return "%s%s" % (self.api_root, path)
    else:
      return "%s/%s/%s" % (self.api_root, self.organization_id, path)

  def projects(self):
    req = self.get('?q=&per_page=500')
    if req.status_code == 200:
      return [Project(project['id'], project, connection = self) for project in req.json()['projects']]
    else:
      raise RuntimeError(
        "There was an error listing the projects in your "
        "organization.  Make sure your login details are correct."
      )

  def project(self, project_id):
    req = self.get(project_id)
    if req.status_code == 200:
      return Project(project_id, req.json(), connection = self)
    else:
      raise RuntimeError(
        "There was an error fetching project %s" % project_id
      )

  def runs(self, project_id):
    req = self.get(project_id)
    if req.status_code == 200:
      return req.json()
    else:
      raise RuntimeError(
        "There was an error fetching the runs in project %s" % project_id
      )

  def create_project(self, title):
    req = self.post('', data = json.dumps({
      'name': title
    }))
    if req.status_code == 201:
      data = req.json()
      return Project(data['id'], data, connection = self)
    else:
      raise RuntimeError(req.text)

  def delete_project(self, project_id):
    req = self.delete(project_id)
    if req.status_code == 200:
      return True

  def archive_project(self, project_id):
    req = self.put(project_id, data = json.dumps({"project": {"archived": True}}))
    if req.status_code == 200:
      return True
    else:
      raise RuntimeError(req.json())

  def packages(self):
    req = self.get("packages")
    if req.status_code == 200:
      return req.json()
    else:
      raise RuntimeError(req.text)

  def package(self, package_id):
    req = self.get("packages/%s" % package_id)
    if req.status_code == 200:
      return req.json()
    else:
      raise RuntimeError(req.text)

  def resources(self, query):
    req = self.get("/_commercial/kits?q=%s&per_page=1000" % query)
    return req.json()

  def create_package(self, name, description):
    req = self.post('packages', data = json.dumps({
      "name": "%s%s" % ("com.%s." % self.organization_id, name),
      "description": description
    }))
    if req.status_code == 200:
      return req.json()
    else:
      raise RuntimeError(req.text)

  def delete_package(self, id):
    req = self.delete('packages/%s' % id)
    if req.status_code == 200:
        return True

  def post(self, path, **kwargs):
    if self.verbose: print ("POST %s" %  self.url(path))
    return requests.post(self.url(path), headers = self._merge_headers(kwargs), **kwargs)

  def put(self, path, **kwargs):
    if self.verbose: print ("PUT %s" %  self.url(path))
    return requests.put(self.url(path), headers = self._merge_headers(kwargs), **kwargs)

  def get(self, path, **kwargs):
    if self.verbose: print ("GET %s" %  self.url(path))
    return requests.get(self.url(path), headers = self._merge_headers(kwargs), **kwargs)

  def delete(self, path, **kwargs):
    if self.verbose: print ("DELETE %s" %  self.url(path))
    return requests.delete(self.url(path), headers = self._merge_headers(kwargs), **kwargs)

  def _merge_headers(self, kwargs):
    default_headers = self.default_headers
    default_headers.update(kwargs.pop('headers', {}))
    return default_headers
