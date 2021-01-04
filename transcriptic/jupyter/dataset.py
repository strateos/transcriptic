import warnings

from copy import deepcopy

import pandas as pd

from .common import _BaseObject
from .container import Container
from .dataobject import DataObject


class Dataset(_BaseObject):
    """
    A Dataset object contains helper methods for accessing data related information

    Attributes
    ----------
    id : str
        Dataset id
    name: str
        Dataset name
    data : DataFrame
        DataFrame of well-indexed data values. Note that associated metadata is found in
         attributes dictionary
    data_objects : list(DataObject)
        List of DataObject type
    attachments : dict(str, bytes)
        names and data of all attachments for the dataset
    container: Container
        Container object that was used for this dataset
    operation: str
        Operation used for generating the dataset
    data_type: str
        Data type of this dataset
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """

    def __init__(self, data_id, attributes=None, connection=None):
        """
        Initialize a Dataset by providing a data name/id. The attributes and connection
        parameters are generally not specified unless one wants to manually initialize
        the object.

        Parameters
        ----------
        data_id: str
            Dataset name or id in string form
        attributes: Optional[dict]
            Attributes of the dataset
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless
            explicitly provided
        """
        super(Dataset, self).__init__("dataset", data_id, attributes, connection)
        # TODO: Get BaseObject to handle dataset name
        self.name = self.attributes["title"]
        self.id = data_id

        # TODO: Consider more formally distinguishing between dataset types
        try:
            self.operation = self.attributes["instruction"]["operation"]["op"]
        except KeyError:
            self.operation = None
        try:
            self.container = Container(
                self.attributes["container"]["id"],
                attributes=self.attributes["container"],
                connection=connection,
            )
        except KeyError as e:
            if "instruction" in self.attributes:
                warnings.warn(f"Missing key {e} when initializing dataset")
            self.container = None

        self.analysis_tool = self.attributes["analysis_tool"]
        self.analysis_tool_version = self.attributes["analysis_tool_version"]
        self.data_type = self.attributes["data_type"]
        self._raw_data = None
        self._data = pd.DataFrame()
        self._attachments = None
        self._data_objects = None

    @property
    def attachments(self):
        if not self._attachments:
            self._attachments = self.connection.attachments(data_id=self.id)
        return self._attachments

    @property
    def raw_data(self):
        if not self._raw_data:
            # Get all raw data
            self._raw_data = self.connection.dataset(data_id=self.id, key="*")
        return self._raw_data

    @property
    def data(self, key="*"):
        if self._data.empty:
            # Get all data initially (think about lazy loading in the future)
            try:
                self._data = pd.DataFrame(self.raw_data)
            except:
                raise RuntimeError(
                    "Failed to cast data as DataFrame. Try using raw_data property "
                    "instead."
                )
            self._data.columns = [x.upper() for x in self._data.columns]
        if key == "*":
            return self._data
        else:
            return self._data[key]

    def data_objects(self):
        if not self._data_objects:
            self._data_objects = DataObject.init_from_dataset_id(self.id)
        return self._data_objects

    def cross_ref_aliquots(self):
        # Use the container.aliquots DataFrame as the base
        aliquot_data = deepcopy(self.container.aliquots)
        data_column = []
        indices_without_data = []
        # Print a warning if new column will overwrite existing column
        if "Aliquot Data" in aliquot_data.columns.values.tolist():
            warnings.warn(
                "Column 'Aliquot Data' will be overwritten with data pulled from "
                "Dataset."
            )
        # Look up data for every well index
        for index in aliquot_data.index:
            # Get humanized index
            humanized_index = self.container.container_type.humanize(int(index))
            if humanized_index in self.data:
                # Use humanized index to get data for that well
                data_point = self.data.loc[0, humanized_index]
            else:
                # If no data for that well, use None instead
                data_point = None
                indices_without_data.append(humanized_index)
            # Append data point to list
            data_column.append(data_point)
        # Print a list of well indices that do not have corresponding data keys
        if len(indices_without_data) > 0:
            warnings.warn(
                "The following indices were not found as data keys: %s"
                % ", ".join(indices_without_data)
            )
        # Add these data as a column to the DataFrame
        aliquot_data["Aliquot Data"] = data_column

        return aliquot_data

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="height:400px; width:600px" seamless></iframe>""" % self.connection.get_route(
            "view_data", data_id=self.id
        )
