from __future__ import print_function
from builtins import object
import json
import transcriptic
import os
from os.path import expanduser
from transcriptic.objects import Project
from . import api
from . import routes
from autoprotocol import Protocol


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

        # Preload known environment arguments
        self.env_args = dict(api_root=self.api_root, org_id=self.organization_id)
        transcriptic.ctx = self

    @staticmethod
    def from_file(path):
        """Loads context from file"""
        with open(expanduser(path), 'r') as f:
            cfg = json.loads(f.read())
            return Connection(**cfg)

    def save(self, path):
        """Saves context into file"""
        with open(expanduser(path), 'w') as f:
            f.write(json.dumps({
                'email': self.email,
                'token': self.token,
                'organization_id': self.organization_id,
                'api_root': self.api_root,
            }, indent=2))

    def update_environment(self, **kwargs):
        """Update environment variables. To remove an existing variable, set to None"""
        self.env_args = dict(self.env_args, **kwargs)

    def url(self, path):
        if path.startswith("/"):
            return "%s%s" % (self.api_root, path)
        else:
            return "%s/%s/%s" % (self.api_root, self.organization_id, path)

    def preview_protocol(self, protocol):
        route = self.get_route('preview_protocol')
        return api.post(route,
                        json={
                            "protocol": json.dumps(protocol.as_dict()) if
                            isinstance(protocol, Protocol) else protocol
                        },
                        allow_redirects=False,
                        status_response={
                            '302': lambda resp: resp.headers['Location'],
                            'default': lambda resp: Exception("cannot preview protocol.")
                        })

    def projects(self):
        route = self.get_route('get_projects')
        data = api.get(route, status_response={
            'default': lambda resp: RuntimeError(
                "There was an error listing the projects in your "
                "organization.  Make sure your login details are correct."
            )
        })
        return [Project(project['id'], project, connection=self) for
                project in data['projects']]

    def project(self, project_id=None):
        route = self.get_route('get_project', project_id=project_id)
        data = api.get(route, status_response={
            'default': lambda resp: RuntimeError(
                "There was an error fetching project %s" % project_id
            )
        })
        return Project(project_id, data, connection=self)

    def runs(self, project_id=None):
        route = self.get_route('get_project_runs', project_id=project_id)
        return api.get(route, status_response={
            "default": lambda resp: RuntimeError(
                "There was an error fetching the runs in project %s" %
                project_id
            )
        })

    def create_project(self, title):
        route = self.get_route('create_project')
        data = api.post(route, data=json.dumps({
            'name': title
        }))
        return Project(data['id'], data, connection=self)

    def delete_project(self, project_id=None):
        route = self.get_route('delete_project', project_id=project_id)
        return api.delete(route, status_response={
            '200': lambda resp: True
        })

    def archive_project(self, project_id=None):
        route = self.get_route('archive_project', project_id=project_id)
        return api.put(route, data=json.dumps({"project": {"archived": True}}),
                       status_response={
                           '200': lambda resp: True
                       })

    def packages(self):
        route = self.get_route("get_packages")
        return api.get(route)

    def package(self, package_id=None):
        route = self.get_route("get_package", package_id=package_id)
        return api.get(route)

    def create_package(self, name, description):
        route = self.get_route('create_package')
        return api.post(route, data=json.dumps({
            "name": "%s%s" % ("com.%s." % self.organization_id, name),
            "description": description
        }))

    def delete_package(self, package_id=None):
        route = self.get_route('delete_package', package_id=package_id)
        return api.delete(route)

    def post_release(self, data, package_id=None):
        route = self.get_route('post_release', package_id=package_id)
        return api.post(route, data=data)

    def get_release_status(self, package_id=None, release_id=None, timestamp=None):
        route = self.get_route('get_release_status', package_id=package_id, release_id=release_id, timestamp=timestamp)
        return api.get(route)

    def get_quick_launch(self, project_id=None, quick_launch_id=None):
        route = self.get_route('get_quick_launch', project_id=project_id, quick_launch_id=quick_launch_id)
        return api.get(route)

    def create_quick_launch(self, data, project_id=None):
        route = self.get_route('create_quick_launch', project_id=project_id)
        return api.post(route, data=data)

    def resources(self, query):
        route = self.get_route('query_resources', query=query)
        return api.get(route)

    def monitoring_data(self, data_type, project_id=None, run_id=None, instruction_id=None):
        route = self.get_route('monitoring_data', project_id=project_id, run_id=run_id,
                               instruction_id=instruction_id, data_type=data_type)
        return api.get(route)

    def raw_image_data(self, data_id=None):
        route = self.get_route('view_raw_image', data_id=data_id)
        return api.get(route, status_response={'200': lambda resp: resp}, stream=True)

    def _get_object(self, obj_id):
        route = self.get_route('def_route', obj_id=obj_id)
        return api.get(route, status_response={
            '404': Exception("[404] No object found for ID " + obj_id)
        })

    def analyze_run(self, protocol, test_mode=False):
        if isinstance(protocol, Protocol):
            protocol = protocol.as_dict()
        if "errors" in protocol:
            raise AnalysisException(("Error%s in protocol:\n%s" %
                                     (("s" if len(protocol["errors"]) > 1 else ""),
                                      "".join(["- " + e['message'] + "\n" for
                                               e in protocol["errors"]]))))

        def error_string(r):
            return AnalysisException("Error%s in protocol:\n%s" %
                                     (("s" if len(r.json()['protocol']) > 1 else ""),
                                      "".join(["- " + e['message'] + "\n" for e in r.json()['protocol']])
                                      ))

        return api.post(self.get_route('analyze_run'),
                        data=json.dumps({
                            "protocol": protocol,
                            "test_mode": test_mode
                        }),
                        status_response={'422': lambda response: error_string(response)})

    def submit_run(self, protocol, project_id=None, title=None, test_mode=False):
        if isinstance(protocol, Protocol):
            protocol = protocol.as_dict()
        return api.post(self.get_route('submit_run', project_id=project_id),
                        data=json.dumps({
                            "title": title,
                            "protocol": protocol,
                            "test_mode": test_mode
                        }),
                        status_response={
                            '404': lambda resp: AnalysisException("Error: Couldn't create run (404). \n"
                                                                  "Are you sure the project %s "
                                                                  "exists, and that you have access to it?" %
                                                                  self.url(project_id)),
                            '422': lambda resp: AnalysisException("Error creating run: %s" % resp.text)
                        })

    def dataset(self, obj_id, key="*"):
        route = self.get_route('dataset', obj_id=obj_id, key=key)
        return api.get(route)

    def datasets(self, project_id=None, run_id=None):
        route = self.get_route(project_id=project_id, run_id=run_id)
        return api.get(route, status_response={
            '404': lambda resp: Exception("[404] No run found for ID " + id)
        })

    def get_route(self, method, **kwargs):
        """Helper function to automatically match and supply required arguments"""
        route_method = getattr(routes, method)
        route_method_args = route_method.__code__.co_varnames
        # Update loaded argument dictionary with additional arguments
        arg_dict = dict(self.env_args, **kwargs)
        input_args = []
        for arg in route_method_args:
            if arg_dict[arg]:
                input_args.append(arg_dict[arg])
            else:
                raise Exception("For route: {0}, argument {1} needs to be provided.".format(method, arg))

        return route_method(*tuple(input_args))

    def update_headers(self, kwargs):
        """Helper function to safely merge and update headers"""
        self.headers.update(**kwargs)
        return self.headers

    def _merge_headers(self, kwargs):
        return dict(kwargs.pop('headers', {}), **self.headers)


class AnalysisException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
