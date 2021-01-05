import warnings

from operator import itemgetter

import pandas as pd

from .common import _BaseObject


class Container(_BaseObject):
    """
    A Container object represents a container from the Transcriptic LIMS and
    contains relevant information on the container type as well as the
    aliquots present in the container.

    Example Usage:
        .. code-block:: python

          my_container = container("ct186apgz6a374")
          my_container.well_map
          my_container.aliquots

          my_container.container_type.col_count
          my_container.container_type.robotize("B1")
          my_container.container_type.humanize(12)

    Attributes
    ----------
    name: str
        Name of container
    well_map: dict
        Well mapping with well indices for keys and well names as values
    aliquots: DataFrame
        DataFrame of aliquots present in the container. DataFrame index
        now corresponds to the Well Index.
    container_type: autoprotocol.container_type.ContainerType
        Autoprotocol ContainerType object with many useful container type
        information and functions.
    cover: str
        Cover type of container
    storage: str
        Storage condition of container

        Example Usage:

        .. code-block:: python

          my_container = container("ct186apgz6a374")

          my_container.well_map

          my_container.container_type.col_count
          my_container.container_type.robotize("B1")
          my_container.container_type.humanize(12)


    """

    def __init__(self, container_id, attributes=None, connection=None):
        """
        Initialize a Container by providing a container name/id. The attributes and
        connection parameters are generally not specified unless one wants to manually
        initialize the object.

        Parameters
        ----------
        container_id: str
            Container name or id in string form
        attributes: Optional[dict]
            Attributes of the container
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless
            explicitly provided
        """
        super(Container, self).__init__(
            "container", container_id, attributes, connection
        )
        # TODO: Unify container "label" with name, add Containers route
        self.id = container_id
        self.cover = self.attributes["cover"]
        self.name = self.attributes["label"]
        self.storage = self.attributes["storage_condition"]
        self.well_map = {
            aliquot["well_idx"]: aliquot["name"]
            for aliquot in self.attributes["aliquots"]
        }
        self.container_type = self._parse_container_type()
        self._aliquots = pd.DataFrame()

    def _parse_container_type(self):
        """Helper function for parsing container string into container object"""

        container_type = self.attributes["container_type"]

        # Return the corresponding AP-Py container object for now. In the future,
        # consider merging the current and future dictionary when instantiating
        # container_type
        try:
            from autoprotocol.container_type import _CONTAINER_TYPES

            return _CONTAINER_TYPES[container_type["shortname"]]
        except ImportError:
            warnings.warn(
                "Please install `autoprotocol-python` in order to get container types"
            )
            return None
        except KeyError:
            warnings.warn("ContainerType given is not supported yet in AP-Py")
            return None

    @property
    def aliquots(self):
        """
        Return a DataFrame of aliquots in the container, along with aliquot
        name, volume, and properties. Row index for the DataFrame corresponds
        to the well index of the aliquot.

        """
        if self._aliquots.empty:
            aliquot_list = self.attributes["aliquots"]
            try:
                from autoprotocol import Unit

                self._aliquots = pd.DataFrame(
                    sorted(
                        [
                            dict(
                                {
                                    "Well Index": x["well_idx"],
                                    "Name": x["name"],
                                    "Id": x["id"],
                                    "Volume": Unit(float(x["volume_ul"]), "microliter"),
                                },
                                **x["properties"],
                            )
                            for x in aliquot_list
                        ],
                        key=itemgetter("Well Index"),
                    )
                )
            except ImportError:
                warnings.warn(
                    "Volume is not cast into Unit-type. Please install "
                    "`autoprotocol-python` in order to have automatic Unit casting"
                )
                self._aliquots = pd.DataFrame(
                    sorted(
                        [
                            dict(
                                {
                                    "Well Index": x["well_idx"],
                                    "Name": x["name"],
                                    "Id": x["id"],
                                    "Volume": float(x["volume_ul"]),
                                },
                                **x["properties"],
                            )
                            for x in aliquot_list
                        ],
                        key=itemgetter("Well Index"),
                    )
                )
            indices = self._aliquots.pop("Well Index")
            self._aliquots.set_index(indices, inplace=True)
        return self._aliquots

    def __repr__(self):
        """
        Return a string representation of a Container using the specified name.
        (ex. Container('my_plate'))

        """
        return "Container(%s)" % (str(self.name))
