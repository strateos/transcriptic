"""
Big dumb file of routes, please do not add any logic into this file
Note: {api_root} and {org_id} are automatically supplied in the Connection.get_route and do not need to be specified
"""


class Routes(object):
    def __init__(self, api_root, org_id):
        self.api_root = api_root
        self.org_id = org_id

    def _get(self, route, **kwargs):
        kwargs.update(self.__dict__)
        return route.format(**kwargs)

    def create_project(self):
        return self._get("{api_root}/{org_id}")

    def delete_project(self, project_id):
        return self._get("{api_root}/{org_id}/{project_id}", project_id=project_id)

    def archive_project(self, project_id):
        return self._get("{api_root}/{org_id}/{project_id}", project_id=project_id)

    def get_project(self, project_id):
        return self._get("{api_root}/{org_id}/{project_id}", project_id=project_id)

    def get_projects(self):
        return self._get("{api_root}/{org_id}/?q=&per_page=500")

    def get_project_runs(self, project_id):
        return self._get("{api_root}/{org_id}/{project_id}/runs", project_id=project_id)

    def create_package(self):
        return self._get("{api_root}/{org_id}/packages")

    def delete_package(self, package_id):
        return self._get("{api_root}/{org_id}/packages/{package_id}", package_id=package_id)

    def get_package(self, package_id):
        return self._get("{api_root}/{org_id}/packages/{package_id}", package_id=package_id)

    def get_packages(self):
        return self._get("{api_root}/{org_id}/packages/")

    def get_protocols(self):
        return self._get("{api_root}/{org_id}/protocols")

    def launch_protocol(self, protocol_id):
        return self._get("{api_root}/{org_id}/protocols/{protocol_id}/launch", protocol_id=protocol_id)

    def get_launch_request(self, protocol_id, launch_request_id):
        return self._get(
            "{api_root}/{org_id}/protocols/{protocol_id}/launch/{launch_request_id}",
            protocol_id=protocol_id,
            launch_request_id=launch_request_id
        )

    def post_release(self, package_id):
        return self._get("{api_root}/{org_id}/packages/{package_id}/releases/", package_id=package_id)

    def get_release_status(self, package_id, release_id, timestamp):
        return self._get(
            "{api_root}/{org_id}/packages/{package_id}/releases/{release_id}?_={timestamp}",
            package_id=package_id,
            release_id=release_id,
            timestamp=timestamp
        )

    def query_kits(self, query):
        return self._get("{api_root}/_commercial/kits?q={query}&per_page=1000&full_json=true", query=query)

    def query_resources(self, query):
        return self._get("{api_root}/_commercial/resources?q={query}&per_page=1000", query=query)

    def query_inventory(self, query, page=0):
        return self._get("{api_root}/{org_id}/inventory/samples?q={query}&per_page=75&page={page}", query=query,
                         page=page)

    def get_quick_launch(self, project_id, quick_launch_id):
        return self._get(
            "{api_root}/{org_id}/{project_id}/runs/quick_launch/{quick_launch_id}",
            project_id=project_id,
            quick_launch_id=quick_launch_id
        )

    def create_quick_launch(self, project_id):
        return self._get("{api_root}/{org_id}/{project_id}/runs/quick_launch", project_id=project_id)

    def resolve_quick_launch_inputs(self, project_id, quick_launch_id):
        return self._get(
            "{api_root}/{org_id}/{project_id}/runs/quick_launch/{quick_launch_id}/resolve_inputs",
            project_id=project_id,
            quick_launch_id=quick_launch_id
        )

    def login(self):
        return self._get("{api_root}/users/sign_in")

    def get_organizations(self):
        return self._get("{api_root}/organizations")

    def get_organization(self):
        return self._get("{api_root}/{org_id}")

    def deref_route(self):
        return self._get("{api_root}/-/{obj_id}")

    def analyze_run(self):
        return self._get("{api_root}/{org_id}/analyze_run")

    def analyze_launch_request(self):
        return self._get("{api_root}/{org_id}/analyze_run")

    def submit_run(self, project_id):
        return self._get("{api_root}/{org_id}/{project_id}/runs", project_id=project_id)

    def submit_launch_request(self, project_id):
        return self._get("{api_root}/{org_id}/{project_id}/runs", project_id=project_id)

    def dataset_short(self, data_id):
        return self._get("{api_root}/datasets/{data_id}.json", data_id=data_id)

    def dataset(self, data_id, key):
        return self._get("{api_root}/datasets/{data_id}.json?key={key}", data_id=data_id, key=key)

    def datasets(self, project_id, run_id):
        return self._get("{api_root}/{org_id}/{project_id}/runs/{run_id}/data", project_id=project_id, run_id=run_id)

    def get_uploads(self, key):
        return self._get("{api_root}/upload/url_for?key={key}", key=key)

    def upload(self):
        return self._get("{api_root}/api/uploads")

    def upload_datasets(self):
        return self._get("{api_root}/api/datasets")

    def preview_protocol(self):
        return self._get("{api_root}/runs/preview")

    def preview_protocol_embed(self, preview_id):
        return self._get("{api_root}/runs/preview/{preview_id}.embed", preview_id=preview_id)

    def view_data(self, data_id):
        return self._get("{api_root}/datasets/{data_id}.embed", data_id=data_id)

    def view_run(self, project_id, run_id):
        return self._get("{api_root}/{org_id}/{project_id}/runs/{run_id}.embed", project_id=project_id, run_id=run_id)

    def view_instruction(self, project_id, run_id, instruction_id):
        return self._get(
            "{api_root}/{org_id}/{project_id}/runs/{run_id}/instructions/{instruction_id}.embed",
            project_id=project_id,
            run_id=run_id,
            instruction_id=instruction_id
        )

    def view_raw_image(self, data_id):
        return self._get("{api_root}/-/{data_id}.raw", data_id=data_id)

    def get_data_zip(self, data_id):
        return self._get("{api_root}/-/{data_id}.zip", data_id=data_id)

    def monitoring_data(self, data_type, instruction_id, grouping=None, start_time=None, end_time=None):
        base_route = "{api_root}/sensor_data/{data_type}?instruction_id={instruction_id}"
        base_route += "&grouping={grouping}" if grouping else ""
        base_route += "&start_time={start_time}" if start_time else ""
        base_route += "&end_time={end_time}" if end_time else ""
        return self._get(
            base_route,
            data_type=data_type,
            instruction_id=instruction_id,
            grouping=grouping,
            start_time=start_time,
            end_time=end_time
        )

    def get_payment_methods(self):
        return self._get("{api_root}/{org_id}/payment_methods")
