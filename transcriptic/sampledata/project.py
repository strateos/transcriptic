from transcriptic.jupyter import Project
from transcriptic.util import load_sampledata_json


def load_project_from_attributes(project_id: str, attributes: dict) -> Project:
    return Project(
        project_id,
        attributes=attributes,
    )


sample_project_attr = load_sampledata_json("p123.json")


def load_sample_project(project_id="p123") -> Project:
    return load_project_from_attributes(
        project_id, load_sampledata_json(f"{project_id}.json")
    )
