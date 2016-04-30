from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
from builtins import object
import plotly.plotly as py
import pandas
import matplotlib.pyplot as plt
import plotly.tools as tls
import numpy as np
from IPython.display import HTML, display
from transcriptic.util import humanize
from transcriptic import dataset as get_dataset


class _PlateRead(object):

    """
    A PlateRead object generalizes the parsing of datasets derived from the
    plate reader for easy statistical analysis and visualization.

    Refer to the Absorbance, Fluorescence and Luminescence objects for more
    information.

    """

    def __init__(self, op_type, dataset, group_labels, group_wells=None,
                 control_reading=None, name=None):
        self.name = name
        self.dataset = dataset
        self.control_reading = control_reading
        self.op_type = op_type
        if ("data_keys" not in self.dataset.attributes or
                len(self.dataset.attributes["data_keys"]) == 0):
            raise RuntimeError("No data found in given dataset.")
        if self.op_type not in ["absorbance", "fluorescence", "luminescence"]:
            raise RuntimeError(
                "Data given is not from a spectrophotometry operation.")
        if self.op_type != (self.dataset.attributes["instruction"]["operation"]
                            ["op"]):
            raise RuntimeError("Data given is not a %s operation." % op_type)

        # Populate measurement params
        measure_params_dict = dict()
        measure_params_dict["reader"] = self.dataset.attributes[
            "warp"]["device_id"]
        dataset_op = self.dataset.attributes["instruction"]["operation"]
        if self.op_type == "absorbance":
            measure_params_dict["wavelength"] = dataset_op["wavelength"].split(
                ":")[0] + "nm"
        if self.op_type == "fluorescence":
            measure_params_dict["wavelength"] = (
                "excitation: %s emission: %s" %
                (dataset_op["excitation"].split(":")[0] + "nm",
                 dataset_op["emission"].split(":")[0] + "nm")
                )
        if self.op_type == "luminescence":
            measure_params_dict["wavelength"] = ""

        self.params = measure_params_dict

        # Populate plate field
        plate_info_dict = dict()
        plate_info_dict["id"] = self.dataset.attributes["container"]["id"]
        plate_info_dict["col_count"] = self.dataset.attributes[
            "container"]["container_type"]["col_count"]
        plate_info_dict["well_count"] = self.dataset.attributes[
            "container"]["container_type"]["well_count"]
        self.params["plate"] = plate_info_dict

        # Get dataset and parse into DataFrame
        data_dict = get_dataset(self.dataset.attributes["id"])
        df_dict = {}
        well_count = self.dataset.attributes[
            "container"]["container_type"]["well_count"]
        col_count = self.dataset.attributes[
            "container"]["container_type"]["col_count"]
        # If no group well list specified, default to including all well data
        # values in one group
        if not group_wells:
            df_dict[group_labels[0]] = [x[0] for x in list(data_dict.values())]
        # If given list of all int, assume one group with all wells in list
        elif all(isinstance(i, int) for i in group_wells):
            if len(group_wells) > len(data_dict):
                raise ValueError(
                    "Sum of group lengths exceeds total no. of wells.")
            try:
                df_dict[group_labels[0]] = [
                    data_dict[humanize(well, well_count, col_count).lower()][0]
                    for well in group_wells]
            except:
                raise ValueError("Well %s is not in the dataset" % well)
        elif all(isinstance(i, list) for i in group_wells):
            if group_wells and (sum([len(i) for i in group_wells]) >
                                len(data_dict)):
                raise ValueError(
                    "Sum of group lengths exceeds total no. of wells.")
            for (idx, well_list) in enumerate(group_wells):
                try:
                    df_dict[group_labels[idx]] = [
                        data_dict[humanize(well, well_count, col_count).lower()
                                  ][0] for well in well_list]
                except:
                    raise ValueError("Well %s is not in the dataset" % well)
        else:
            raise ValueError(
                "Format Error: Group Well List should be a list of list of \
                 wells in robot format")

        # To ensure pandas dataframe compatiblity: Check that group len
        # elements are of the same length, pad with NaN otherwise
        if group_wells and all(isinstance(i, list) for i in group_wells):
            group_len_list = [len(x) for x in group_wells]
            if group_len_list.count(group_len_list[0]) != len(group_len_list):
                max_len = max(group_len_list)
                for (idx, group_len) in enumerate(group_len_list):
                    while len(df_dict[group_labels[idx]]) < max_len:
                        df_dict[group_labels[idx]].append(float("NaN"))

        self.df = pandas.DataFrame(df_dict, columns=group_labels)

        # If control absorbance object specified, create df_abj variable by
        # subtracting control df from original
        if control_reading:
            self.df_adj = self.df - control_reading.df

        self.cv = self.df.std()/self.df.mean()*100

    def plot(self, mpl=True, plot_type="box", **plt_kwargs):
        """
        Parameters
        ----------
        mpl : boolean, optional
            Set to True to render a matplotlib plot, otherwise a Plotly plot
            is rendered
        plot_type : {"box", "bar", "line", "hist"}, optional
            Type of plot to render
        \**plot_kwargs : dict, optional
            Optional dictionary of specifications for your plot type of choice
        """
        mpl_fig, ax = plt.subplots()
        nl = "\n" if mpl else "<br>"
        ax.set_ylabel(self.op_type + nl + self.params["wavelength"])
        self.df.plot(kind=plot_type, ax=ax)
        labels = [item.label.get_text() for item in ax.xaxis.get_major_ticks()]
        if mpl:
            return None
        else:
            if not plt_kwargs:
                plt_kwargs = {
                    "layout": {
                        "xaxis": {
                            "tickmode": "array",
                            "ticktext": labels,
                            "tickvals": list(range(1, len(labels)+1)),
                            "tickangle": 0,
                            "tickfont": {
                                "size": 10
                            },
                        }
                    }
                }
            pyfig = tls.mpl_to_plotly(mpl_fig)
            pyfig.update(plt_kwargs)
            return py.iplot(pyfig)


