# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy
from matplotlib import colormaps

class MplWidget(QWidget):
    def __init__(self, dwi=False,parent=None):
        super().__init__(parent)
        if dwi == True:
            self.fig = Figure(figsize=(25, 10))
        else:
            self.fig = Figure(figsize=(10, 5))

        self.canvas = FigureCanvas(self.fig)

        self.canvas.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.canvas)

    def get_region_colors(self, regions, cmap_name="tab10"):
        """
        Returns a dict: {region_name: RGBA_color}
        """
        unique_regions = list(dict.fromkeys(regions))  # preserves order
        n = len(unique_regions)

        # Safely resample colormap
        cmap = colormaps[cmap_name].resampled(n)
        colors = cmap.colors

        return dict(zip(unique_regions, colors))
