import pytest

from pandas import DatetimeTZDtype
from transcriptic.analysis.kinetics import *
from transcriptic.sampledata.connection import MockConnection
from transcriptic.sampledata.dataset import load_sample_kinetics_datasets


class TestKinetics:
    @pytest.fixture(scope="class", autouse=True)
    def init_mock_connection(self):
        yield MockConnection()

    def test_spectrophotometry_object(self):
        sample_datasets = load_sample_kinetics_datasets()

        spectrophotometry_obj = Spectrophotometry(sample_datasets)

        assert spectrophotometry_obj.operation == "absorbance"

        readings = spectrophotometry_obj.readings
        assert isinstance(readings.columns.dtype, DatetimeTZDtype)

        # there isn't a good way to test this currently, let's ensure the calls work
        spectrophotometry_obj.plot()
        spectrophotometry_obj.plot(
            wells=["A1", "A2", "B1", "B2", "C1", "C2"],
            groupby="row",
            title="Test title",
            xlabel="test xlabel",
            ylabel="test ylabel",
        )
