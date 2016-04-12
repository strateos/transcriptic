from __future__ import print_function
from builtins import object
import requests
import json
import transcriptic
import os
from os.path import expanduser
from transcriptic.objects import Project
from . import api
from . import routes


class Connection(object):

    def __init__(
        self, email=None, token=None, organization_id=False,
        api_root="https://secure.transcriptic.com", organization=False,
        cookie=False, verbose=False
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
        self.headers = {
            "X-User-Email": email,
            "X-User-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Save relevant information required for get_route helper
        self.default_route_args = dict(api_root=self.api_root, org_id=self.organization_id)
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
        route = self.get_route('get_projects')
        req = api.get(route)
        if req.status_code == 200:
            return [Project(project['id'], project, connection=self) for
                    project in req.json()['projects']]
        else:
            raise RuntimeError(
                "There was an error listing the projects in your "
                "organization.  Make sure your login details are correct."
            )

    def project(self, project_id):
        route = self.get_route('get_project', project_id=project_id)
        req = api.get(route)
        if req.status_code == 200:
            return Project(project_id, req.json(), connection=self)
        else:
            raise RuntimeError(
                "There was an error fetching project %s" % project_id
            )

    def runs(self, project_id):
        route = self.get_route('get_project_runs', project_id=project_id)
        req = api.get(route)
        if req.status_code == 200:
            return req.json()
        else:
            raise RuntimeError(
                "There was an error fetching the runs in project %s" %
                project_id
            )

    def create_project(self, title):
        route = self.get_route('create_project')
        req = api.post(route, data=json.dumps({
            'name': title
        }))
        if req.status_code == 201:
            data = req.json()
            return Project(data['id'], data, connection=self)
        else:
            raise RuntimeError(req.text)

    def delete_project(self, project_id):
        route = self.get_route('delete_project', project_id=project_id)
        req = api.delete(route)
        if req.status_code == 200:
            return True

    def archive_project(self, project_id):
        route = self.get_route('archive_project', project_id=project_id)
        req = api.put(route, data=json.dumps({"project": {"archived": True}}))
        if req.status_code == 200:
            return True
        else:
            raise RuntimeError(req.json())

    def packages(self):
        route = self.get_route("get_packages")
        req = api.get(route)
        if req.status_code == 200:
            return req.json()
        else:
            raise RuntimeError(req.text)

    def package(self, package_id):
        route = self.get_route("get_package", package_id=package_id)
        req = api.get(route)
        if req.status_code == 200:
            return req.json()
        else:
            raise RuntimeError(req.text)

    def create_package(self, name, description):
        route = self.get_route('create_package')
        req = api.post(route, data=json.dumps({
            "name": "%s%s" % ("com.%s." % self.organization_id, name),
            "description": description
        }))
        if req.status_code == 201:
            return req.json()
        else:
            raise RuntimeError(req.text)

    def delete_package(self, package_id):
        route = self.get_route('delete_package', package_id=package_id)
        req = api.delete(route)
        if req.status_code == 200:
            return True

    def post_release(self, package_id, data):
        route = self.get_route('post_release', package_id=package_id)
        req = api.post(route, data=data)
        if req.status_code == 201:
            return req.json()
        else:
            raise RuntimeError(req.text)

    def get_release_status(self, package_id, release_id, timestamp):
        route = self.get_route('get_release_status', package_id=package_id, release_id=release_id, timestamp=timestamp)
        req = api.get(route)
        if req.status_code == 200:
            return req.json()
        else:
            raise RuntimeError(req.text)

    def get_quick_launch(self, project_id, quick_launch_id):
        route = self.get_route('get_quick_launch', project_id=project_id, quick_launch_id=quick_launch_id)
        req = api.get(route)
        if req.status_code == 200:
            return req.json()
        else:
            raise RuntimeError(req.text)

    def create_quick_launch(self, project_id, quick_launch_id, data):
        route = self.get_route('create_quick_launch', project_id=project_id, quick_launch_id=quick_launch_id)
        req = api.post(route, data=data)
        if req.status_code == 201:
            return req.json()
        else:
            raise RuntimeError(req.text)

    def resources(self, query):
        route = self.get_route('query_resources', query=query)
        req = api.get(route)
        return req.json()

    def post(self, path, **kwargs):
        if self.verbose:
            print("POST %s" % self.url(path))
        return requests.post(self.url(path),
                             headers=self._merge_headers(kwargs),
                             **kwargs)

    def put(self, path, **kwargs):
        if self.verbose:
            print("PUT %s" % self.url(path))
        return requests.put(self.url(path),
                            headers=self._merge_headers(kwargs),
                            **kwargs)

    def get(self, path, **kwargs):
        if self.verbose:
            print("GET %s" % self.url(path))
        return requests.get(self.url(path),
                            headers=self._merge_headers(kwargs),
                            **kwargs)

    def delete(self, path, **kwargs):
        if self.verbose:
            print("DELETE %s" % self.url(path))
        return requests.delete(self.url(path),
                               headers=self._merge_headers(kwargs),
                               **kwargs)

    def get_route(self, method, **kwargs):
        """Helper function to automatically match and supply required arguments"""
        route_method = getattr(routes, method)
        route_method_args = route_method.__code__.co_varnames
        return route_method(*(dict(self.default_route_args, **kwargs)[arg] for arg in route_method_args))

    def update_headers(self, kwargs):
        """Helper function to safely merge and update headers"""
        self.headers.update(**kwargs)
        return self.headers

    def _merge_headers(self, kwargs):
        return dict(kwargs.pop('headers', {}), **self.headers)
