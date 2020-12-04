from transcriptic.jupyter import Run
from transcriptic.util import load_sampledata_json


def load_run_from_attributes(
    run_id: str,
    attributes: dict,
) -> Run:
    """
    Helper function for constructing an object from specified attributes
    """
    return Run(
        run_id=run_id,
        attributes=attributes,
    )


sample_run_attr = load_sampledata_json("r123.json")


def load_sample_run(run_id="r123") -> Run:
    """
    Loads sample run from registered mocked data.

    Example Usage:

        .. code-block:: python

            my_run = load_sample_run()
            my_run.name

    Parameters
    ----------
    run_id: str
        RunId of registered object mock to load.

    Returns
    -------
    Run
        Returns a Run object with some mocked data
    """
    return load_run_from_attributes(run_id, load_sampledata_json(f"{run_id}.json"))
