# import plotly.plotly as py
import pandas
import matplotlib.pyplot as plt
import plotly.tools as tls
import numpy as np
from plotly.graph_objs import *
from IPython.display import HTML, display
from transcriptic.util import natural_sort, humanize
from transcriptic import dataset as get_dataset


class PlateRead(object):
    '''
    A PlateRead object generalizes the parsing of datasets derived from the
    plate reader for easy statistical analysis and visualization.

    Refer to the Absorbance, Fluorescence and Luminescence objects for more
    information.
    '''
    def __init__(self, dataset, groups, group_well_list=None, control_reading=None, name=None):
        self.name = name
        self.dataset = dataset
        self.control_reading = control_reading
        if "data_keys" not in self.dataset.attributes or len(self.dataset.attributes["data_keys"])==0:
            raise RuntimeError("No data found in given dataset.")
        data_dict = get_dataset(self.dataset.attributes["id"])
        if self.dataset.attributes["instruction"]["operation"]["op"] != "absorbance":
            raise RuntimeError("Data given is not from absorbance operation.")

        # Populate measurement params
        measure_params_dict = {}
        measure_params_dict["wavelength"] = self.dataset.attributes["instruction"]["operation"]["wavelength"]
        measure_params_dict["reader"] = self.dataset.attributes["warp"]["device_id"]
        self.params = measure_params_dict

        # Populate plate field
        plate_info_dict = {}
        plate_info_dict["id"] = self.dataset.attributes["container_type"]["id"]
        plate_info_dict["col_count"] = self.dataset.attributes["container_type"]["col_count"]
        plate_info_dict["well_count"] = self.dataset.attributes["container_type"]["well_count"]
        self.params["plate"] = plate_info_dict

        sorted_keys = natural_sort(data_dict.keys())
        df_dict = {}
        well_count = self.dataset.attributes["container_type"]["well_count"]
        col_count = self.dataset.attributes["container_type"]["col_count"]
        # If no group well list specified, default to including all well data values in one group
        if not group_well_list:
            df_dict[groups[0]] = [x[0] for x in data_dict.values()]
        # If given list of all int, assume one group with all wells in list
        elif all(isinstance(i, int) for i in group_well_list):
            if len(group_well_list) > len(data_dict):
                raise ValueError("Sum of group lengths exceeds total no. of wells.")
            try:
                df_dict[groups[0]] = [data_dict[humanize(well,well_count,col_count).lower()][0] for well in group_well_list]
            except:
                raise ValueError("Well %s is not in the dataset" % well)
        elif all(isinstance(i, list) for i in group_well_list):
            if group_well_list and sum([len(i) for i in group_well_list]) > len(data_dict):
                raise ValueError("Sum of group lengths exceeds total no. of wells.")
            for (idx, well_list) in enumerate(group_well_list):
                try:
                    df_dict[groups[idx]] = [data_dict[humanize(well,well_count,col_count).lower()][0] for well in well_list]
                except:
                    raise ValueError("Well %s is not in the dataset" % well)
        else:
            raise ValueError("Format Error: Group Well List should be a list of list of wells in robot format")

        # To ensure pandas dataframe compatiblity: Check that group len elements are of the same length, pad with NaN otherwise
        if group_well_list and all(isinstance(i, list) for i in group_well_list):
            group_len_list = [len(x) for x in group_well_list]
            if group_len_list.count(group_len_list[0]) != len(group_len_list):
                max_len = max(group_len_list)
                for (idx, group_len) in enumerate(group_len_list):
                    while len(df_dict[groups[idx]]) < max_len:
                        df_dict[groups[idx]].append(float("NaN"))

        self.df = pandas.DataFrame(df_dict, columns=groups)

        # If control absorbance object specified, create df_abj variable by subtracting control df from original
        if control_reading:
            self.df_adj = self.df - control_reading.df

        self.cv = self.df.std()/self.df.mean()*100

    def plot(self, mpl=False):
        # Generates matplotlib obj
        mpl_fig, ax = plt.subplots()
        ax.set_ylabel("Absorbance " + self.params.wavelength)
        ax.set_xlabel("Groups")
        self.df.boxplot(ax=ax)
        #labels = [item.get_text() for item in ax.get_xticklabels()]
        if mpl:
            #return mpl_fig
            return None
        else:
            return plot(tls.mpl_to_plotly(mpl_fig))


class Absorbance(PlateRead):
    '''
    An Absorbance object parses a dataset object and provides functions for
    easy statistical analysis and visualization.

    Parameters
    ----------

    dataset: dataset
      Single dataset selected from datasets object.
    group_labels: list[str]
      Labels for each of the respective groups.
    group_wells: list[int]
      List of list of wells (robot form) belonging to each group in order. E.g. [[1,3,5],[2,4,6]]
    control_abs: Absorbance object
        Absorbance object of water/control blank. If specified, will create adjusted dataframe df_adj
        by subtracting from existing df.

    '''
    def __init__(self, dataset, groups, group_well_list=None, control_reading=None, name=None):


        PlateRead.__init__(self, dataset, groups, group_well_list, control_reading, name)

    def beers_law(self, conc_list=None, use_adj=True, **kwargs):
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
            plot_obj = pandas.DataFrame({"values":dataf.mean(), "conc":np.asarray(conc_list)})
            result = np.polyfit(plot_obj["conc"], plot_obj["values"], 1, full=True)
            gradient, intercept = result[0]
            mpl_fig, ax = plt.subplots()
            plot_obj.plot(x="conc", y="values", kind="scatter", ax=ax, **kwargs)
            plt.plot(plot_obj["conc"], gradient*plot_obj["conc"] + intercept, '-')
            ax.set_ylabel("Absorbance " + self.params["wavelength"])

            # Calculate R^2 from residuals
            ss_res = result[1]
            ss_tot = np.sum(np.square((plot_obj["values"] - plot_obj["values"].mean())))
            print ("%s R^2: %s" % (self.name, (1-ss_res/ss_tot)))



def compare_standards(abs_obj, std_abs_obj):
    # Compare against mean of standard absorbance
    # Check to ensure CVs are at least 2 apart
    for indx in range(len(abs_obj.cv)):
        cv_ratio = abs_obj.cv.iloc[indx]/std_abs_obj.cv.iloc[indx]
        if cv_ratio < 2:
            print "Warning for %s: Sample CV is only %s times that of Standard CV. RMSE may be inaccurate." % (abs_obj.cv.index[indx], cv_ratio)
    # RMSE (normalized wrt to standard mean)
    RMSE = np.sqrt(np.square(abs_obj.df - std_abs_obj.df.mean())).mean() /  std_abs_obj.df.mean()*100
    RMSE = pandas.DataFrame(RMSE, columns=["RMSE % (normalized to standard mean)"])

    sampleVariance = pandas.DataFrame(abs_obj.df.var(), columns=["Sample Variance"])
    sampleCV = pandas.DataFrame(abs_obj.cv, columns=["Sample (%) CV"])

    if abs_obj.name:
        display(HTML("<b>Standards Comparison (%s)</b>" % abs_obj.name))
    print sampleVariance
    print sampleCV
    print RMSE
