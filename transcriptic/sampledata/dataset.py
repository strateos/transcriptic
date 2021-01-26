from typing import List

from transcriptic.jupyter import Dataset
from transcriptic.util import load_sampledata_json


def load_dataset_from_attributes(
    dataset_id: str,
    attributes: dict,
) -> Dataset:
    """
    Helper function for constructing an object from specified attributes
    """
    return Dataset(
        data_id=dataset_id,
        attributes=attributes,
    )


sample_dataset_attr = load_sampledata_json("d123.json")


def load_sample_dataset(dataset_id="d123") -> Dataset:
    """
    Loads sample dataset from registered mocked data.

    Example Usage:

        .. code-block:: python

            my_dataset = load_sample_dataset()
            my_dataset.data_type

    Parameters
    ----------
    dataset_id: str
        DatasetId of registered object mock to load.

    Returns
    -------
    Dataset
        Returns a Dataset object with some mocked data
    """
    return load_dataset_from_attributes(
        dataset_id, load_sampledata_json(f"{dataset_id}.json")
    )


# Manually annotate which datasets correspond to absorbance datasets for now
ABSORBANCE_DATASETS = ["d123", "d124", "d125", "d126", "d127"]


def load_sample_absorbance_dataset(dataset_id="d123") -> Dataset:
    """
    Loads sample absorbance dataset from registered mocked data.

    Example Usage:

        .. code-block:: python

            my_dataset = load_sample_absorbance_dataset()
            my_dataset.data_type
            Absorbance(my_dataset, ["some label"])

    Returns
    -------
    Dataset
        Returns an Absorbance Dataset object with some mocked data

    """
    assert dataset_id in ABSORBANCE_DATASETS
    return load_sample_dataset(dataset_id)


def load_sample_kinetics_datasets(dataset_ids=None) -> List[Dataset]:
    """
    Loads sample kinetics dataset from registered mocked data.

    Example Usage:

        .. code-block:: python

            my_datasets = load_sample_kinetics_datasets()
            print([dataset.data_type for dataset in my_datasets])
            kinetics.Spectrophotometry(my_datasets)

    Returns
    -------
    List[Dataset]
        Returns a list of Absorbance Dataset objects with some mocked data

    """
    if dataset_ids is None:
        dataset_ids = ABSORBANCE_DATASETS
    return [load_sample_dataset(dataset_id) for dataset_id in dataset_ids]
