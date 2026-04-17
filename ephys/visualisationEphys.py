# This Python file uses the following encoding: utf-8

class VisualisationEphys:
    def __init__(self,MW,Vis3D,Ephys):
        self.MW = MW
        self.Vis3D = Vis3D
        self.Ephys = Ephys
        #self.Ephys.ephys_data.read_data = read_data
        self.total_ch_visible = 20
        duration = 1.5

        self.MW.ui.spinBox_startMin.setMaximum(int(self.Ephys.ephys_data.t_stop*60))
        self.MW.ui.spinBox_duration.setMaximum(int((self.Ephys.ephys_data.t_stop-self.Ephys.ephys_data.t_start)*1000))

        self.time_start = int(self.Ephys.ephys_data.t_stop/2)
        self.time_end = self.time_start + duration

        time_start_min = int(self.time_start/60)
        time_start_sec = int(self.time_start - time_start_min*60)
        time_start_ms = int((self.time_start - time_start_min*60-time_start_sec)*1000)
        self.MW.ui.spinBox_startMin.setValue(time_start_min) #min
        self.MW.ui.spinBox_startS.setValue(time_start_sec) #sec
        self.MW.ui.spinBox_startMs.setValue(time_start_ms) #ms
        self.MW.ui.spinBox_startMs.setMaximum(int((float(self.Ephys.ephys_data.t_stop.magnitude-self.Ephys.ephys_data.t_start.magnitude))*1000))
        self.MW.ui.spinBox_startS.setMaximum(int((float(self.Ephys.ephys_data.t_stop.magnitude-self.Ephys.ephys_data.t_start.magnitude))*1000))

        self.MW.ui.spinBox_duration.setValue(duration*1000)
        self.MW.ui.horizontalSlider_ephys.setMaximum(int((float(self.Ephys.ephys_data.t_stop.magnitude-self.Ephys.ephys_data.t_start.magnitude)-duration)*1000))
        self.MW.ui.horizontalSlider_ephys.setValue(self.time_start*1000) #sec

        self.MW.ui.spinBox_startMin.editingFinished.connect(self.change_start_end_time)
        self.MW.ui.spinBox_startS.editingFinished.connect(self.change_start_end_time)
        self.MW.ui.spinBox_startMs.editingFinished.connect(self.change_start_end_time)
        self.MW.ui.spinBox_duration.editingFinished.connect(self.change_start_end_time)
        self.MW.ui.horizontalSlider_ephys.valueChanged.connect(self.change_start_end_time_slider)

        self.MW.ui.pushButton_zoomOut.clicked.connect(self.MW.ui.widget_pgEphys.zoomOut)
        self.MW.ui.pushButton_zoomReset.clicked.connect(self.MW.ui.widget_pgEphys.zoomReset)
        self.MW.ui.pushButton_measurement.clicked.connect(self.MW.ui.widget_pgEphys.plot.activate_measurement)
        self.MW.ui.pushButton_selectTime.clicked.connect(self.MW.ui.widget_pgEphys.plot.select_timeframe)
        self.MW.ui.pushButton_timeline.clicked.connect(self.MW.ui.widget_pgEphys.plot.draw_timeline)

        # create and electrode table
        self.Vis3D.table_excel = self.MW.ui.tableWidget_ephys
        self.Vis3D.fill_table(self.Ephys.ephys_data.all_channels,self.Ephys.ephys_data.dead_channels)
        self.Vis3D.table_excel.cellClicked.connect(self.Vis3D.on_table_click)


    def visualize_data(self,channels):
        if self.time_start==self.time_end or channels==[]:
            if channels==[]:
                self.MW.ui.widget_pgEphys.plot.clear()
                self.displayed_channels = channels
                for index,_ in enumerate(self.Ephys.ephys_data.all_channels):
                    self.ephys_lines[index] = None
            return
        signal = self.Ephys.ephys_data.read_data.analogsignals[0].load(time_slice=(self.time_start,self.time_end),channel_indexes=channels)
        self.MW.ui.widget_pgEphys.xMin = self.time_start
        self.MW.ui.widget_pgEphys.xMax = self.time_end
        self.displayed_channels,self.ephys_lines = self.MW.ui.widget_pgEphys.plot_ephys(signal.times, signal.magnitude, channels)

        # highlight channel, even after time scrolling
        if self.Vis3D.table_excel.currentRow()!=-1:
            self.highlight_channel(ch_idx=self.Vis3D.table_excel.currentRow())


    def change_start_end_time(self):
        self.time_start = min(self.MW.ui.spinBox_startMin.value()*60 + self.MW.ui.spinBox_startS.value() + self.MW.ui.spinBox_startMs.value()/1000,self.Ephys.ephys_data.t_stop.magnitude-self.MW.ui.spinBox_duration.value()/1000)

        self.time_end = self.time_start + self.MW.ui.spinBox_duration.value()/1000

        self.MW.ui.horizontalSlider_ephys.blockSignals(True)
        self.MW.ui.spinBox_startMin.blockSignals(True)
        self.MW.ui.spinBox_startS.blockSignals(True)
        self.MW.ui.spinBox_startMs.blockSignals(True)
        self.MW.ui.horizontalSlider_ephys.setMaximum(int((self.Ephys.ephys_data.t_stop.magnitude-self.Ephys.ephys_data.t_start.magnitude-self.MW.ui.spinBox_duration.value()/1000)*1000))
        self.MW.ui.horizontalSlider_ephys.setValue(self.time_start*1000) #ms
        time_start_min = int(self.time_start/60)
        time_start_sec = int(self.time_start - time_start_min*60)
        time_start_ms = int((self.time_start - time_start_min*60-time_start_sec)*1000)
        self.MW.ui.spinBox_startMin.setValue(time_start_min) #min
        self.MW.ui.spinBox_startS.setValue(time_start_sec) #sec
        self.MW.ui.spinBox_startMs.setValue(time_start_ms) #ms
        self.MW.ui.horizontalSlider_ephys.blockSignals(False)
        self.MW.ui.spinBox_startMin.blockSignals(False)
        self.MW.ui.spinBox_startS.blockSignals(False)
        self.MW.ui.spinBox_startMs.blockSignals(False)

        self.visualize_data(self.displayed_channels)

    def change_start_end_time_slider(self,val):
        self.MW.ui.spinBox_startMin.blockSignals(True)
        self.MW.ui.spinBox_startS.blockSignals(True)
        self.MW.ui.spinBox_startMs.blockSignals(True)
        time_start_min = int(self.MW.ui.horizontalSlider_ephys.value()/1000/60)
        time_start_sec = int(self.MW.ui.horizontalSlider_ephys.value()/1000 - time_start_min*60)
        time_start_ms = int((self.MW.ui.horizontalSlider_ephys.value()/1000- time_start_min*60-time_start_sec)*1000)
        self.MW.ui.spinBox_startMin.setValue(time_start_min) #min
        self.MW.ui.spinBox_startS.setValue(time_start_sec) #sec
        self.MW.ui.spinBox_startMs.setValue(time_start_ms) #ms
        self.MW.ui.spinBox_startMin.blockSignals(False)
        self.MW.ui.spinBox_startS.blockSignals(False)
        self.MW.ui.spinBox_startMs.blockSignals(False)

        self.time_start = self.MW.ui.spinBox_startMin.value()*60 + self.MW.ui.spinBox_startS.value() + self.MW.ui.spinBox_startMs.value()/1000
        self.time_end = self.time_start + self.MW.ui.spinBox_duration.value()/1000
        self.visualize_data(self.displayed_channels)

    def highlight_channel(self,ch_idx):
        if self.ephys_lines[ch_idx] is None:
            return
        pen_current = self.ephys_lines[ch_idx].opts['pen']

        if pen_current.width() == 3:
            return  # already highlighted

        # reset all lines to default
        for idx, line in self.ephys_lines.items():
            if line is None:
                continue
            current_pen = line.opts['pen']
            current_pen.setWidth(0.5)
            line.setPen(current_pen)

        # highlight clicked line
        current_pen = self.ephys_lines[ch_idx].opts['pen']
        current_pen.setWidth(3)
        self.ephys_lines[ch_idx].setPen(current_pen)

        self.Vis3D.table_excel.selectRow(ch_idx)

        self.ch_highlight = ch_idx



