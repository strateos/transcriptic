from contextlib import contextmanager

import pandas as pd
import pytest

from transcriptic.analysis.spectrophotometry import *
from transcriptic.sampledata.connection import MockConnection
from transcriptic.sampledata.dataset import load_sample_absorbance_dataset


@contextmanager
def mpl_plot_was_rendered():
    """Helper function to ensure that the tested function generates a matplotlib plot"""
    figs_before = plt.gcf().number
    yield
    figs_after = plt.gcf().number
    assert figs_after > figs_before


class TestSpectrophotometry:
    @pytest.fixture(scope="class", autouse=True)
    def init_mock_connection(self):
        yield MockConnection()

    def test_absorbance_object(self):
        sample_dataset = load_sample_absorbance_dataset()

        abs_dataset = Absorbance(
            sample_dataset,
            ["control", "sample1", "sample2"],
            [[0, 1, 2], [12, 13, 14], [24, 25, 26]],
        )

        assert abs_dataset.op_type == "absorbance"
        assert abs_dataset.df.equals(
            pd.DataFrame.from_dict(
                {
                    "control": [0.05, 0.04, 0.06],
                    "sample1": [1.21, 1.13, 1.32],
                    "sample2": [2.22, 2.15, 2.37],
                }
            )
        )
        assert len(abs_dataset.cv) == 3
        with mpl_plot_was_rendered():
            abs_dataset.plot()
        with mpl_plot_was_rendered():
            abs_dataset.beers_law(conc_list=[0, 1, 2])
