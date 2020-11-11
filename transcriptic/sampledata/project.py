from transcriptic.jupyter import Project
from transcriptic.util import load_sampledata_json


def load_project_from_attributes(project_id: str, attributes: dict) -> Project:
    """
    Helper function for constructing an object from specified attributes
    """
    return Project(
        project_id,
        attributes=attributes,
    )


sample_project_attr = load_sampledata_json("p123.json")


def load_sample_project(project_id="p123") -> Project:
    """
    Loads sample project from registered mocked data.

    Example Usage:

        .. code-block:: python

            my_project = load_sample_project()
            my_project.name

    Parameters
    ----------
    project_id: str
        ProjectId of registered object mock to load.

    Returns
    -------
    Project
        Returns a Project object with some mocked data
    """
    return load_project_from_attributes(
        project_id, load_sampledata_json(f"{project_id}.json")
    )
