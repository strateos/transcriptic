from transcriptic.jupyter import Container
from transcriptic.util import load_sampledata_json


def load_container_from_attributes(
    container_id: str,
    attributes: dict,
) -> Container:
    return Container(
        container_id=container_id,
        attributes=attributes,
    )


sample_container_attr = load_sampledata_json("ct123.json")


def load_sample_container(container_id="ct123") -> Container:
    return load_container_from_attributes(
        container_id, load_sampledata_json(f"{container_id}.json")
    )
