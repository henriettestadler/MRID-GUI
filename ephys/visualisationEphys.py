# This Python file uses the following encoding: utf-8
import numpy as np
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtGui import QColor
class VisualisationEphys:
    def __init__(self,MW,Vis3D,read_data):
        self.MW = MW
        self.Vis3D = Vis3D
        self.read_data = read_data
        t_start = self.read_data.analogsignals[0].t_start
        t_stop = self.read_data.analogsignals[0].t_stop
        print(t_start,t_stop,flush=True)
        self.MW.ui.spinBox_startMin.setMaximum(int(t_stop*60))
        self.MW.ui.spinBox_duration.setMaximum(int((t_stop-t_start)*1000))

        self.time_start = int(t_stop/2)
        self.time_end = self.time_start + 5

        print(self.time_start,self.time_end,flush=True)

        time_start_min = int(self.time_start/60)
        time_start_sec = int(self.time_start - time_start_min*60)
        time_start_ms = int(self.time_start - time_start_min*60-time_start_sec)*1000
        self.MW.ui.spinBox_startMin.setValue(time_start_min)
        self.MW.ui.spinBox_startS.setValue(time_start_sec)
        self.MW.ui.spinBox_startMs.setValue(time_start_ms)
        self.MW.ui.spinBox_duration.setValue((self.time_end-self.time_start )*1000)
        self.MW.ui.spinBox_startMin.valueChanged.connect(self.change_start_end_time)
        self.MW.ui.spinBox_startS.valueChanged.connect(self.change_start_end_time)
        self.MW.ui.spinBox_startMs.valueChanged.connect(self.change_start_end_time)
        self.MW.ui.spinBox_duration.valueChanged.connect(self.change_start_end_time)

        # create and electrode table
        self.fill_table()



    def visualize_data(self,channels):
        signal = self.read_data.analogsignals[0].load(time_slice=(self.time_start,self.time_end),channel_indexes=channels)
        #signal.times.units is sec

        #n_channels = signal.shape[1]
        slot_height = 1.0  # each channel gets a fixed slot of this size
        self.MW.ui.widget_ephys.canvas.figure.clear()
        self.MW.ui.widget_ephys.ax = self.MW.ui.widget_ephys.canvas.figure.add_subplot(111)
        self.displayed_channels = []
        self.ephys_lines = {}

        for i, ch_idx in enumerate(channels):
            offset = ch_idx * slot_height

            # normalize each channel independently to [-0.5, 0.5] then offset
            ch = signal.magnitude[:, i]
            ch_range = ch.max() - ch.min()
            if ch_range > 0:
                ch_norm = (ch - ch.mean()) / ch_range  # centers and scales to ~[-0.5, 0.5]
            else:
                ch_norm = ch * 0

            line, = self.MW.ui.widget_ephys.ax.plot(
                signal.times,
                ch_norm + offset,
                linewidth=0.5,
                color='white'
            )
            self.displayed_channels.append(ch_idx)
            self.ephys_lines[ch_idx] = line

        # y ticks centered in each slot

        self.MW.ui.widget_ephys.ax.set_yticks([i * slot_height for i in channels])
        self.MW.ui.widget_ephys.ax.set_yticklabels([f"{i}" for i in channels])
        self.MW.ui.widget_ephys.ax.set_ylim(channels[0]-slot_height, channels[0]+len(channels) * slot_height)
        self.MW.ui.widget_ephys.ax.set_xlim(self.time_start,self.time_end)
        self.MW.ui.widget_ephys.ax.tick_params(colors='white')
        self.MW.ui.widget_ephys.ax.yaxis.label.set_color('white')
        for label in self.MW.ui.widget_ephys.ax.get_yticklabels():
            label.set_color('white')

        self.MW.ui.widget_ephys.canvas.figure.tight_layout()
        self.MW.ui.widget_ephys.canvas.figure.subplots_adjust(left=0.04, right=1, top=1, bottom=0)
        self.MW.ui.widget_ephys.ax.xaxis.set_visible(False)

        self.MW.ui.widget_ephys.ax.set_facecolor((0, 0, 0))
        self.MW.ui.widget_ephys.canvas.figure.patch.set_facecolor((0, 0, 0))
        self.MW.ui.widget_ephys.canvas.setStyleSheet("background-color: black;")
        self.MW.ui.widget_ephys.canvas.draw()

        # connect click event
        self.slot_height = slot_height
        self.n_displayed = len(channels)

        self.MW.ui.widget_ephys.canvas.mpl_connect(
            'button_press_event', self.on_ephys_click
        )


    def on_ephys_click(self, event):
        if event.inaxes is None:
            return
        # reverse-calculate which channel was clicked
        ch_idx = int(event.ydata / self.slot_height + 0.5)
        #ch_idx = max(0, min(ch_idx, self.n_displayed - 1))  # clamp
        print('ch_idx',ch_idx,event.ydata,flush=True)

        self.Vis3D.manually_pick_point(point=[],idx=ch_idx)
        self.highlight_channel(ch_idx)


    def highlight_channel(self,ch_idx):
        if ch_idx not in self.ephys_lines:
            total_channels = 20
            half = int(total_channels/2)
            n_total = self.read_data.analogsignals[0].load(time_slice=(self.time_start,self.time_end)).shape[1]
            start = max(0, ch_idx - half)
            end = min(n_total, ch_idx + half + 1)
            # shift window if we hit a border
            if start == 0:
                end = min(n_total, total_channels)
            if end == n_total:
                start = max(0, n_total - total_channels)
            channels = np.arange(start, end)
            self.visualize_data(channels)

        if self.ephys_lines[ch_idx].get_color() == 'red':
            return

        # reset all lines then highlight clicked
        for i, line in self.ephys_lines.items():
            line.set_color('white')
            line.set_linewidth(0.5)

        self.ephys_lines[ch_idx].set_color('red')
        self.ephys_lines[ch_idx].set_linewidth(1.2)
        self.MW.ui.widget_ephys.canvas.draw()


    def change_start_end_time(self,val):
        self.time_start = self.MW.ui.spinBox_startMin.value()*60 + self.MW.ui.spinBox_startS.value() + self.MW.ui.spinBox_startMs.value()/1000
        self.time_end = self.time_start + self.MW.ui.spinBox_duration.value()/1000

        self.visualize_data(self.displayed_channels)


    def fill_table(self):
        df = self.Vis3D.points_data
        df['Coordinates'] = df[['Atlas x', 'Atlas y', 'Atlas z']].astype(str).apply(', '.join, axis=1)
        df_col = df['Channel']
        df = df.drop(columns=['Atlas x', 'Atlas y', 'Atlas z','Channel ID','Channel'])

        self.MW.ui.tableWidget_ephys.setRowCount(len(df))
        self.MW.ui.tableWidget_ephys.setColumnCount(len(df.columns))
        self.MW.ui.tableWidget_ephys.setHorizontalHeaderLabels(df.columns.tolist())

        # Fill
        for row_idx, row in df.iterrows():
            index = self.Vis3D.atlaslabelsdf[self.Vis3D.atlaslabelsdf['IDX'] == df_col[row_idx]].index[0]
            max_idx = self.Vis3D.atlaslabelsdf['IDX'].max()
            rgba = self.Vis3D.cmap(df_col[row_idx] / max_idx)
            r, g, b,a = rgba
            print(row_idx,rgba,flush=True)
            color = QColor(r*255, g*255, b*255)
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setForeground(color)
                self.MW.ui.tableWidget_ephys.setItem(row_idx, col_idx, item)
            #self.MW.ui.tableWidget_ephys.setVerticalHeaderItem(row_idx, QTableWidgetItem(str(row_idx)))




