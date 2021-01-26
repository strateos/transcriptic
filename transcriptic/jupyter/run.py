import pandas as pd

from requests.exceptions import ReadTimeout

from .common import _BaseObject
from .container import Container
from .dataset import Dataset
from .instruction import Instruction


class Run(_BaseObject):
    """
    A Run object contains helper methods for accessing Run-related information such as
    Instructions, Datasets and monitoring data.

    Example Usage:

        .. code-block:: python

            myRun = Run('r12345')
            myRun.data
            myRun.instructions
            myRun.containers
            myRun.Instructions[0]

    Attributes
    ----------
    id : str
        Run id
    name: str
        Run name
    data: DataFrame
        DataFrame summary of all datasets which belong to this run
    instructions: DataFrame
        DataFrame summary of all Instruction objects which belong to this run
    containers: DataFrame
        DataFrame summary of all Container objects which belong to this run
    project_id : str
        Project id which run belongs to
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """

    def __init__(self, run_id, attributes=None, connection=None, timeout=30.0):
        """
        Initialize a Run by providing a run name/id. The attributes and connection
        parameters are generally not specified unless one wants to manually initialize
        the object.

        Parameters
        ----------
        run_id: str
            Run name or id in string form
        attributes: Optional[dict]
            Attributes of the run
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless
            explicitly provided
        timeout: Optional[float]
            Timeout in seconds (defaults to 30.0). This will be used when making API
            calls to fetch data associated with the run.
        """
        super(Run, self).__init__("run", run_id, attributes, connection)
        self.project_id = self.attributes["project"]["id"]
        self.timeout = timeout
        self._data_ids = pd.DataFrame()
        self._instructions = pd.DataFrame()
        self._containers = pd.DataFrame()
        self._data = pd.DataFrame()

    @property
    def data_ids(self):
        """
        Find and generate a list of datarefs and data_ids associated with this run.

        Returns
        -------
        DataFrame
            Returns a DataFrame of data ids, with datarefs and data_ids as columns

        """
        if self._data_ids.empty:
            datasets = []
            for dataset in self.attributes["datasets"]:
                inst_id = dataset["instruction_id"]
                if inst_id:
                    titles = [
                        inst.attributes["operation"]["dataref"]
                        for inst in self.instructions["Instructions"]
                        if inst.attributes["id"] == inst_id
                    ]
                    if len(titles) == 0:
                        title = "unknown"
                    elif len(titles) == 1:
                        title = titles[0]
                    else:
                        # This should never happen since instruction_ids are unique
                        raise ValueError("No unique instruction id found")
                else:
                    title = dataset["title"]
                datasets.append(
                    {
                        "Name": title,
                        "DataType": dataset["data_type"],
                        "Id": dataset["id"],
                    }
                )
            if len(datasets) > 0:
                data_ids = pd.DataFrame(datasets)
                self._data_ids = data_ids[["Name", "DataType", "Id"]]
        return self._data_ids

    @property
    def instructions(self):
        if self._instructions.empty:
            instruction_list = [
                Instruction(
                    dict(x, **{"project_id": self.project_id, "run_id": self.id}),
                    connection=self.connection,
                )
                for x in self.attributes["instructions"]
            ]
            self._instructions = pd.DataFrame(instruction_list)
            self._instructions.columns = ["Instructions"]
            self._instructions.insert(
                0, "Name", [inst.name for inst in self._instructions.Instructions]
            )
            self._instructions.insert(
                1, "Id", [inst.id for inst in self._instructions.Instructions]
            )
            self._instructions.insert(
                2,
                "Started",
                [inst.started_at for inst in self._instructions.Instructions],
            )
            self._instructions.insert(
                3,
                "Completed",
                [inst.completed_at for inst in self._instructions.Instructions],
            )
        return self._instructions

    @property
    def Instructions(self):
        """
        Helper for allowing direct access of `Instruction` objects

        Returns
        -------
        Series
            Returns a Series of `Instruction` objects

        """
        return self.instructions.Instructions

    @property
    def containers(self):
        if self._containers.empty:
            container_list = []
            for ref in Run(self.id).attributes["refs"]:
                container_list.append(Container(ref["container"]["id"]))
            self._containers = pd.DataFrame(container_list)
            self._containers.columns = ["Containers"]
            self._containers.insert(
                0, "Name", [container.name for container in self._containers.Containers]
            )
            self._containers.insert(
                1,
                "ContainerId",
                [container.id for container in self._containers.Containers],
            )
            self._containers.insert(
                2,
                "Type",
                [
                    container.container_type.shortname
                    for container in self._containers.Containers
                ],
            )
            self._containers.insert(
                3,
                "Status",
                [
                    container.attributes["status"]
                    for container in self._containers.Containers
                ],
            )
            self._containers.insert(
                4,
                "Storage Condition",
                [container.storage for container in self._containers.Containers],
            )
        return self._containers

    @property
    def Containers(self):
        """
        Helper for allowing direct access of `Container` objects

        Returns
        -------
        Series
            Returns a Series of `Container` objects
        """
        return self.containers.Containers

    @property
    def data(self):
        """
        Find and generate a list of Dataset objects which are associated with this run

        Returns
        -------
        DataFrame
            Returns a DataFrame of datasets, with Name, Dataset and DataType as columns

        """
        if self._data.empty:
            num_datasets = len(self.data_ids)
            if num_datasets == 0:
                print("No datasets were found.")
            else:
                print(f"Attempting to fetch ${num_datasets} datasets...")
                try:
                    data_list = []
                    for name, data_type, data_id in self.data_ids.values:
                        dataset = Dataset(data_id)
                        data_list.append(
                            {
                                "Name": name,
                                "DataType": data_type,
                                "Operation": dataset.operation,
                                "AnalysisTool": dataset.analysis_tool,
                                "Datasets": dataset,
                            }
                        )
                    data_frame = pd.DataFrame(data_list)

                    # Rearrange columns
                    self._data = data_frame[
                        ["Name", "DataType", "Operation", "AnalysisTool", "Datasets"]
                    ]
                except ReadTimeout:
                    print(
                        f"Operation timed out after {self.timeout} seconds. Returning "
                        "data_ids instead of Datasets.\nTo try again, increase value "
                        "of self.timeout and resubmit request."
                    )
                    return self.data_ids
        return self._data

    @property
    def Datasets(self):
        """
        Helper for allowing direct access of `Dataset` objects

        Returns
        -------
        Series
            Returns a Series of `Dataset` objects
        """
        try:
            return self.data.Datasets
        except Exception:
            print("Unable to load Datasets successfully. Returning empty series.")
            return pd.Series()

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
        style="height:450px" seamless></iframe>""" % self.connection.get_route(
            "view_run", project_id=self.project_id, run_id=self.id
        )