class Absorbance(_PlateRead):

    """
    An Absorbance object parses a dataset object and provides functions for
    easy statistical analysis and visualization.

    Parameters
    ----------

    dataset: dataset
        Single dataset selected from datasets object
    group_labels: list[str]
        Labels for each of the respective groups
    group_wells: list[int]
        List of list of wells (robot form) belonging to each group in order.
        E.g. [[1,3,5],[2,4,6]]
    control_abs: Absorbance object, optional
        Absorbance object of water/control blank. If specified, will create
        adjusted dataframe df_adj by subtracting from existing df
    name: str, optional
        Name of absorbance object. Used in plotting functions

    """

    def __init__(self, dataset, group_labels, group_wells=None,
                 control_abs=None, name=None):
        _PlateRead.__init__(self, "absorbance", dataset, group_labels,
                            group_wells, control_abs, name)

    def beers_law(self, conc_list=None, use_adj=True, **kwargs):
        """"
        Apply Beer-Lambert's law to a series of absorbance readings and get
        an estimation of the linearity between the absorbance and concentration
        values.

        Parameters
        ----------

        conc_list: list[double], optional
            List of concentrations of dye used
        use_adj: Boolean, optional
            Booelan option which determines if the adjusted absorbance readings
            are used
        \**plot_kwargs : dict
            Optional dictionary of specifications for your plot type of choice
        """
        if "title" not in kwargs:
            if self.name:
                kwargs["title"] = "Beer's Law (%s)" % self.name
            else:
                kwargs["title"] = "Beer's Law"
        if "yerr" not in kwargs:
            kwargs["yerr"] = self.df.std()

        # Use df_adj for beer's law if control abs object was given
        if use_adj and self.control_reading:
            dataf = self.df_adj
        else:
            dataf = self.df
        # Use default labels if concentration not provided
        if not conc_list:
            if "xlim" not in kwargs:
                kwargs["xlim"] = (-1, len(dataf.mean()))
            dataf.mean().plot(**kwargs)
        else:
            plot_obj = pandas.DataFrame(
                {"values": dataf.mean(), "conc": np.asarray(conc_list)})
            result = np.polyfit(
                plot_obj["conc"], plot_obj["values"], 1, full=True)
            gradient, intercept = result[0]
            mpl_fig, ax = plt.subplots()
            plot_obj.plot(
                x="conc", y="values", kind="scatter", ax=ax, **kwargs)
            plt.plot(
                plot_obj["conc"], gradient*plot_obj["conc"] + intercept, '-')
            ax.set_ylabel("Absorbance " + self.params["wavelength"])

            # Calculate R^2 from residuals
            ss_res = result[1]
            ss_tot = np.sum(
                np.square((plot_obj["values"] - plot_obj["values"].mean())))
            print("%s R^2: %s" % (self.name, (1-old_div(ss_res, ss_tot))))


