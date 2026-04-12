# This Python file uses the following encoding: utf-8
from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtCore import QRectF
from PySide6.QtGui import QKeySequence,QShortcut
from PySide6 import QtGui

class ClickablePlotWidget(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.PgWidget = parent  # reference to your PgEphysWidget
        self.scroll_time = False
        self.zooming = False
        self.measurement = False
        self.timeline = False
        self.rect_item = None
        self.timeline_item = None
        self.measurement_text = {}


    def mouseDoubleClickEvent(self, event):
        vb = self.getViewBox()
        pos = vb.mapSceneToView(event.position())
        x = pos.x()
        y = pos.y()
        # Pass event up to main widget
        channel_idx = self.PgWidget.find_closest_line(x, y)

        # highlight line and focus on point
        self.PgWidget.VisEphys.Vis3D.manually_pick_point(point=[],idx=channel_idx)
        self.PgWidget.VisEphys.highlight_channel(channel_idx)

        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.scroll_time = True
            self.pos_original = event.globalPos()
        elif event.button() == Qt.LeftButton:
            if self.PgWidget.MW.ui.pushButton_measurement.isChecked():
                self.measurement = True
            elif self.PgWidget.MW.ui.pushButton_timeline.isChecked():
                self.timeline = True
            else:
                self.zooming = True
            self.pos_original = self.plotItem.vb.mapSceneToView(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.scroll_time = False
        elif event.button() == Qt.LeftButton:
            pos = self.plotItem.vb.mapSceneToView(event.pos())
            if self.zooming:
                diff_x = self.PgWidget.xMax - self.PgWidget.xMin
                diff_y = self.PgWidget.yMax - self.PgWidget.yMin
                if self.rect_item is not None:
                    self.removeItem(self.rect_item)
                if abs(pos.x() - self.pos_original.x()) < diff_x/75 and abs(pos.y() - self.pos_original.y()) < diff_y/75:
                    self.zooming = False
                    return
                if pos.x() > self.pos_original.x():
                    self.PgWidget.xMin = max(self.pos_original.x(),self.PgWidget.VisEphys.time_start)
                    self.PgWidget.xMax = min(pos.x(),self.PgWidget.VisEphys.time_end)

                else:
                    self.PgWidget.xMin = max(pos.x() ,self.PgWidget.VisEphys.time_start)
                    self.PgWidget.xMax = min(self.pos_original.x(),self.PgWidget.VisEphys.time_end)

                if not self.PgWidget.MW.ui.pushButton_selectTime.isChecked():
                    if pos.y() > self.pos_original.y():
                        self.PgWidget.yMin = max(self.pos_original.y(),-self.PgWidget.slot_height)
                        self.PgWidget.yMax = min(pos.y(), (len(self.PgWidget.MW.Ephys.ephys_data.all_channels)-1) * self.PgWidget.slot_height)
                    else:
                        self.PgWidget.yMin = max(pos.y(),-self.PgWidget.slot_height)
                        self.PgWidget.yMax = min(self.pos_original.y(), (len(self.PgWidget.MW.Ephys.ephys_data.all_channels)-1) * self.PgWidget.slot_height)
                self.PgWidget.plot.setLimits(yMin=self.PgWidget.yMin, yMax=self.PgWidget.yMax,xMin=self.PgWidget.xMin,xMax=self.PgWidget.xMax)
                self.PgWidget.plot.setXRange(self.PgWidget.xMin,self.PgWidget.xMax)
                self.PgWidget.plot.setYRange(self.PgWidget.yMin,self.PgWidget.yMax)


                self.zooming = False
                self.rect_item = None
            elif self.measurement:
                self.measurement =False
                for idx in list(self.measurement_text.keys()):
                        self.removeItem(self.measurement_text.pop(idx))
                if hasattr(self,"plot_points"):
                    self.removeItem(self.plot_points)
                    del self.plot_points
                self.removeItem(self.rect_item)
                self.rect_item = None
            elif self.timeline:
                self.removeItem(self.timeline_item)
                if hasattr(self,'timeline_text'):
                    self.removeItem(self.timeline_text)
                self.timeline =False
                self.timeline_item = None


    def mouseMoveEvent(self, event):
        if self.scroll_time:
            pos = event.globalPos()  # position on screen
            delta = pos-self.pos_original
            if delta.x() != 0:  # horizontal scroll
                self.PgWidget.VisEphys.time_start = max(0,self.PgWidget.VisEphys.time_start+delta.x()/1000)
                self.PgWidget.VisEphys.time_end += delta.x()/1000
                signal = self.PgWidget.VisEphys.read_data.analogsignals[0].load(time_slice=(self.PgWidget.VisEphys.time_start,self.PgWidget.VisEphys.time_end),channel_indexes=self.PgWidget.displayed_channels)
                self.PgWidget.VisEphys.displayed_channels,self.PgWidget.VisEphys.ephys_lines = self.PgWidget.plot_ephys(signal.times, signal.magnitude, self.PgWidget.displayed_channels)

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
            #pos_scene = self.plotItem.vb.mapViewToScene(pos)
            #pos_original_scene = self.plotItem.vb.mapViewToScene(self.pos_original)
            if hasattr(self, '_last_pos') and abs(pos.x() - self._last_pos.x()) < 1e-6 and abs(pos.y() - self._last_pos.y()) < 1e-6:
                return
            self._last_pos = pos
            # draw new rect
            if self.rect_item is None:
                self.rect_item = pg.QtWidgets.QGraphicsRectItem()
                self.rect_item.setPen(pg.mkPen('w'))
                self.rect_item.setBrush(pg.mkBrush(255, 255, 255, 50))
                self.addItem(self.rect_item)

            if not self.PgWidget.MW.ui.pushButton_selectTime.isChecked():
                self.rect_item.setRect(QRectF(
                    self.pos_original.x(), self.pos_original.y(),
                    pos.x() - self.pos_original.x(),
                    pos.y() - self.pos_original.y()
                ).normalized())
            else:
                self.rect_item.setRect(QRectF(
                    self.pos_original.x(), self.PgWidget.yMin,
                    pos.x() - self.pos_original.x(),
                    self.PgWidget.yMax-self.PgWidget.yMin
                ).normalized())

        elif self.timeline:
            pos = self.plotItem.vb.mapSceneToView(event.pos())
            if self.timeline_item is None:
                self.timeline_item = pg.QtWidgets.QGraphicsLineItem()
                self.timeline_item.setPen(pg.mkPen('w'))
                self.addItem(self.timeline_item)

                self.timeline_text = pg.TextItem(color='w', anchor=(0, 1),fill=pg.mkBrush(0, 0, 0, 150),border=pg.mkPen('w', width=1))
                self.timeline_text.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
                self.addItem(self.timeline_text)

            self.timeline_item.setLine(pos.x(), self.PgWidget.yMin, pos.x(), self.PgWidget.yMax)
            mins = int(pos.x() // 60)
            secs = int(pos.x() % 60)
            ms = int((pos.x() % 1) * 1000)
            self.timeline_text.setText(f"Time: {mins}:{secs:02d}.{ms:03d}, {(pos.x()):.3f} sec")
            self.timeline_text.setPos(self.PgWidget.xMin, self.PgWidget.yMin)



        elif self.measurement:
            pos = self.plotItem.vb.mapSceneToView(event.pos())

            if self.rect_item is None:
                # draw new rect
                self.rect_item = pg.QtWidgets.QGraphicsRectItem()
                self.rect_item.setPen(pg.mkPen('r'))
                self.rect_item.setBrush(pg.mkBrush(255, 255, 255, 50))  # semi-transparent
                self.addItem(self.rect_item)

            self.rect_item.setRect(QRectF(
                self.pos_original.x(), self.pos_original.y(),
                pos.x() - self.pos_original.x(),
                pos.y() - self.pos_original.y()
            ).normalized())

            self.measure_from_pos(pos)


        super().mouseMoveEvent(event)


    def activate_measurement(self,val):
        # Then style the checked state
        self.PgWidget.MW.ui.pushButton_selectTime.setChecked(False)
        self.PgWidget.MW.ui.pushButton_timeline.setChecked(False)


    def select_timeframe(self,val):
        self.PgWidget.MW.ui.pushButton_measurement.setChecked(False)
        self.PgWidget.MW.ui.pushButton_timeline.setChecked(False)


    def draw_timeline(self,val):
        self.PgWidget.MW.ui.pushButton_selectTime.setChecked(False)
        self.PgWidget.MW.ui.pushButton_measurement.setChecked(False)

    def measure_from_pos(self,pos):
        # get the times
        t1 = pos.x() if pos.x() < self.pos_original.x() else self.pos_original.x()
        t2 = self.pos_original.x() if pos.x() < self.pos_original.x() else pos.x()

        # get the data
        y1 = pos.y() if pos.y() < self.pos_original.y() else self.pos_original.y()
        y2 = self.pos_original.y() if pos.y() < self.pos_original.y() else pos.y()

        steps = np.arange(y1+self.PgWidget.slot_height*0.1, y2-self.PgWidget.slot_height*0.1, self.PgWidget.slot_height)
        channels_measurement = []
        line_indices = []
        for y_datapoint in steps:
            idx = self.PgWidget.find_closest_line(pos.x(), y_datapoint)
            channel_idx = self.PgWidget.MW.Ephys.ephys_data.all_channels[idx]
            if channel_idx in self.PgWidget.displayed_channels and channel_idx not in channels_measurement:
                channels_measurement.append(channel_idx)
                line_indices.append(idx)

        if channels_measurement == [] or abs(t2-t1)<1e-4:
            return

        signal = self.PgWidget.VisEphys.read_data.analogsignals[0].load(time_slice=(t1,t2),channel_indexes=channels_measurement)

        points_x = []
        points_y = []


        for idx,ch_idx in enumerate(channels_measurement):
            signal_data = signal.magnitude[:, idx]
            ch_max = np.max(signal_data)
            ch_min = np.min(signal_data)
            t_max = signal.times[np.argwhere(signal_data==ch_max)[0][0]]
            t_min = signal.times[np.argwhere(signal_data==ch_min)[0][0]]
            diff_y_uV = (ch_max-ch_min)*0.192
            signal_times, ch_norm, offset = self.PgWidget.lines_values[line_indices[idx]]
            values = ch_norm + offset
            y_max=values[np.argmin(np.abs(signal_times - t_max))]
            y_min=values[np.argmin(np.abs(signal_times - t_min))]
            points_x.append(t_max)
            points_x.append(t_min)
            points_y.append(y_max)
            points_y.append(y_min)

            mins = abs(int(float(t_max-t_min) // 60))
            secs = abs(int(float(t_max-t_min) % 60))
            ms = abs(int((float(t_max-t_min) % 1) * 1000))

            if idx not in self.measurement_text:
                self.measurement_text[idx] = pg.TextItem(
                    color='w', anchor=(0, 1), fill=pg.mkBrush(0, 0, 0, 150),
                    border=pg.mkPen('w', width=1),
                )
                self.addItem(self.measurement_text[idx])

            diff_y = self.PgWidget.yMax -self.PgWidget.yMin #diff_y/20
            print(self.PgWidget.yMin + idx*diff_y/(len(self.PgWidget.MW.Ephys.ephys_data.all_channels) * self.PgWidget.slot_height)*2,flush=True)
            self.measurement_text[idx].setText(f"Ch {ch_idx}: {mins}:{secs:02d}.{ms:03d}, {(diff_y_uV):.3f} uV")
            self.measurement_text[idx].setPos(self.PgWidget.xMin, self.PgWidget.yMin + idx*diff_y/(len(self.PgWidget.MW.Ephys.ephys_data.all_channels) * self.PgWidget.slot_height)*2) #*0.015
            self.measurement_text[idx].setFont(QtGui.QFont("Arial", self.height()*0.015, QtGui.QFont.Bold))

        # Remove leftover items if channel count decreased
        for idx in list(self.measurement_text.keys()):
            if idx >= len(channels_measurement):
                self.removeItem(self.measurement_text.pop(idx))

        if hasattr(self, "plot_points"):
            self.plot_points.setData(points_x, points_y)
        else:
            self.plot_points = self.plot(points_x, points_y, pen=None, symbol='o')
        # -> get ms and uV


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
        self.plot.getViewBox().setMenuEnabled(False)
        self.plot.hideButtons()

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
        self.yMax = len(self.MW.Ephys.ephys_data.all_channels) * self.slot_height

    def on_dock_floating_changed(self, floating):
        if floating:
            self.MW.ui.dockWidget_ephys.showFullScreen()

    def change_amplitude(self,amplitude_change):
        #signal = self.VisEphys.read_data.analogsignals[0].load(time_slice=(self.VisEphys.time_start,self.VisEphys.time_end),channel_indexes=self.displayed_channels)
        self.amplitude = max(0.01,self.amplitude+amplitude_change)

        for index, line in self.lines.items():
            if line is None:
                continue
            signal_times, ch_norm, offset = self.lines_values[index]
            line.setData(signal_times, ch_norm * self.amplitude + offset)

        ##plot channels new and highlight current selected channel
        #self.VisEphys.displayed_channels,self.VisEphys.ephys_lines = self.plot_ephys(signal.times, signal.magnitude, self.displayed_channels,clear=False)
        ##if self.VisEphys.Vis3D.table_excel.currentRow()!=-1:
        #self.VisEphys.highlight_channel(ch_idx=self.VisEphys.ch_highlight)



    def plot_ephys(self,signal_times, signal_data, channels,clear=True):
        """
        signal_times: 1D array of times (seconds)
        signal_data: 2D array (samples x channels)
        channels: list of channel indices to display
        slot_height: vertical offset per channel
        """
        if clear:
            self.plot.clear()
        else:
            #remove all lines
            for line in self.lines.values():
                self.plot.removeItem(line)

        show_all = self.MW.ui.pushButton_showChannels.isChecked()

        self.lines = {}
        self.displayed_channels = []
        self.lines_values = {}
        self.signal_data = signal_data
        self.signal_times = signal_times

        n_samples, n_channels = signal_data.shape

        for index,_ in enumerate(self.MW.Ephys.ephys_data.all_channels):
            self.lines[index] = None
            self.lines_values[index] = None

        for i,ch_idx in enumerate(channels):
            index = self.MW.Ephys.ephys_data.all_channels.index(ch_idx)

            # offset each channel with space for deselected channels or not (depending on user input)
            if show_all:
                offset = (len(self.MW.Ephys.ephys_data.all_channels)-1-index) * self.slot_height
            else:
                offset = (len(channels)-1-i) * self.slot_height

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
            self.lines_values[index] = (signal_times, ch_norm, offset)
            i+=1

        # y-axis ticks in the center of each channel slot
        if show_all:
            yticks = [((len(self.MW.Ephys.ephys_data.all_channels)-1-index) * self.slot_height, str(ch)) for index, ch in enumerate(self.MW.Ephys.ephys_data.all_channels)]
        else:
            yticks = [((len(channels)-1-index) * self.slot_height, str(ch)) for index, ch in enumerate(channels)]
            self.yMax = len(self.displayed_channels) * self.slot_height

        self.plot.getAxis('left').setTicks([yticks])
        self.plot.setLimits(yMin=self.yMin, yMax=self.yMax,xMin=self.xMin,xMax=self.xMax)
        self.plot.setXRange(self.xMin,self.xMax)
        self.plot.setYRange(self.yMin,self.yMax)

        return self.displayed_channels,self.lines


    def find_closest_line(self, x_click, y_click):
        closest_line = None
        min_distance = float('inf')

        for i, val in self.lines_values.items():
            if val is None:
                continue
            x, y1,y2 = val
            y = y1+y2
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

    def zoomReset(self):
        self.xMin = self.VisEphys.time_start
        self.xMax = self.VisEphys.time_end
        self.yMin = -self.slot_height
        self.yMax = len(self.MW.Ephys.ephys_data.all_channels) * self.slot_height

        self.plot.setLimits(yMin=self.yMin, yMax=self.yMax,xMin=self.xMin,xMax=self.xMax)
        self.plot.setXRange(self.xMin,self.xMax)
        self.plot.setYRange(self.yMin,self.yMax)


    def zoomOut(self):
        self.xMin = max(self.xMin-0.1,self.VisEphys.time_start)
        self.xMax = min(self.xMax+0.1,self.VisEphys.time_end)
        self.yMin = max(self.yMin-self.slot_height,-self.slot_height)
        self.yMax = min(self.yMax+self.slot_height, len(self.MW.Ephys.ephys_data.all_channels) * self.slot_height)

        self.plot.setLimits(yMin=self.yMin, yMax=self.yMax,xMin=self.xMin,xMax=self.xMax)
        self.plot.setXRange(self.xMin,self.xMax)
        self.plot.setYRange(self.yMin,self.yMax)
        #if hasattr(self.plot,"measurement_text"):
        #    self.plot.measurement_text.setPos(self.xMin, self.yMin)

