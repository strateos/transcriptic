from __future__ import print_function
from builtins import object, str
import json
import transcriptic
import os
from os.path import expanduser
from . import routes
from autoprotocol import Protocol
import requests
from .version import __version__
import platform
import inspect


class Connection(object):
    """
    A Connection object is the object used for communicating with Transcriptic.

    Local usage: This is most easily instantiated by using the `from_file` function after
    calling `transcriptic login` from the command line.

    .. code-block:: shell
        :caption: shell

        $ transcriptic login
        Email: me@example.com
        Password:
        Logged in as me@example.com (example-lab)

    .. code-block:: python
        :caption: python

        from transcriptic.config import Connection
        api = Connection.from_file("~/.transcriptic")

    For those using Jupyter notebooks on secure.transcriptic.com (beta), a Connection object is automatically
    instatianted as api.

    .. code-block:: python
        :caption: python

        from transcriptic import api

    The `api` object can then be used for making any api calls. It is recommended to use the objects
    in `transcriptic.objects` since that wraps the response in a more friendly format.

    Example Usage:

    .. code-block:: python
        :caption: python

        api.projects()
        api.runs(project_id="p123456789")

    If you have multiple organizations and would like to switch to a specific organization, or if you
    would like to auto-load certain projects, you can use the `update_environment` function call.

    Example Usage:

    .. code-block:: python
        :caption: python

        api.update_environment(org_id="my_other_org", project_id="p123")


    """
    def __init__(self, email=None, token=None, organization_id=False,
                 api_root="https://secure.transcriptic.com", organization=False,
                 cookie=False, verbose=False, use_environ=True, analytics=True, user_id="default"):
        if email is None and use_environ:
            email = os.environ['USER_EMAIL']
            token = os.environ['USER_TOKEN']
            organization_id = os.environ['USER_ORGANIZATION']
        self.api_root = api_root
        self.email = email
        self.token = token
        self.organization_id = organization_id or organization
        self.verbose = verbose
        self.analytics = analytics
        self.user_id = user_id
        self.headers = {
            "X-User-Email": email,
            "X-User-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "txpy/{} ({}/{}; {}/{}; {}; {})".format(__version__,
                                                                  platform.python_implementation(),
                                                                  platform.python_version(),
                                                                  platform.system(),
                                                                  platform.release(),
                                                                  platform.machine(),
                                                                  platform.architecture()[0])
        }
        # Preload known environment arguments
        self.env_args = dict(api_root=self.api_root, org_id=self.organization_id)
        transcriptic.api = self

    @staticmethod
    def from_file(path):
        """Loads connection from file"""
        with open(expanduser(path), 'r') as f:
            cfg = json.loads(f.read())
            expected_keys = ['email', 'token', 'organization_id', 'api_root', 'analytics', "user_id"]

            def key_not_found(): raise OSError("Key not found")
            [key_not_found() for key in expected_keys if key not in cfg.keys()]
            return Connection(**cfg)

    def save(self, path):
        """Saves current connection into file"""
        with open(expanduser(path), 'w') as f:
            f.write(json.dumps({
                'email': self.email,
                'token': self.token,
                'organization_id': self.organization_id,
                'api_root': self.api_root,
                'analytics': self.analytics,
                'user_id': self.user_id
            }, indent=2))

    def update_environment(self, **kwargs):
        """Update environment variables. To remove an existing variable, set to None"""
        self.env_args = dict(self.env_args, **kwargs)

    def url(self, path):
        """url format helper"""
        if path.startswith("/"):
            return "%s%s" % (self.env_args['api_root'], path)
        else:
            return "%s/%s/%s" % (self.env_args['api_root'], self.env_args['org_id'], path)

    def preview_protocol(self, protocol):
        """Post protocol preview"""
        route = self.get_route('preview_protocol')
        return self.post(route,
                         json={
                             "protocol": json.dumps(protocol.as_dict()) if
                             isinstance(protocol, Protocol) else protocol
                         },
                         allow_redirects=False,
                         status_response={
                             '302': lambda resp: resp.headers['Location'],
                             'default': lambda resp: Exception("cannot preview protocol.")
                         })

    def organizations(self):
        """Get list of organizations"""
        route = self.get_route('get_organizations')
        return self.get(route)

    def get_organization(self, org_id=None):
        """Get particular organization"""
        route = self.get_route('get_organization', org_id=org_id)
        resp = self.get(route, status_response={
            '200': lambda resp: resp,
            '404': lambda resp: RuntimeError('There was an error fetching the organization {}'.format(org_id)),
            'default': lambda resp: resp
        })
        return resp

    def projects(self):
        """Get list of projects in organization"""
        route = self.get_route('get_projects')
        return self.get(route, status_response={
            '200': lambda resp: resp.json()["projects"],
            'default': lambda resp: RuntimeError(
                "There was an error listing the projects in your "
                "organization.  Make sure your login details are correct."
            )
        })

    def project(self, project_id=None):
        """Get particular project"""
        route = self.get_route('get_project', project_id=project_id)
        return self.get(route, status_response={
            'default': lambda resp: RuntimeError(
                "There was an error fetching project %s" % project_id
            )
        })

    def runs(self, project_id=None):
        """Get list of runs in project"""
        route = self.get_route('get_project_runs', project_id=project_id)
        return self.get(route, status_response={
            "200": lambda resp: resp.json(),
            "default": lambda resp: RuntimeError(
                "There was an error fetching the runs in project %s" %
                project_id
            )
        })

    def create_project(self, title):
        """Create project with given title"""
        route = self.get_route('create_project')
        return self.post(route, data=json.dumps({
            'name': title
        }))

    def delete_project(self, project_id=None):
        """Delete project with given project_id"""
        route = self.get_route('delete_project', project_id=project_id)
        return self.delete(route, status_response={
            '200': lambda resp: True
        })

    def archive_project(self, project_id=None):
        """Archive project with given project_id"""
        route = self.get_route('archive_project', project_id=project_id)
        return self.put(route, data=json.dumps({"project": {"archived": True}}),
                        status_response={
                            '200': lambda resp: True
                        })

    def packages(self):
        """Get list of packages in organization"""
        route = self.get_route("get_packages")
        return self.get(route)

    def package(self, package_id=None):
        """Get package with given package_id"""
        route = self.get_route("get_package", package_id=package_id)
        return self.get(route)

    def create_package(self, name, description):
        """Create package with given name and description"""
        route = self.get_route('create_package')
        return self.post(route, data=json.dumps({
            "name": "%s%s" % ("com.%s." % self.organization_id, name),
            "description": description
        }))

    def delete_package(self, package_id=None):
        """Delete package with given package_id"""
        route = self.get_route('delete_package', package_id=package_id)
        return self.delete(route, status_response={'200': lambda resp: True})

    def post_release(self, data, package_id=None):
        """Create release with given data and package_id"""
        route = self.get_route('post_release', package_id=package_id)
        return self.post(route, data=data)

    def get_release_status(self, package_id=None, release_id=None, timestamp=None):
        """Get status of current release upload"""
        route = self.get_route('get_release_status', package_id=package_id, release_id=release_id, timestamp=timestamp)
        return self.get(route)

    def get_quick_launch(self, project_id=None, quick_launch_id=None):
        """Get quick launch object"""
        route = self.get_route('get_quick_launch', project_id=project_id, quick_launch_id=quick_launch_id)
        return self.get(route)

    def create_quick_launch(self, data, project_id=None):
        """Create quick launch object"""
        route = self.get_route('create_quick_launch', project_id=project_id)
        return self.post(route, data=data)

    def launch_protocol(self, params, protocol_id=None):
        """Launch protocol-id with params"""
        route = self.get_route('launch_protocol', protocol_id=protocol_id)
        return self.post(route, data=params)

    def get_launch_request(self, protocol_id=None, launch_request_id=None):
        """Get launch request id"""
        route = self.get_route('get_launch_request', protocol_id=protocol_id, launch_request_id=launch_request_id)
        return self.get(route)

    def get_protocols(self):
        """Get list of available protocols"""
        route = self.get_route('get_protocols')
        return self.get(route)

    def resources(self, query):
        """Get resources"""
        route = self.get_route('query_resources', query=query)
        return self.get(route)

    def inventory(self, query, timeout=30.0, page=0):
        """Get inventory"""
        route = self.get_route('query_inventory', query=query, page=page)
        return self.get(route, timeout=timeout)

    def kits(self, query):
        """Get kits"""
        route = self.get_route('query_kits', query=query)
        return self.get(route)

    def monitoring_data(self, data_type, instruction_id=None, grouping=None, start_time=None, end_time=None):
        """Get monitoring_data"""
        route = self.get_route('monitoring_data', data_type=data_type, instruction_id=instruction_id,
                               grouping=grouping, start_time=start_time, end_time=end_time)
        return self.get(route)

    def raw_image_data(self, data_id=None):
        """Get raw image data"""
        route = self.get_route('view_raw_image', data_id=data_id)
        return self.get(route, status_response={'200': lambda resp: resp}, stream=True)

    def _get_object(self, obj_id):
        """Helper function for deref objects"""
        route = self.get_route('deref_route', obj_id=obj_id)
        return self.get(route, status_response={
            '404': lambda resp: Exception("[404] No object found for ID " + obj_id)
        })

    def analyze_run(self, protocol, test_mode=False):
        """Analyze given protocol"""
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

        return self.post(self.get_route('analyze_run'),
                         data=json.dumps({
                             "protocol": protocol,
                             "test_mode": test_mode
                         }),
                         status_response={'422': lambda response: error_string(response)})

    def submit_run(self, protocol, project_id=None, title=None, test_mode=False):
        """Submit given protocol"""
        if isinstance(protocol, Protocol):
            protocol = protocol.as_dict()
        return self.post(self.get_route('submit_run', project_id=project_id),
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

    def dataset(self, data_id, key="*"):
        """Get dataset with given data_id"""
        route = self.get_route('dataset', data_id=data_id, key=key)
        return self.get(route)

    def datasets(self, project_id=None, run_id=None, timeout=30.0):
        """Get datasets belonging to run"""
        route = self.get_route('datasets', project_id=project_id, run_id=run_id)
        return self.get(route, status_response={
            '404': lambda resp: Exception("[404] No run found for ID {}. Please ensure you have the "
                                          "right permissions.".format(run_id))
        }, timeout=timeout)

    def get_zip(self, data_id, file_path=None):
        """
        Get zip file with given data_id. Downloads to memory and returns a Python ZipFile by default.
        When dealing with larger files where it may not be desired to load the entire file into memory,
        specifying `file_path` will enable the file to be downloaded locally.

        Example Usage:

        .. code-block:: python

            small_zip_id = 'd12345'
            small_zip = api.get_zip(small_zip_id)

            my_big_zip_id = 'd99999'
            api.get_zip(my_big_zip_id, file_path='big_file.zip')

        Parameters
        ----------
        data_id: data_id
            Data id of file to download
        file_path: Optional[str]
            Path to file which to save the response to. If specified, will not return ZipFile explicitly.

        Returns
        ----------
        zip: zipfile.ZipFile
            A Python ZipFile is returned unless `file_path` is specified

        """
        import zipfile
        from io import BytesIO
        route = self.get_route('get_data_zip', data_id=data_id)
        req = self.get(route, status_response={'200': lambda resp: resp}, stream=True)
        if file_path:
            f = open(file_path, 'wb')
            # Buffer download of data into memory with smaller chunk sizes
            chunk_sz = 1024  # 1kb chunks
            for chunk in req.iter_content(chunk_sz):
                if chunk:
                    f.write(chunk)
            f.close()
            print("Zip file downloaded locally to {}.".format(file_path))
        else:
            return zipfile.ZipFile(BytesIO(req.content))

    def get_route(self, method, **kwargs):
        """Helper function to automatically match and supply required arguments"""
        route_method = getattr(routes, method)
        route_method_args, _, _, route_defaults = inspect.getargspec(route_method)
        if route_defaults:
            route_method_args = route_method_args[:-len(route_defaults)]
        # Update loaded argument dictionary with additional arguments which are not None
        arg_dict = dict(self.env_args, **{k: v for k, v in list(kwargs.items()) if v is not None})
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
        """Helper function for merging headers"""
        return dict(kwargs.pop('headers', {}), **self.headers)

    def get(self, route, **kwargs):
        return self._call('get', route, **kwargs)

    def put(self, route, **kwargs):
        return self._call('put', route, **kwargs)

    def post(self, route, **kwargs):
        return self._call('post', route, **kwargs)

    def delete(self, route, **kwargs):
        return self._call('delete', route, **kwargs)

    @staticmethod
    def _req_call(method, route, **kwargs):
        return getattr(requests, method)(route, **kwargs)

    def _call(self, method, route, custom_request=False, status_response={}, merge_status=True, **kwargs):
        """Base function for handling all requests"""
        if not custom_request:
            if self.verbose:
                print("{0}: {1}".format(method.upper(), route))
            if 'headers' not in kwargs:
                return self._handle_response(self._req_call(method, route, headers=self.headers, **kwargs),
                                             merge_status=merge_status, **status_response)
            else:
                return self._handle_response(self._req_call(method, route, **kwargs), merge_status=merge_status,
                                             **status_response)
        else:
            return self._handle_response(self._req_call(method, route, **kwargs), merge_status=merge_status,
                                         **status_response)

    def _handle_response(self, response, **kwargs):
        default_status_response = {'200': lambda resp: resp.json(),
                                   '201': lambda resp: resp.json(),
                                   'default': lambda resp: Exception("[%d] %s" % (resp.status_code, resp.text))
                                   }
        if kwargs['merge_status']:
            kwargs.pop('merge_status')
            status_response = dict(default_status_response, **kwargs)
        else:
            kwargs.pop('merge_status')
            status_response = dict(**kwargs)

        return_val = status_response.get(str(response.status_code), status_response['default'])

        if isinstance(return_val(response), Exception):
            raise return_val(response)
        else:
            return return_val(response)

    def _post_analytics(self, client_id=None, event_action=None, event_category="cli"):
        route = "https://www.google-analytics.com/collect"
        if not client_id:
            client_id = self.user_id
        packet = 'v=1&tid=UA-28937242-7&cid={}&t=event&ea={}&ec={}'.format(client_id, event_action, event_category)
        requests.post(route, packet)


class AnalysisException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
