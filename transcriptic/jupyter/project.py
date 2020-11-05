import pandas as pd

from .common import _BaseObject
from .run import Run


class Project(_BaseObject):
    """
    A Project object contains helper methods for managing your runs. You can view the
    runs associated with this project as well as submit runs to the project.

    Example Usage:

    .. code-block:: python

        myProject = Project("My Project")
        projectRuns = myProject.runs()
        myRunId = projectRuns.query("title == 'myRun'").id.item()
        myRun = Run(myRunId)

    Attributes
    ----------
    id : str
        Project id
    name: str
        Project name
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """

    def __init__(self, project_id, attributes=None, connection=None):
        """
        Initialize a Project by providing a project name/id. The attributes and
        connection parameters are generally not specified unless one wants to manually
        initialize the object.

        Parameters
        ----------
        project_id: str
            Project name or id in string form
        attributes: Optional[dict]
            Attributes of the project
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless
            explicitly provided
        """
        super(Project, self).__init__("project", project_id, attributes, connection)
        self._runs = pd.DataFrame()

    def runs(self, use_cache=True):
        """
        Get the list of runs belonging to the project

        Parameters
        ----------
        use_cache: Boolean
            Determines whether the cached list of runs is returned

        Returns
        -------
        DataFrame
            Returns a DataFrame of runs, with the id and title as columns
        """
        if self._runs.empty and use_cache:
            temp = self.connection.env_args
            self.connection.update_environment(project_id=self.id)
            project_runs = self.connection.runs()
            self._runs = pd.DataFrame([[pr["id"], pr["title"]] for pr in project_runs])
            self._runs.columns = ["id", "Name"]
            self.connection.env_args = temp
        return self._runs

    def submit(self, protocol, title, test_mode=False):
        """
        Submit a run to this project

        Parameters
        ----------
        protocol: dict
            Autoprotocol Protocol in dictionary form, can be generated using
            Protocol.as_dict()
        title: Optional[str]
            Title of run. Run-id will automatically be used as name if field is not
            provided
        test_mode: Optional[boolean]
            Determines if run will be submitted will be treated as a test run or a run
            that is meant for execution

        Returns
        -------
        Run
            Returns a run object if run is successfully submitted
        """
        response = self.connection.submit_run(
            protocol, project_id=self.id, title=title, test_mode=test_mode
        )
        return Run(response["id"], response)
