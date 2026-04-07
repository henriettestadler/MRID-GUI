# This Python file uses the following encoding: utf-8
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy
from matplotlib import colormaps

class MplWidget_Ephys(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = FigureCanvas(Figure())
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.xaxis.set_visible(False)
        self.ax.set_facecolor((0, 0, 0))
        self.canvas.figure.patch.set_facecolor((0, 0, 0))
        self.canvas.setStyleSheet("background-color: black;")


    def set_subplots(self, n):
        self.canvas.figure.clear()
        self.axes = self.canvas.figure.subplots(n, 1, sharex=True)
        if n == 1:
            self.axes = [self.axes]
