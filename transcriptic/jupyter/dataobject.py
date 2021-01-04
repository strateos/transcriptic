import json

from io import StringIO

import pandas as pd
import requests

from .common import _check_api
from .container import Container


class DataObject(object):
    """
    A DataObject holds a reference to the raw data, stored in S3, along with format and
    validation information

    Attributes
    ----------
    id : str
        DataObject id
    dataset_id : str
        Dataset id
    data : bytes
        Bytes fetched from the url
    name: str
        Dataset name
    content_type: str
        content type
    format: str
        format
    size: int
        size in bytes
    status: Enum("valid", "invalid", "unverified")
        valid vs invalid
    url: str
        download url which expires every 1hr.  Call `refresh` to renew
    validation_errors: list(str)
        validation errors
    container: Container
        Container object that was used for this data object
    attributes: dict
        Master attributes dictionary
    """

    def __init__(self, data_object_id=None):
        attributes = {}

        # Fetch dataobject from server if id supplied
        if data_object_id is not None:
            attributes = DataObject.fetch_attributes(data_object_id)

        self.__init_attrs(attributes)

        # cached values
        self._container = None
        self._data = None
        self._json = None

    def __init_attrs(self, attributes):
        self.attributes = attributes

        self.id = attributes.get("id")
        self.dataset_id = attributes.get("dataset_id")
        self.content_type = attributes.get("content_type")
        self.format = attributes.get("format")
        self.name = attributes.get("name")
        self.size = attributes.get("size")
        self.status = attributes.get("status")
        self.url = attributes.get("url")
        self.validation_errors = attributes.get("validation_errors")

    @staticmethod
    def fetch_attributes(data_object_id):
        connection = _check_api("data_objects")
        return connection.data_object(data_object_id)

    @staticmethod
    def init_from_attributes(attributes):
        data_object = DataObject()
        data_object.__init_attrs(attributes)

        return data_object

    @staticmethod
    def init_from_id(data_object_id):
        return DataObject(data_object_id)

    @staticmethod
    def init_from_dataset_id(data_object_id):
        connection = _check_api("data_objects")

        # array of attributes
        attributes_arr = connection.data_objects(data_object_id)

        return [DataObject.init_from_attributes(a) for a in attributes_arr]

    @property
    def container(self):
        container_id = self.attributes["container_id"]

        if container_id is None:
            return None

        if not self._container:
            self._container = Container(container_id)

        return self._container

    @property
    def data(self):
        if self._data:
            return self._data

        self._data = requests.get(self.url).content

        return self._data

    @property
    def data_str(self):
        return self.data.decode("utf-8")

    @property
    def json(self):
        if self._json:
            return self._json

        self._json = json.loads(self.data)

        return self._json

    def dataframe(self):
        """Creates a simple Pandas Dataframe"""
        if self.format == "csv" or self.content_type == "text/csv":
            return pd.read_csv(StringIO(self.data_str))
        else:
            return pd.DataFrame(self.json)

    def save_data(self, filepath, chunk_size=1024):
        """Save DataObject data to a file.  Useful for large files"""
        with open(filepath, "wb") as f:
            if self._data:
                f.write(self._data)
                return

            r = requests.get(self.url, stream=True)

            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

    def refresh(self):
        """Refresh DataObject as the url will expire after 1 hour"""
        clone = DataObject.init_from_id(self.id)
        self.__init_attrs(clone.attributes)
