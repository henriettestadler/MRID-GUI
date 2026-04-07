# This Python file uses the following encoding: utf-8
from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QDockWidget
from PySide6.QtGui import QKeySequence,QShortcut

class ClickablePlotWidget(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.PgWidget = parent  # reference to your PgEphysWidget
        self.scroll_time = False
        self.zooming = False
        self.rect_item = None


    def mouseDoubleClickEvent(self, event):
        vb = self.getViewBox()
        pos = vb.mapSceneToView(event.position())
        x = pos.x()
        y = pos.y()
        # Pass event up to main widget
        channel_idx = self.PgWidget.find_closest_line( x, y)

        # highlight line and focus on point
        print('mouseDoubleClickEvent',flush=True)
        self.PgWidget.VisEphys.Vis3D.manually_pick_point(point=[],idx=channel_idx)
        self.PgWidget.VisEphys.highlight_channel(channel_idx)

        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.scroll_time = True
            self.pos_original = event.globalPos()
        elif event.button() == Qt.LeftButton:
            self.zooming = True
            self.pos_original = self.plotItem.vb.mapSceneToView(event.pos())
            print(self.pos_original,flush=True)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.scroll_time = False
        elif event.button() == Qt.LeftButton:
            ## zooming
            pos = self.plotItem.vb.mapSceneToView(event.pos())
            #print('width',pos.x() - self.pos_original.x(),flush=True) #sec
            #print('height',pos.y() - self.pos_original.y(),flush=True) #some unit
            if pos.x() > self.pos_original.x():
                self.xMin = self.pos_original.x()
                self.xMax = pos.x()
            else:
                self.xMin = pos.x()
                self.xMax = self.pos_original.x()

            if pos.y() > self.pos_original.y():
                self.yMin = self.pos_original.y()
                self.yMax = pos.y()
            else:
                self.yMin = pos.y()
                self.yMax = self.pos_original.y()
            self.PgWidget.plot.setXRange(self.xMin,self.xMax)
            self.PgWidget.plot.setYRange(self.yMin,self.yMax)
            self.PgWidget.plot.setLimits(yMin=self.yMin, yMax=self.yMax,xMin=self.xMin,xMax=self.xMax)
            self.zooming = False

    def mouseMoveEvent(self, event):
        if self.scroll_time:
            pos = event.globalPos()  # position on screen
            delta = pos-self.pos_original
            if delta.x() != 0:  # horizontal scroll
                self.PgWidget.VisEphys.time_start = max(0,self.PgWidget.VisEphys.time_start+delta.x()/1000)
                self.PgWidget.VisEphys.time_end += delta.x()/1000
                signal = self.PgWidget.VisEphys.read_data.analogsignals[0].load(time_slice=(self.PgWidget.VisEphys.time_start,self.PgWidget.VisEphys.time_end),channel_indexes=self.PgWidget.displayed_channels)
                self.PgWidget.plot_ephys(signal.times, signal.magnitude, self.PgWidget.displayed_channels)

                #change slots

                self.PgWidget.MW.ui.spinBox_startMin.blockSignals(True)
                self.PgWidget.MW.ui.spinBox_startS.blockSignals(True)
                self.PgWidget.MW.ui.spinBox_startMs.blockSignals(True)
                self.PgWidget.MW.ui.horizontalSlider_ephys.blockSignals(True)
                time_start_min = int(self.PgWidget.VisEphys.time_start/60)
                time_start_sec = int(self.PgWidget.VisEphys.time_start - time_start_min*60)
                time_start_ms = int((self.PgWidget.VisEphys.time_start - time_start_min*60-time_start_sec)*1000)
                self.PgWidget.MW.ui.horizontalSlider_ephys.setValue(self.PgWidget.VisEphys.time_start*1000) #ms
                self.PgWidget.MW.ui.spinBox_startMin.setValue(time_start_min) #min
                self.PgWidget.MW.ui.spinBox_startS.setValue(time_start_sec) #sec
                self.PgWidget.MW.ui.spinBox_startMs.setValue(time_start_ms) #ms
                self.PgWidget.MW.ui.horizontalSlider_ephys.blockSignals(False)
                self.PgWidget.MW.ui.spinBox_startMin.blockSignals(False)
                self.PgWidget.MW.ui.spinBox_startS.blockSignals(False)
                self.PgWidget.MW.ui.spinBox_startMs.blockSignals(False)
        elif self.zooming:
            pos = self.plotItem.vb.mapSceneToView(event.pos())
            #pos = event.globalPos()
            if self.rect_item is not None:
                    self.removeItem(self.rect_item)
            # draw new rect
            self.rect_item = pg.QtWidgets.QGraphicsRectItem(
                QRectF(self.pos_original.x(), self.pos_original.y(),
                       pos.x() - self.pos_original.x(),
                       pos.y() - self.pos_original.y())
            )
            self.rect_item.setPen(pg.mkPen('r'))
            self.rect_item.setBrush(pg.mkBrush(255, 255, 255, 50))  # semi-transparent
            self.addItem(self.rect_item)

            print('width',pos.x() - self.pos_original.x(),flush=True) #sec
            print('height',pos.y() - self.pos_original.y(),flush=True) #some unit


            # box from self.pos_original to pos
            # -> get ms and uV (print


        super().mouseMoveEvent(event)



    #def wheelEvent(self, event):




class PgWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)

        # Layout
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        # Single plot widget
        self.plot = ClickablePlotWidget(self) #pg.PlotWidget()
        self.plot.setBackground('k')  # black background
        self.plot.showAxis('bottom', show=False)  # hide x-axis
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.layout.addWidget(self.plot)

        # Store plotted lines
        self.lines = {}
        self.displayed_channels = []

        self.slot_height = 1.0
        self.amplitude = 1.0

    def init_PgWidget_class(self, VisEphys,MW):
        self.MW = MW
        self.VisEphys = VisEphys
        #self.ui.pushButton_openfile100um.clicked.connect(lambda: self.LoadMRI.Resample.open_as_new_file(self,self.MW))
        self.MW.ui.pushButtonAmp_plus.clicked.connect(lambda: self.change_amplitude(+0.2))
        self.MW.ui.pushButtonAmp_minus.clicked.connect(lambda: self.change_amplitude(-0.2))

        self.MW.ui.dockWidget_ephys.topLevelChanged.connect(self.on_dock_floating_changed)

        #ctrl D ctrl I
        ctrl_d = QShortcut(QKeySequence("Ctrl+D"), self.MW.ui.Dock_ephys)
        ctrl_d.activated.connect(self.MW.ui.pushButtonAmp_minus.click)
        ctrl_i = QShortcut(QKeySequence("Ctrl+I"), self.MW.ui.Dock_ephys)
        ctrl_i.activated.connect(self.MW.ui.pushButtonAmp_plus.click)

        self.xMin = self.VisEphys.time_start
        self.xMax = self.VisEphys.time_end
        self.yMin = -self.slot_height
        self.yMax = len(self.VisEphys.all_channels) * self.slot_height

    def on_dock_floating_changed(self, floating):
        if floating:
            self.MW.ui.dockWidget_ephys.showFullScreen()

    def change_amplitude(self,amplitude_change):
        signal = self.VisEphys.read_data.analogsignals[0].load(time_slice=(self.VisEphys.time_start,self.VisEphys.time_end),channel_indexes=self.displayed_channels)
        self.amplitude = max(0.01,self.amplitude+amplitude_change)

        #plot channels new and highlight current selected channel
        self.plot_ephys(signal.times, signal.magnitude, self.displayed_channels)
        if self.VisEphys.Vis3D.table_excel.currentRow()!=-1:
            self.VisEphys.highlight_channel(ch_idx=self.VisEphys.Vis3D.table_excel.currentRow())



    def plot_ephys(self,signal_times, signal_data, channels):
        """
        signal_times: 1D array of times (seconds)
        signal_data: 2D array (samples x channels)
        channels: list of channel indices to display
        slot_height: vertical offset per channel
        """
        self.plot.clear()
        self.lines = {}
        self.displayed_channels = []
        self.lines_values = {}

        n_samples, n_channels = signal_data.shape

        for index,_ in enumerate(self.VisEphys.all_channels):
            self.lines[index] = None
            self.lines_values[index] = None

        for i,ch_idx in enumerate(channels):
            index = self.VisEphys.all_channels.index(ch_idx)

            # offset each channel
            offset = (len(self.VisEphys.all_channels)-1-index) * self.slot_height
            ch = signal_data[:, i]
            if ch.size==0:
                continue

            # normalize each channel independently to [-0.5, 0.5]
            ch_range = ch.max() - ch.min()
            ch_norm = (ch - ch.mean()) / ch_range

            # offset and plot
            max_idx = self.VisEphys.Vis3D.atlaslabelsdf['IDX'].max()
            j = self.VisEphys.Vis3D.chMap.index(ch_idx)
            channel_id = self.VisEphys.Vis3D.points_data['Channel'].iloc[j]
            rgba = self.VisEphys.Vis3D.cmap(channel_id / max_idx)
            r, g, b,a = rgba

            pen = pg.mkPen(color=(int(r*255), int(g*255), int(b*255),int(a*255)), width=0.5)
            line = self.plot.plot(signal_times, ch_norm * self.amplitude + offset, pen=pen)

            self.displayed_channels.append(ch_idx)
            self.lines[index] = line
            self.lines_values[index] = (signal_times, ch_norm + offset)
            i+=1

        # y-axis ticks in the center of each channel slot
        yticks = [((len(self.VisEphys.all_channels)-1-index) * self.slot_height, str(ch)) for index, ch in enumerate(self.VisEphys.all_channels)]
        self.plot.getAxis('left').setTicks([yticks])
        self.plot.setXRange(self.xMin,self.xMax)
        self.plot.setYRange(self.yMin,self.yMax)
        self.plot.setLimits(yMin=self.yMin, yMax=self.yMax,xMin=self.xMin,xMax=self.xMax)

        return self.displayed_channels,self.lines


    def find_closest_line(self, x_click, y_click):
        closest_line = None
        min_distance = float('inf')

        for i, val in self.lines_values.items():
            if val is None:
                continue
            x, y = val
            if len(x) == 0:
                continue
            # find nearest time index
            idx = np.searchsorted(x.magnitude, x_click)
            idx = np.clip(idx, 0, len(x.magnitude) - 1)

            y_at_x = y[idx]

            # compare vertical distance ONLY
            distance = abs(y_at_x - y_click)

            if distance < min_distance:
                min_distance = distance
                closest_line = i

        return closest_line