class Fluorescence(_PlateRead):

    """
    An Fluorescence object parses a dataset object and provides functions for
    easy statistical analysis and visualization.

    Parameters
    ----------

    dataset: dataset
        Single dataset selected from datasets object
    group_labels: list[str]
        Labels for each of the respective groups
    group_wells: list[int]
        List of list of wells (robot form) belonging to each group in order.
        E.g. [[1,3,5],[2,4,6]]
    control_fluor: Fluorescence object, optional
        Fluorescence object of water/control blank. If specified, will create
        adjusted dataframe df_adj by subtracting from existing df
    name: str, optional
        Name of fluorescence object. Used in plotting functions

    """

    def __init__(self, dataset, group_labels, group_wells=None,
                 control_fluor=None, name=None):
        _PlateRead.__init__(self, "fluorescence", dataset, group_labels,
                            group_wells, control_fluor, name)


class Luminescence(_PlateRead):

    """
    An Luminescence object parses a dataset object and provides functions for
    easy statistical analysis and visualization.

    Parameters
    ----------

    dataset: dataset
        Single dataset selected from datasets object
    group_labels: list[str]
        Labels for each of the respective groups
    group_wells: list[int]
        List of list of wells (robot form) belonging to each group in order.
        E.g. [[1,3,5],[2,4,6]]
    control_lumi: Luminescence object, optional
        Luminescence object of water/control blank. If specified, will create
        adjusted dataframe df_adj by subtracting from existing df
    name: str, optional
        Name of luminescence object. Used in plotting functions

    """

    def __init__(self, dataset, group_labels, group_wells=None,
                 control_lumi=None, name=None):
        _PlateRead.__init__(self, "luminescence", dataset, group_labels,
                            group_wells, control_lumi, name)


def compare_standards(pr_obj, std_pr_obj):
    """
    Compare a sample plate read object with a standard plate read object to get
    measures such as the Root-Mean-Square-Error (RMSE) and
    Coefficient-of-Variation (CV).


    Parameters
    ----------

    pr_obj: _PlateRead
        Sample plate read object
    std_pr_obj: _PlateRead
        Standard plate read object
    """
    # Compare against mean of standard absorbance
    # Check to ensure CVs are at least 2 apart
    for indx in range(len(pr_obj.cv)):
        cv_ratio = old_div(pr_obj.cv.iloc[indx], std_pr_obj.cv.iloc[indx])
        if cv_ratio < 2:
            print("Warning for %s: Sample CV is only %s times that of Standard \
                CV. RMSE may be inaccurate." % (
                pr_obj.cv.index[indx], cv_ratio))
    # RMSE (normalized wrt to standard mean)
    RMSE = (np.sqrt(np.square(pr_obj.df - std_pr_obj.df.mean()).mean()) /
            std_pr_obj.df.mean() * 100)
    RMSE = pandas.DataFrame(
        RMSE, columns=["RMSE % (normalized to standard mean)"])

    sampleVariance = pandas.DataFrame(
        pr_obj.df.var(), columns=["Sample Variance"])
    sampleCV = pandas.DataFrame(pr_obj.cv, columns=["Sample (%) CV"])

    if pr_obj.name:
        display(HTML("<b>Standards Comparison (%s)</b>" % pr_obj.name))
    print(sampleVariance)
    print(sampleCV)
    print(RMSE)
