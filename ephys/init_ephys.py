# This Python file uses the following encoding: utf-8
from ephys.visualisation3D import Visualisation3D
import os
from PySide6 import QtWidgets
import pandas as pd
import pyvista as pv
import numpy as np
import SimpleITK as sITK
from ephys.ephysrecording import EphysRecording
from ephys.mrid_info import MRIDInfo
from ephys.visualisationEphys import VisualisationEphys
import xml.etree.ElementTree as ET
from ephys.change_anatRegion import Change_AnatRegion
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTableWidgetItem
import numpy
from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel
from ephys.videoplayer import VideoPlayer

class InitEphys:
    def __init__(self, MW,filename):
        self.MW = MW
        self.MW.ui.pushButton_anatRegion.clicked.connect(self.changeRegion)
        self.first_time = True
        self.session_path = os.path.dirname(os.path.dirname(filename))

        self.MW.ui.pushButton_changeTAG.clicked.connect(self.change_mridTAG_combobox)
        self.Video = VideoPlayer(self.MW)
        self.MW.ui.pushButton_AddVideo.clicked.connect(self.Video.add_video)

    ##TODO
    #os.path.join(filename[:-4] + '.xml')
    #xml_file,flush=True)
    #xml -> mapp, tells you the order
    #- number of channels
    #- 16bits -> int16 (plus und minus Werte)
    #- Hz
    #- groups… (each has their own visualisation window); ich glaube pro tag 1group
    #- dead channels (if skip=1), aber option haben

    def open_dat(self,filename,group_idx=0):
        self.ephys_data = EphysRecording.from_file(filename)

        if self.first_time:
            self.ephys_data.all_channels =self.ephys_data.all_channels[0]
            self.ephys_data.dead_channels = self.ephys_data.dead_channels[0]
            self.ephys_data.active_channels =self.ephys_data.active_channels[0]
            self.mrid_info = MRIDInfo.from_file(filename,group_idx)
            self.Visualisation3D = Visualisation3D(self.session_path,self.MW,self.mrid_info.mrid,self.mrid_info.mrid_tags,chMap=self.ephys_data.all_channels)
            self.Visualisation3D.initialize_mridTag(self.mrid_info.mrid,chMap=self.ephys_data.all_channels)
            self.VisEphys = VisualisationEphys(self.MW,self.Visualisation3D,self.ephys_data.read_data,self.ephys_data.all_channels,self.ephys_data.dead_channels)
        else:
            self.ephys_data.all_channels =self.ephys_data.all_channels[self.mrid_info.mrid_idx_xml]
            self.ephys_data.dead_channels = self.ephys_data.dead_channels[self.mrid_info.mrid_idx_xml]
            self.ephys_data.active_channels =self.ephys_data.active_channels[self.mrid_info.mrid_idx_xml]
            self.Visualisation3D.index = self.mrid_info.mrid_idx_xml
            self.mrid_info.mrid = list(self.mrid_info.mrid_coordinates.keys())[self.mrid_info.mrid_idx_xml]
            self.Visualisation3D.spinbox.blockSignals(True)
            self.Visualisation3D.table_excel.blockSignals(True)
            self.Visualisation3D.initialize_mridTag(self.mrid_info.mrid,chMap=self.ephys_data.all_channels)
            self.Visualisation3D.spinbox.blockSignals(False)
            self.Visualisation3D.fill_table(self.ephys_data.all_channels,self.ephys_data.dead_channels)
            self.Visualisation3D.table_excel.blockSignals(False)

        print(self.mrid_info.mrid_idx_xml,flush=True)
        self.MW.ui.widget_pgEphys.init_PgWidget_class(self.VisEphys,self.MW)

        self.VisEphys.visualize_data(self.ephys_data.active_channels)
        self.Visualisation3D.manually_pick_point(point=[],idx=self.ephys_data.all_channels.index(self.ephys_data.active_channels[0]))
        if self.first_time:
            self.Visualisation3D.spinbox.valueChanged.connect(self.Visualisation3D.channel_changed)
            self.MW.ui.horizontalSlider_ElectrodeRegion.valueChanged.connect(self.Visualisation3D.change_opacityRegionOfInterest)
            self.MW.ui.horizontalSlider_OtherRegions.valueChanged.connect(self.Visualisation3D.change_opacityOtherRegions)
            self.MW.ui.horizontalSlider_Background.valueChanged.connect(self.Visualisation3D.change_opacityBackground)
            self.first_time = False

        self.Visualisation3D.plotter.enable_parallel_projection()

    def change_xml_file(self,channel_idx:int,skip):
        tree = ET.parse(self.ephys_data.xml_path)
        root = tree.getroot()

        for idx, group in enumerate(root.findall('.//group')):
            if idx == self.mrid_info.mrid_idx_xml:
                for ch in group.findall('channel'):
                    if int(ch.text) == int(channel_idx):
                        ch.set('skip', str(skip))
                        break

        tree.write(self.ephys_data.xml_path, xml_declaration=True, encoding="utf-8")

    def change_mridTAG_combobox(self): #,filename,new_tag_index
        dialog = QDialog(self.MW)
        dialog.setWindowTitle("Select new MRID TAG")
        layout = QVBoxLayout()

        label = QLabel("Choose:")
        combo = QComboBox()
        combo_items = []
        for i, mrid in enumerate(self.mrid_info.mrid_coordinates):
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
            self.change_mridTAG(combo.currentIndex())


    def change_mridTAG(self,new_index):
        self.mrid_info.mrid_idx_xml = new_index
        self.mrid_info.mrid = list(self.mrid_info.mrid_coordinates.keys())[self.mrid_info.mrid_idx_xml] #'trio' #A->0

        del self.Visualisation3D.chMap
        self.open_dat(self.ephys_data.file_path)



    def changeRegion(self):
        dlg = Change_AnatRegion(self.MW)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.MW.ui.comboBox_anatRegion.setCurrentIndex(self.MW.ui.comboBox_anatRegion.findText(self.MW.ui.comboBox_ChangeanatRegion.currentText().split('(')[0].strip()))
            points_electrodes_path = os.path.join(os.path.join(self.session_path,"analysed"),self.mrid_info.mrid,'channel_atlas_coordinates.xlsx')
            self.points_data = pd.read_excel(points_electrodes_path,header=0)

            new_index = self.MW.ui.comboBox_anatRegion.currentIndex()
            new_label = self.Visualisation3D.atlaslabelsdf['LABEL'].values[new_index]
            new_idx = self.Visualisation3D.atlaslabelsdf['IDX'].values[new_index]

            channel_numb = self.Visualisation3D.chMap.index(self.MW.ui.spinBox_channelID.value())

            self.points_data.loc[channel_numb,'Channel Label'] = new_label
            self.points_data.loc[channel_numb,'Channel'] = new_idx
            #save back in excel
            df = pd.DataFrame(self.points_data)
            excel_path = os.path.join(os.path.join(self.session_path,"analysed"),self.mrid_info.mrid,'channel_atlas_coordinates.xlsx')
            df.to_excel(excel_path, index=False)

            #change atlas incase new label was added
            if self.check_newlabel(new_idx):
                self.Visualisation3D.delete_volumes(self.mrid_info.mrid,new_idx,channel_numb)

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





