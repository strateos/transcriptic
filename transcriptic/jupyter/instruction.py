import warnings

import pandas as pd


class Instruction(object):
    """
    An Instruction object contains information related to the current instruction such
    as the start, completed time as well as warps associated with the instruction.

    Note that Instruction objects are usually created as part of a run and not created
    explicitly.

    Additionally, if diagnostic information is available, one can click on the
    `Show Diagnostics Data` button to view relevant diagnostic information.

    Example Usage:

        .. code-block:: python

            myRun = Run('r12345')
            myRun.instructions

            # Access instruction object
            myRun.Instructions[1]
            myRun.Instructions[1].warps


    Attributes
    ----------
    id : str
        Instruction id
    name: str
        Instruction name
    warps : DataFrame
        DataFrame of warps in the instruction
    started_at : str
        Time where instruction begun
    completed_at : str
        Time where instruction ended
    device_id: str
        Id of device which instruction was executed on
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object
    """

    def __init__(self, attributes, connection=None):
        """
        Parameters
        ----------
        attributes : dict
            Instruction attributes
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless
            explicitly provided
        """
        self.connection = connection
        self.attributes = attributes
        self.id = attributes["id"]
        self.name = attributes["operation"]["op"]
        self.started_at = attributes["started_at"]
        self.completed_at = attributes["completed_at"]
        self.generated_containers = attributes["generated_containers"]
        if len(attributes["warps"]) > 0:
            device_id_set = set(
                [warp["device_id"] for warp in self.attributes["warps"]]
            )
            self.device_id = device_id_set.pop()
            if len(device_id_set) > 1:
                warnings.warn(
                    "There is more than one device involved in this instruction. Please"
                    " contact Transcriptic for assistance."
                )

        else:
            self.device_id = None
        self._warps = pd.DataFrame()
        self._warp_events = pd.DataFrame()

    @property
    def warps(self):
        if self._warps.empty:
            warp_list = self.attributes["warps"]
            if len(warp_list) != 0:
                self._warps = pd.DataFrame(x["command"] for x in warp_list)
                self._warps.columns = [x.title() for x in self._warps.columns.tolist()]
                # Rearrange columns to start with `Name`
                if "Name" in self._warps.columns:
                    col_names = ["Name"] + [
                        col for col in self._warps.columns if col != "Name"
                    ]
                    self._warps = self._warps[col_names]
                self._warps.insert(1, "WarpId", [x["id"] for x in warp_list])
                self._warps.insert(
                    2, "Completed", [x["reported_completed_at"] for x in warp_list]
                )
                self._warps.insert(
                    3, "Started", [x["reported_started_at"] for x in warp_list]
                )
            else:
                warnings.warn(
                    "There are no warps associated with this instruction. Please "
                    "contact Transcriptic for assistance."
                )
        return self._warps

    @property
    def warp_events(self):
        """
        Warp events include discrete monitoring events such as liquid sensing
        events for a particular instruction.
        """
        # Note: We may consider adding special classes for specific warp
        # events, with more specific annotations/fields.
        if self._warp_events.empty:
            self._warp_events = self.monitoring(data_type="events")
        return self._warp_events

    def monitoring(self, data_type="pressure", grouping=None):
        """
        View monitoring data of a given instruction

        Parameters
        ----------
        data_type: Optional[str]
            Monitoring data type, defaults to 'pressure'
        grouping: Optional[str]
            Determines whether the values will be grouped, defaults to None. E.g. "5:ms"

        Returns
        -------
        DataFrame
            Returns a pandas dataframe of the monitoring data if present.
            Returns an empty dataframe if no data can be found due to errors.
        """
        response = self.connection.monitoring_data(
            instruction_id=self.id, data_type=data_type, grouping=grouping
        )
        # Handle errors by returning empty dataframe
        if "error" in response:
            warnings.warn(response["error"])
            return pd.DataFrame()
        res = pd.DataFrame(response["results"])
        # re-order so that "name" column is always leading
        if "name" in res.columns:
            rearr_cols = ["name"] + res.columns[res.columns != "name"].tolist()
            return res[rearr_cols]
        return res

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="width:450px" seamless></iframe>""" % self.connection.get_route(
            "view_instruction",
            run_id=self.attributes["run_id"],
            project_id=self.attributes["project_id"],
            instruction_id=self.id,
        )
