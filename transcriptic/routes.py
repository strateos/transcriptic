"""
Big dumb file of routes, please do not add any logic into this file
Note: {api_root} and {org_id} are automatically supplied in the Connection.get_route and do not need to be specified
"""


def create_project(api_root, org_id):
    return "{api_root}/{org_id}".format(**locals())


def delete_project(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}".format(**locals())


def archive_project(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}".format(**locals())


def get_project(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}".format(**locals())


def get_projects(api_root, org_id):
    return "{api_root}/{org_id}/?q=&per_page=500".format(**locals())


def get_project_runs(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}".format(**locals())


def create_package(api_root, org_id):
    return "{api_root}/{org_id}/packages".format(**locals())


def delete_package(api_root, org_id, package_id):
    return "{api_root}/{org_id}/packages/{package_id}".format(**locals())


def get_package(api_root, org_id, package_id):
    return "{api_root}/{org_id}/packages/{package_id}".format(**locals())


def get_packages(api_root, org_id):
    return "{api_root}/{org_id}/packages/".format(**locals())


def post_release(api_root, org_id, package_id):
    return "{api_root}/{org_id}/packages/{package_id}/releases/".format(**locals())


def get_release_status(api_root, org_id, package_id, release_id, timestamp):
    return "{api_root}/{org_id}/packages/{package_id}/releases/{release_id}?_={timestamp}".format(**locals())


def query_resources(api_root, query):
    return "{api_root}/_commercial/kits?q={query}&per_page=1000".format(**locals())


def get_quick_launch(api_root, org_id, project_id, quick_launch_id):
    return "{api_root}/{org_id}/{project_id}/runs/quick_launch/{quick_launch_id}".format(**locals())


def create_quick_launch(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}/runs/quick_launch".format(**locals())


def upload_sign(api_root):
    return "{api_root}/upload/sign".format(**locals())


def aws_upload():
    return "https://transcriptic-uploads.s3.amazonaws.com"


def login(api_root):
    return "{api_root}/users/sign_in".format(**locals())


def get_organizations(api_root, org_id):
    return "{api_root}/{org_id}".format(**locals())


def deref_route(api_root, obj_id):
    return "{api_root}/-/{obj_id}".format(**locals())


def analyze_run(api_root, org_id):
    return "{api_root}/{org_id}/analyze_run".format(**locals())


def submit_run(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}/runs".format(**locals())


def dataset(api_root, data_id, key):
    return "{api_root}/datasets/{data_id}.json?key={key}".format(**locals())


def datasets(api_root, org_id, project_id, run_id):
    return "{api_root}/{org_id}/{project_id}/runs/{run_id}/data".format(**locals())


def preview_protocol(api_root):
    return "{api_root}/runs/preview".format(**locals())


def view_data(api_root, data_id):
    return "{api_root}/datasets/{data_id}.embed".format(**locals())


def view_run(api_root, org_id, project_id, run_id):
    return "{api_root}/{org_id}/{project_id}/runs/{run_id}.embed".format(**locals())


def view_raw_image(api_root, data_id):
    return "{api_root}/-/{data_id}.raw".format(**locals())


def monitoring_data(api_root, org_id, project_id, run_id, instruction_id, data_type):
    return "{api_root}/{org_id}/{project_id}/runs/{run_id}/{instruction_id}/monitoring/{data_type}".format(**locals())
