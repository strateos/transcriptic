from transcriptic.jupyter import Container
from transcriptic.util import load_sampledata_json


def load_container_from_attributes(
    container_id: str,
    attributes: dict,
) -> Container:
    """
    Helper function for constructing an object from specified attributes
    """
    return Container(
        container_id=container_id,
        attributes=attributes,
    )


sample_container_attr = load_sampledata_json("ct123.json")


def load_sample_container(container_id: str = "ct123") -> Container:
    """
    Loads sample container from registered mocked data.

    Example Usage:

        .. code-block:: python

            my_container = load_sample_container()
            my_container.name

    Parameters
    ----------
    container_id: str
        ContainerId of registered object mock to load.

    Returns
    -------
    Container
        Returns a Container object with some mocked data
    """
    return load_container_from_attributes(
        container_id, load_sampledata_json(f"{container_id}.json")
    )
