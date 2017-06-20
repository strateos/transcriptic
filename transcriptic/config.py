from __future__ import print_function

from builtins import object, str
import json
import transcriptic
import os
from os.path import expanduser
from . import routes
import requests
from .version import __version__
import platform
import inspect
import warnings
from io import StringIO, BytesIO

import sys
if sys.version_info[0] < 3:
    PermissionError = RuntimeError
    # not exactly identical, but similar enough for this case
    FileNotFoundError= IOError

try:
    import magic
except ImportError:
    warnings.warn(
        "`python-magic` is recommended. You may be missing some system-level "
        "dependencies if you have already pip-installed it.\n"
        "Please refer to https://github.com/ahupp/python-magic#installation "
        "for more installation instructions."
    )
    pass


class Connection(object):
    """
    A Connection object is the object used for communicating with Transcriptic.

    Local usage: This is most easily instantiated by using the `from_file` 
    function after calling `transcriptic login` from the command line.

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

    For those using Jupyter notebooks on secure.transcriptic.com (beta), a 
    Connection object is automatically instantiated as api.

    .. code-block:: python
        :caption: python

        from transcriptic import api

    The `api` object can then be used for making any api calls. It is 
    recommended to use the objects in `transcriptic.objects` since that wraps 
    the response in a more friendly format.

    Example Usage:

    .. code-block:: python
        :caption: python

        api.projects()
        api.runs(project_id="p123456789")

    If you have multiple organizations and would like to switch to a specific 
    organization, or if you would like to auto-load certain projects, you can
    set it directly by assigning to the corresponding variable.

    Example Usage:

    .. code-block:: python
        :caption: python
        
        api.organization_id = "my_other_org"
        api.project_id = "p123"

    """
    def __init__(self, email=None, token=None, organization_id=None,
                 api_root="https://secure.transcriptic.com",
                 cookie=None, verbose=False, analytics=True,
                 user_id="default", feature_groups=[]):
        # Initialize environment args used for computing routes
        self.env_args = dict()
        self.api_root = api_root
        self.organization_id = organization_id

        # Initialize session headers
        self.session = requests.Session()
        self.session.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "txpy/{} ({}/{}; {}/{}; {}; {})".format(
                __version__,
                platform.python_implementation(),
                platform.python_version(),
                platform.system(),
                platform.release(),
                platform.machine(),
                platform.architecture()[0]
            )
        }
        # cookie authentication is mutually exclusive from token authentication
        if cookie:
            if email is not None or token is not None:
                warnings.warn("Cookie and token authentication is mutually "
                              "exclusive. Ignoring email and token")
            self.session.headers["X-User-Email"] = None
            self.session.headers["X-User-Token"] = None
            self.cookie = cookie
        else:
            if cookie is not None:
                warnings.warn("Cookie and token authentication is mutually "
                              "exclusive. Ignoring cookie")
            self.session.headers["Cookie"] = None
            self.email = email
            self.token = token

        # Initialize feature groups
        RELEVANT_GROUPS = set(
            ['can_submit_autoprotocol', 'can_upload_packages']
        )
        self.feature_groups = list(RELEVANT_GROUPS.intersection(feature_groups))

        # Initialize CLI parameters
        self.verbose = verbose
        self.analytics = analytics
        self.user_id = user_id

        transcriptic.api = self

    @staticmethod
    def from_file(path):
        """Loads connection from file"""
        with open(expanduser(path), 'r') as f:
            cfg = json.loads(f.read())
            expected_keys = ['email', 'token', 'organization_id', 'api_root',
                             'analytics', 'user_id']
            def key_not_found(): raise OSError("Key not found")
            [key_not_found() for key in expected_keys if key not in cfg.keys()]
            return Connection(**cfg)

    @property
    def api_root(self):
        try:
            return self.env_args['api_root']
        except (NameError, KeyError):
            raise ValueError("api_root is not set.")

    @api_root.setter
    def api_root(self, value):
        self.update_environment(api_root=value)

    @property
    def organization_id(self):
        try:
            return self.env_args['org_id']
        except (NameError, KeyError):
            raise ValueError("organization_id is not set.")

    @organization_id.setter
    def organization_id(self, value):
        self.update_environment(org_id=value)

    @property
    def project_id(self):
        try:
            return self.env_args['project_id']
        except (NameError, KeyError):
            raise ValueError("project_id is not set.")

    @project_id.setter
    def project_id(self, value):
        self.update_environment(project_id=value)

    @property
    def email(self):
        try:
            return self.session.headers['X-User-Email']
        except (NameError, KeyError):
            raise ValueError("email is not set.")

    @email.setter
    def email(self, value):
        if self.cookie is not None:
            warnings.warn("Cookie and token authentication is mutually "
                          "exclusive. Clearing cookie from headers")
            self.update_headers(**{'Cookie': None})
        self.update_headers(**{'X-User-Email': value})

    @property
    def token(self):
        try:
            return self.session.headers['X-User-Token']
        except (NameError, KeyError):
            raise ValueError("token is not set.")

    @token.setter
    def token(self, value):
        if self.cookie is not None:
            warnings.warn("Cookie and token authentication is mutually "
                          "exclusive. Clearing cookie from headers")
            self.update_headers(**{'Cookie': None})
        self.update_headers(**{'X-User-Token': value})

    @property
    def cookie(self):
        try:
            return self.session.headers['Cookie']
        except (NameError, KeyError):
            return ValueError("cookie is not set.")

    @cookie.setter
    def cookie(self, value):
        if self.email is not None or self.token is not None:
            warnings.warn("Cookie and token authentication is mutually "
                          "exclusive. Clearing email and token from headers")
            self.update_headers(**{'X-User-Email': None, 'X-User-Token': None})
        self.update_headers(**{'Cookie': value})

    def save(self, path):
        """Saves current connection into specified file, used for CLI"""
        with open(expanduser(path), 'w') as f:
            f.write(
                json.dumps(
                    {
                        'email': self.email,
                        'token': self.token,
                        'organization_id': self.organization_id,
                        'api_root': self.api_root,
                        'analytics': self.analytics,
                        'user_id': self.user_id,
                        'feature_groups': self.feature_groups
                    },
                    indent=2
                )
            )

    def update_environment(self, **kwargs):
        """
        Updates environment variables used for computing routes. 
        To remove an existing variable, set value to None.
        """
        self.env_args = dict(self.env_args, **kwargs)

    def update_headers(self, **kwargs):
        """
        Updates session headers
        To remove an existing variable, set value to None.
        """
        self.session.headers = dict(self.session.headers, **kwargs)

    def url(self, path):
        """url format helper"""
        if path.startswith("/"):
            return "%s%s" % (self.api_root, path)
        else:
            return "%s/%s/%s" % (self.api_root, self.organization_id, path)

    def preview_protocol(self, protocol):
        """Post protocol preview"""
        route = self.get_route('preview_protocol')
        protocol = _parse_protocol(protocol)
        err_default = "Unable to preview protocol"
        return self.post(
            route,
            json={"protocol": json.dumps(protocol)},
            allow_redirects=False,
            status_response={
                '302': lambda resp: resp.headers['Location'],
                'default': lambda resp: RuntimeError(err_default)
            }
        )

    def organizations(self):
        """Get list of organizations"""
        route = self.get_route('get_organizations')
        return self.get(route)

    def get_organization(self, org_id=None):
        """Get particular organization"""
        route = self.get_route('get_organization', org_id=org_id)
        err_404 = "There was an error fetching the organization " \
                  "{}".format(org_id)
        resp = self.get(
            route,
            status_response={
                '200': lambda resp: resp,
                '404': lambda resp: RuntimeError(err_404),
                'default': lambda resp: resp
            }
        )
        return resp

    def projects(self):
        """Get list of projects in organization"""
        route = self.get_route('get_projects')
        err_default = "There was an error listing the projects in your " \
                      "organization.  Make sure your login details are correct."
        return self.get(
            route,
            status_response={
                '200': lambda resp: resp.json()["projects"],
                'default': lambda resp: RuntimeError(err_default)
            }
        )

    def project(self, project_id=None):
        """Get particular project"""
        route = self.get_route('get_project', project_id=project_id)
        err_default = "There was an error fetching project " \
                      "{}".format(project_id)
        return self.get(
            route,
            status_response={'default': lambda resp: RuntimeError(err_default)}
        )

    def runs(self, project_id=None):
        """Get list of runs in project"""
        route = self.get_route('get_project_runs', project_id=project_id)
        err_default = "There was an error fetching the runs in project " \
                      "{}".format(project_id)
        return self.get(
            route,
            status_response={
                "200": lambda resp: resp.json(),
                "default": lambda resp: RuntimeError(err_default)
            }
        )

    def create_project(self, title):
        """Create project with given title"""
        route = self.get_route('create_project')
        return self.post(route, data=json.dumps({'name': title}))

    def delete_project(self, project_id=None):
        """Delete project with given project_id"""
        route = self.get_route('delete_project', project_id=project_id)
        return self.delete(route, status_response={'200': lambda resp: True})

    def archive_project(self, project_id=None):
        """Archive project with given project_id"""
        route = self.get_route('archive_project', project_id=project_id)
        return self.put(
            route,
            data=json.dumps({"project": {"archived": True}}),
            status_response={'200': lambda resp: True}
        )

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

    def get_release_status(self, package_id=None, release_id=None,
                           timestamp=None):
        """Get status of current release upload"""
        route = self.get_route('get_release_status', package_id=package_id,
                               release_id=release_id, timestamp=timestamp)
        return self.get(route)

    def get_quick_launch(self, project_id=None, quick_launch_id=None):
        """Get quick launch object"""
        route = self.get_route('get_quick_launch', project_id=project_id,
                               quick_launch_id=quick_launch_id)
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
        route = self.get_route('get_launch_request', protocol_id=protocol_id,
                               launch_request_id=launch_request_id)
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

    def payment_methods(self):
        route = self.get_route('get_payment_methods')
        return self.get(route)

    def monitoring_data(self, data_type, instruction_id=None, grouping=None,
                        start_time=None, end_time=None):
        """Get monitoring_data"""
        route = self.get_route('monitoring_data', data_type=data_type,
                               instruction_id=instruction_id,
                               grouping=grouping, start_time=start_time,
                               end_time=end_time)
        return self.get(route)

    def raw_image_data(self, data_id=None):
        """Get raw image data"""
        route = self.get_route('view_raw_image', data_id=data_id)
        return self.get(
            route,
            status_response={'200': lambda resp: resp},
            stream=True
        )

    def _get_object(self, obj_id, obj_type=None):
        """Helper function for loading objects"""
        # TODO: Migrate away from deref routes for other object types
        if obj_type == "dataset":
            route = self.get_route('dataset_short', data_id=obj_id)
        else:
            route = self.get_route('deref_route', obj_id=obj_id)
        err_404 = "[404] No object found for ID {}".format(obj_id)
        return self.get(
            route,
            status_response={'404': lambda resp: Exception(err_404)}
        )

    def analyze_run(self, protocol, test_mode=False):
        """Analyze given protocol"""
        protocol = _parse_protocol(protocol)
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

        return self.post(
            self.get_route('analyze_run'),
            data=json.dumps({
                "protocol": protocol,
                "test_mode": test_mode
            }),
            status_response={'422': lambda resp: error_string(resp)}
        )

    def submit_run(self, protocol, project_id=None, title=None, test_mode=False,
                   payment_method_id=None):
        """Submit given protocol"""
        protocol = _parse_protocol(protocol)
        payload = {
            "title": title,
            "protocol": protocol,
            "test_mode": test_mode,
            "payment_method_id": payment_method_id
        }
        data = {k: v for k, v in payload.items() if v is not None}
        route = self.get_route('submit_run', project_id=project_id)
        err_404 = "Error: Couldn't create run (404).\n Are you sure the " \
                  "project {} exists, and that you have access " \
                  "to it?".format(self.url(project_id))

        def err_422(resp): "Error creating run: {}".format(resp.text)

        return self.post(
            route,
            data=json.dumps(data),
            status_response={
                '404': lambda resp: AnalysisException(err_404),
                '422': lambda resp: AnalysisException(err_422)
            }
        )

    def analyze_launch_request(self, launch_request_id, test_mode=False):
        return self.post(
            self.get_route('analyze_launch_request'),
            data=json.dumps({
                "launch_request_id": launch_request_id,
                "test_mode": test_mode
            })
        )

    def submit_launch_request(self, launch_request_id, project_id=None,
                              protocol_id=None, title=None, test_mode=False,
                              payment_method_id=None):
        """Submit specified launch request"""
        payload = {
            "title": title,
            "launch_request_id": launch_request_id,
            "protocol_id": protocol_id,
            "test_mode": test_mode,
            "payment_method_id": payment_method_id
        }
        data = {k: v for k, v in payload.items() if v is not None}
        return self.post(
            self.get_route('submit_launch_request', project_id=project_id),
            data=json.dumps(data),
            status_response={
                '404': lambda resp: AnalysisException(
                    "Error: Couldn't create run (404). \n"
                    "Are you sure the project %s "
                    "exists, and that you have access to it?" %
                    self.url(project_id)),
                '422': lambda resp: AnalysisException(
                    "Error creating run: %s" % resp.text)
            }
        )

    def dataset(self, data_id, key="*"):
        """Get dataset with given data_id"""
        route = self.get_route('dataset', data_id=data_id, key=key)
        return self.get(route)

    def datasets(self, project_id=None, run_id=None, timeout=30.0):
        """Get datasets belonging to run"""
        route = self.get_route('datasets', project_id=project_id, run_id=run_id)
        err_404 = "[404] No run found for ID {}. Please ensure you have the " \
                  "right permissions.".format(run_id)
        return self.get(
            route,
            status_response={'404': lambda resp: Exception(err_404)},
            timeout=timeout
        )

    def upload_dataset_from_filepath(self, file_path, title, run_id,
                                     analysis_tool, analysis_tool_version):
        """
        Helper for uploading a file as a dataset to the specified run.
        
        Uses `upload_dataset`.
        
        .. code-block:: python
        
            api.upload_dataset_from_filepath(
                "my_file.txt", 
                title="my cool dataset",
                run_id="r123",
                analysis_tool="cool script",
                analysis_tool_version="v1.0.0"
            )

        Parameters
        ----------
        file: str
            Path to file to be uploaded
        title: str
            Name of dataset
        run_id: str
            Run-id
        analysis_tool: str, optional
            Name of tool used for analysis
        analysis_tool_version: str, optional
            Version of tool used
            
        Returns
        -------
        response: dict
            JSON-formatted response
        """
        try:
            file_path = os.path.expanduser(file_path)
            file_handle = open(file_path, 'rb')
            name = file_handle.name
        except (AttributeError, FileNotFoundError) as e:
            raise ValueError("'file' has to be a valid filepath")

        try:
            content_type = magic.from_file(file_path, mime=True)
        except NameError:
            # Handle issues with magic import by not decoding content_type
            content_type = None
        return self.upload_dataset(file_handle, name, title, run_id,
                                   analysis_tool, analysis_tool_version,
                                   content_type)

    def upload_dataset(self, file_handle, name, title, run_id,
                       analysis_tool, analysis_tool_version,
                       content_type=None):
        """
        Uploads a file_handle as a dataset to the specified run.

        .. code-block:: python
            # Uploading a data_frame via file_handle, using Py3
            from io import StringIO

            temp_buffer = StringIO()
            my_df.to_csv(temp_buffer)

            api.upload_dataset(
                temp_buffer,
                name="my_df",
                title="my cool dataset",
                run_id="r123",
                analysis_tool="cool script",
                analysis_tool_version="v1.0.0"
            )

        Parameters
        ----------
        file_handle: file_handle
            File handle to be uploaded
        name: str
            Dataset filename
        title: str
            Name of dataset
        run_id: str
            Run-id
        analysis_tool: str, optional
            Name of tool used for analysis
        analysis_tool_version: str, optional
            Version of tool used
        content_type: str
            Type of content uploaded

        Returns
        -------
        response: dict
            JSON-formatted response
        """
        s3_key = self.upload_to_uri(file_handle, content_type, title, name)
        upload_datasets_route = self.get_route("upload_datasets")
        upload_resp = self.post(
            upload_datasets_route,
            json={
                "s3_key": s3_key,
                "file_name": name,
                "title": title,
                "run_id": run_id,
                "analysis_tool": analysis_tool,
                "analysis_tool_version": analysis_tool_version
            },
            status_response={
                '404': lambda resp: "[404] Please double-check your parameters "
                                    "and ensure they are valid."
            }
        )

        return upload_resp

    def upload_to_uri(self, file_handle, content_type, title, name):
        """
        Helper for uploading files via the `upload_uri` route
        
        Parameters
        ----------
        file_handle: file_handle
            File handle to be uploaded
        content_type: str
            Type of content uploaded
        title: str
            Title of content to be uploaded
        name: str
            Name of file to be uploaded

        Returns
        -------
        key: str
            s3 key
        """
        uri_route = self.get_route('upload_uri')
        uri_resp = self.post(uri_route, data=json.dumps({"name": title}))
        try:
            key = uri_resp['key']
            uri = uri_resp['uri']
        except KeyError as e:
            raise RuntimeError("Unexpected payload returned for upload_dataset")

        if isinstance(file_handle, StringIO):
            try:
                # io.StringIO instances must be converted to bytes
                file_handle = BytesIO(bytes(file_handle.getvalue(), "utf-8"))
            except AttributeError as e:
                raise ValueError("Unable to convert read buffer to bytes")

        headers = {
            "Content-Disposition": "attachment; filename='{}'".format(name),
            "Content-Type": content_type
        }
        headers = {k: v for k, v in headers.items() if v}
        self.put(
            uri,
            data=file_handle,
            custom_request=True,
            headers=headers,
            status_response={'200': lambda resp: resp}
        )
        return key

    def get_zip(self, data_id, file_path=None):
        """
        Get zip file with given data_id. Downloads to memory and returns a 
        Python ZipFile by default.
        When dealing with larger files where it may not be desired to load the 
        entire file into memory, specifying `file_path` will enable the file to 
        be downloaded locally.

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
            Path to file which to save the response to. If specified, will not 
            return ZipFile explicitly.

        Returns
        ----------
        zip: zipfile.ZipFile
            A Python ZipFile is returned unless `file_path` is specified

        """
        import zipfile
        route = self.get_route('get_data_zip', data_id=data_id)
        req = self.get(route, status_response={'200': lambda resp: resp},
                       stream=True)
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
        """
        Helper function to automatically match and supply required arguments
        """
        route_method = getattr(routes, method)
        route_method_args, _, _, route_defaults = inspect.getargspec(route_method)
        if route_defaults:
            route_method_args = route_method_args[:-len(route_defaults)]
        # Update loaded argument dict with new arguments which are not None
        new_args = {k: v for k, v in list(kwargs.items()) if v is not None}
        arg_dict = dict(self.env_args, **new_args)
        input_args = []
        for arg in route_method_args:
            if arg_dict[arg]:
                input_args.append(arg_dict[arg])
            else:
                raise Exception("For route: {0}, argument {1} needs to be "
                                "provided.".format(method, arg))

        return route_method(*tuple(input_args))

    def get(self, route, **kwargs):
        return self._call('get', route, **kwargs)

    def put(self, route, **kwargs):
        return self._call('put', route, **kwargs)

    def post(self, route, **kwargs):
        return self._call('post', route, **kwargs)

    def delete(self, route, **kwargs):
        return self._call('delete', route, **kwargs)

    def _req_call(self, method, route, **kwargs):
        return getattr(self.session, method)(route, **kwargs)

    def _call(self, method, route, custom_request=False, status_response={},
              merge_status=True, **kwargs):
        """Base function for handling all requests"""
        if not custom_request:
            if self.verbose:
                print("{0}: {1}".format(method.upper(), route))
            if 'headers' not in kwargs:
                return self._handle_response(
                    self._req_call(method, route, **kwargs),
                    merge_status=merge_status,
                    **status_response
                )
            else:
                return self._handle_response(
                    self._req_call(method, route, **kwargs),
                    merge_status=merge_status,
                    **status_response
                )
        else:
            return self._handle_response(
                self._req_call(method, route, **kwargs),
                merge_status=merge_status,
                **status_response
            )

    def _handle_response(self, response, **kwargs):
        unauthorized_resp = "You are not authorized to execute this command. " \
                            "For more information on access " \
                            "permissions see the package documentation."
        internal_error_resp = "An internal server error has occurred. " \
                              "Please contact support for assistance."
        default_status_response = {
            '200': lambda resp: resp.json(),
            '201': lambda resp: resp.json(),
            '401': lambda resp: PermissionError(
                "[%d] %s" % (resp.status_code, unauthorized_resp)
            ),
            '403': lambda resp: PermissionError(
                "[%d] %s" % (resp.status_code, unauthorized_resp)
            ),
            '500': lambda resp: Exception(
                "[%d] %s" % (resp.status_code, internal_error_resp)
            ),
            'default': lambda resp: Exception(
                "[%d] %s" % (resp.status_code, resp.text)
            )
        }
        if kwargs['merge_status']:
            kwargs.pop('merge_status')
            status_response = dict(default_status_response, **kwargs)
        else:
            kwargs.pop('merge_status')
            status_response = dict(**kwargs)

        return_val = status_response.get(
            str(response.status_code),
            status_response['default']
        )

        if isinstance(return_val(response), Exception):
            raise return_val(response)
        else:
            return return_val(response)

    def _post_analytics(self, client_id=None, event_action=None,
                        event_category="cli"):
        route = "https://www.google-analytics.com/collect"
        if not client_id:
            client_id = self.user_id
        packet = 'v=1&tid=UA-28937242-7&cid={}&t=event&ea={}' \
                 '&ec={}'.format(client_id, event_action, event_category)
        requests.post(route, packet)


class AnalysisException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def _parse_protocol(protocol):
    if isinstance(protocol, dict):
        return protocol
    try:
        from autoprotocol import Protocol
    except ImportError as IE:
        raise RuntimeError("Please install `autoprotocol-python` in order "
                           "to work with Protocol objects")
    if isinstance(protocol, Protocol):
        return protocol.as_dict()

