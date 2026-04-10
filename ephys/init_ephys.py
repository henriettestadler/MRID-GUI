# This Python file uses the following encoding: utf-8
from ephys.visualisation3D import Visualisation3D
import os
from PySide6 import QtWidgets
import pandas as pd
import pyvista as pv
import numpy as np
import SimpleITK as sITK
from neo.io import NeuroScopeIO
from ephys.visualisationEphys import VisualisationEphys
import xml.etree.ElementTree as ET
from ephys.change_anatRegion import Change_AnatRegion
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTableWidgetItem
import numpy
from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel
from PySide6.QtWidgets import QMessageBox, QFileDialog
from ephys.videoplayer import VideoPlayer

class InitEphys:
    def __init__(self, MW, filename):
        self.session_path = os.path.dirname(os.path.dirname(filename))
        self.MW = MW
        self.MW.ui.pushButton_anatRegion.clicked.connect(self.changeRegion)
        self.first_time = True
        self.filename = filename

        self.MW.ui.pushButton_changeTAG.clicked.connect(self.change_mridTAG)
        self.MW.ui.pushButton_AddVideo.clicked.connect(self.add_video)


    def get_mrid_tag(self,session_path):
        mrid_tags = [f.name for f in os.scandir(os.path.join(session_path,"analysed")) if f.is_dir()]

        self.coordinates = {}
        for mrid in mrid_tags:
            coordinates = numpy.load(os.path.join(session_path,"analysed",mrid,"gaussian_centers_3D.npy"))
            self.coordinates[mrid]=coordinates[0][0]
        #Atlas Coordinate System: RAS -> higher X = more Right
        self.coordinates = dict(sorted(self.coordinates.items(), key=lambda item: item[1], reverse=True))

        # get coordinates, set to 0 by default
        self.mrid_idx_xml = 0
        self.mrid = list(self.coordinates.keys())[self.mrid_idx_xml] #self.coordinates[0][0] #'trio' #A->0


    def change_mridTAG(self): #,filename,new_tag_index
        dialog = QDialog(self.MW)
        dialog.setWindowTitle("Select new MRID TAG")
        layout = QVBoxLayout()

        label = QLabel("Choose:")
        combo = QComboBox()
        combo_items = []
        for i, mrid in enumerate(self.coordinates):
            text = f"{mrid} (Channel Group: {i})"
            combo_items.append(text)

        combo.addItems(combo_items)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addWidget(QLabel("Please select in the Combobox the new Tag"))
        layout.addWidget(label)
        layout.addWidget(combo)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            selected = combo.currentIndex()


        self.mrid_idx_xml = selected
        self.mrid = list(self.coordinates.keys())[self.mrid_idx_xml] #self.coordinates[0][0] #'trio' #A->0

        ##something like this?
        print('NEUES TAG',flush=True)
        del self.Visualisation3D.chMap
        self.open_dat()


    ##TODO
    # read data and rhs file
    # read xml file for channel data
    # class neo.io.NeuroScopeIO(filename) - extensions = ['xml', 'dat', 'lfp', 'eeg']
    ## ask if file open okay

    def open_dat(self):
        all_channels,channels, skipped_ch = self.open_xml_file(self.filename)

        reader = NeuroScopeIO(self.filename)
        read_data = reader.read_segment(lazy=True)
        if self.first_time:
            self.get_mrid_tag(self.session_path)
            self.Visualisation3D = Visualisation3D(self.session_path,self.MW,self.mrid,chMap=all_channels[self.mrid_idx_xml])
            self.Visualisation3D.initialize_mridTag(self.mrid,chMap=all_channels[self.mrid_idx_xml])
            self.VisEphys = VisualisationEphys(self.MW,self.Visualisation3D,read_data,all_channels[self.mrid_idx_xml],skipped_ch[self.mrid_idx_xml])
        else:
            self.Visualisation3D.spinbox.blockSignals(True)
            self.Visualisation3D.initialize_mridTag(self.mrid,chMap=all_channels[self.mrid_idx_xml])
            self.Visualisation3D.spinbox.blockSignals(False)
            self.Visualisation3D.fill_table(all_channels[self.mrid_idx_xml],skipped_ch[self.mrid_idx_xml])

        self.VisEphys.all_channels = all_channels[self.mrid_idx_xml]
        self.MW.ui.widget_pgEphys.init_PgWidget_class(self.VisEphys,self.MW)

        self.VisEphys.visualize_data(channels[self.mrid_idx_xml])
        self.Visualisation3D.manually_pick_point(point=[],idx=all_channels[self.mrid_idx_xml].index(channels[self.mrid_idx_xml][0]))
        if self.first_time:
            self.Visualisation3D.spinbox.valueChanged.connect(self.Visualisation3D.channel_changed)
            self.first_time = False
        self.Visualisation3D.plotter.enable_parallel_projection()
        self.Visualisation3D.skipped_ch = skipped_ch[self.mrid_idx_xml]


    def open_xml_file(self,filename):
        self.xml_path = filename.replace('.dat', '.xml')
        tree = ET.parse(self.xml_path)
        root = tree.getroot()
        active_channels = {}
        skipped = {}
        all_channels= {}

        for group_idx, group in enumerate(root.findall('.//group')):
            active_channels[group_idx] = []
            skipped[group_idx] = []
            all_channels[group_idx] = []
            for ch in group.findall('channel'):
                ch_id = int(ch.text)
                skip  = int(ch.get('skip', 0))
                if skip == 0:
                    active_channels[group_idx].append(ch_id)
                else:
                    skipped[group_idx].append(ch_id)
                all_channels[group_idx].append(ch_id)
        return all_channels, active_channels, skipped

    def change_xml_file(self,channel_idx:int,skip):
        tree = ET.parse(self.xml_path)
        root = tree.getroot()

        for idx, group in enumerate(root.findall('.//group')):
            if idx == self.mrid_idx_xml:
                for ch in group.findall('channel'):
                    print('CH',int(ch.text),channel_idx,skip,flush=True)
                    if int(ch.text) == int(channel_idx):
                        ch.set('skip', str(skip))
                        break

        tree.write(self.xml_path, xml_declaration=True, encoding="utf-8")

        #os.path.join(filename[:-4] + '.xml')
        #print(reader.read_params,flush=True)
        #xml_file,flush=True)
        #xml -> mapp, tells you the order
        #- number of channels
        #- 16bits -> int16 (plus und minus Werte)
        #- Hz
        #- groups… (each has their own visualisation window); ich glaube pro tag 1group
        #- dead channels (if skip=1), aber option haben


    def add_video(self):
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open Video File",
            "",
            "Video files (*.avi)"
        )

        #User cancelled
        if not file_name:
            return

        #pop up asking for the view if 4D data used
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Open Main File")
        msg_box.setText(f"Do you want to open the file \n {file_name}?")
        msg_box.addButton("Yes", QMessageBox.ActionRole)
        btn_no = msg_box.addButton("No, other Video", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
        msg_box.exec()
        if msg_box.clickedButton()==btn_cancel:
            return
        if msg_box.clickedButton()==btn_no:
            self.add_video()

        ## initiate video class
        self.Video = VideoPlayer(self.MW,file_name)


    def changeRegion(self):
        dlg = Change_AnatRegion(self.MW)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.MW.ui.comboBox_anatRegion.setCurrentIndex(self.MW.ui.comboBox_anatRegion.findText(self.MW.ui.comboBox_ChangeanatRegion.currentText().split('(')[0].strip()))
            points_electrodes_path = os.path.join(os.path.join(self.session_path,"analysed"),self.mrid,'channel_atlas_coordinates.xlsx')
            self.points_data = pd.read_excel(points_electrodes_path,header=0)

            new_index = self.MW.ui.comboBox_anatRegion.currentIndex()
            new_label = self.Visualisation3D.atlaslabelsdf['LABEL'].values[new_index]
            new_idx = self.Visualisation3D.atlaslabelsdf['IDX'].values[new_index]

            channel_numb = self.Visualisation3D.chMap.index(self.MW.ui.spinBox_channelID.value())

            self.points_data.loc[channel_numb,'Channel Label'] = new_label
            self.points_data.loc[channel_numb,'Channel'] = new_idx
            #save back in excel
            df = pd.DataFrame(self.points_data)
            excel_path = os.path.join(os.path.join(self.session_path,"analysed"),self.mrid,'channel_atlas_coordinates.xlsx')
            df.to_excel(excel_path, index=False)

            #change atlas incase new label was added
            if self.check_newlabel(new_idx):
                self.Visualisation3D.delete_volumes(self.mrid,new_idx,channel_numb)

            #update table with new label and new color table
            max_idx = self.Visualisation3D.atlaslabelsdf['IDX'].max()
            rgba = self.Visualisation3D.cmap(new_idx / max_idx)
            r, g, b,a = rgba
            color = QColor(r*255, g*255, b*255)
            item = QTableWidgetItem(str(new_label))
            self.MW.ui.tableWidget_ephys.setItem(channel_numb, 2, item)
            item = self.MW.ui.tableWidget_ephys.item(channel_numb, 1)
            item.setForeground(QBrush(color))
            item = self.MW.ui.tableWidget_ephys.item(channel_numb, 2)
            item.setForeground(QBrush(color))
            item = self.MW.ui.tableWidget_ephys.item(channel_numb, 3)
            item.setForeground(QBrush(color))


            # update plot color
            line = self.VisEphys.ephys_lines[channel_numb]
            current_pen = line.opts['pen']
            current_pen.setColor(QColor(int(r*255), int(g*255), int(b*255), int(a*255)))
            #pen = pg.mkPen(color=(int(r*255), int(g*255), int(b*255),int(a*255)), width=0.5)
            line.setPen(current_pen)




    def check_newlabel(self,new_idx):
        filepath = os.path.join(self.session_path,"analysed",'atlas-regions.nii.gz')
        mesh = pv.read(filepath)
        old_labels = np.unique(mesh.point_data['NIFTI'])
        new_labels = np.unique(self.points_data.iloc[:, 1].values) #self.points_data.iloc[:, -3:].values
        old_idx = self.Visualisation3D.atlaslabelsdf['IDX'].values[self.old_index_anatregion]
        if (old_labels == new_idx).any() and (new_labels == old_idx).any():
            return False
        else:
            #new atlas with the new label
            atlas_image = sITK.ReadImage(os.path.join(os.path.dirname(os.path.dirname((__file__))), "Files",'Atlas','WHS_SD_rat_atlas_v4.nii.gz'))
            volume = sITK.GetArrayFromImage(atlas_image)
            volume[~np.isin(volume,new_labels)]=0
            label_image = sITK.GetImageFromArray(volume)
            label_image.CopyInformation(atlas_image)
            save_path = os.path.join(self.session_path,'analysed','atlas-regions.nii.gz')
            sITK.WriteImage(label_image, save_path)
            return True





