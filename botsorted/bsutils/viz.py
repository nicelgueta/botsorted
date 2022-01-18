from bokeh.layouts import gridplot
from bokeh.plotting import figure, output_file, show
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.models.tools import (
    PanTool,
    SaveTool,
    WheelZoomTool,
    ResetTool,
    CrosshairTool,
)

import numpy as np
import pandas as pd

from ..config import config
from ..ml.dr import DirectReinforcementModel


def datet(x):
    return np.array(x, dtype=np.datetime64)


class DataVisualiser:
    @staticmethod
    def plot_perf(
        data: pd.DataFrame,
        mod: DirectReinforcementModel,
        tail: int = config["chartTail"],
        modelName: str = f"{config['modelName']} v{config['modelVersion']}",
    ) -> str:  # returns HTML str
        data = data.tail(tail)
        data = DataVisualiser.add_positions_to_data(mod, data)
        data = DataVisualiser.add_performance_to_data(mod, data)
        p1 = figure(
            x_axis_type="datetime",
            title="Cumulative Returns by Strategy",
            plot_width=800,
            plot_height=500,
        )
        p1.grid.grid_line_alpha = 0.3
        p1.xaxis.axis_label = "Date"
        p1.yaxis.axis_label = "Cumulative Returns"

        p1.toolbar.logo = None
        p1.tools = [
            PanTool(),
            # SaveTool(),
            WheelZoomTool(),
            ResetTool(),
            CrosshairTool(),
        ]

        p1.line(  # pylint: disable=too-many-function-args
            datet(data.closeTimeIso),
            data.modelReturnsCumSum,
            color="#33A02C",
            legend_label=modelName,
        )
        p1.line(  # pylint: disable=too-many-function-args
            datet(data.closeTimeIso),
            data.buyHoldReturns,
            color="#FB9A99",
            legend_label="HODL",
        )

        return file_html(p1, CDN), data

    @staticmethod
    def add_positions_to_data(mod, data, addip1=False):
        if addip1:
            data["close"] = pd.Series(
                list(data.close.astype(float))
                + [data.close.astype(float)[data.close.index[-1]]]
            )
        fts = mod.calc_Ft(mod.get_x(data.close.astype(float)), mod.theta)
        data["posFt"] = [0] + list(np.sign(fts))
        data["pos"] = ["L" if f > 0 else "S" if f < 0 else np.NaN for f in data.posFt]

        # remove time when model is computing first M window as not relevant for assessment
        data = data.tail(
            len(data) - mod.M + 1
        )  # minus the lookback window +1 to inlcude the one where it starts off which is 0
        return data

    @staticmethod
    def add_performance_to_data(mod, data):
        data["modelReturnsCumSum"] = (data.close.diff() * data.posFt).cumsum()
        data["buyHoldReturns"] = data.close.diff().cumsum()  # [0]+list(x.cumsum())
        return data
