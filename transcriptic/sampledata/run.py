from transcriptic.jupyter import Run
from transcriptic.util import load_sampledata_json


def load_run_from_attributes(
    run_id: str,
    attributes: dict,
) -> Run:
    return Run(
        run_id=run_id,
        attributes=attributes,
    )


sample_run_attr = load_sampledata_json("r123.json")


def load_sample_run() -> Run:
    return load_run_from_attributes("r123", sample_run_attr)
