# This Python file uses the following encoding: utf-8
from ephys.visualisation3D import Visualisation3D
import os
from PySide6.QtWidgets import QMessageBox
from PySide6 import QtWidgets
import sys
from PySide6.QtWidgets import QHBoxLayout,QPushButton,QDialog
import pandas as pd
import pyvista as pv
import numpy as np
import SimpleITK as sITK
from neo.io import NeuroScopeIO
from ephys.visualisationEphys import VisualisationEphys
import xml.etree.ElementTree as ET
import nibabel as nib
from PySide6.QtGui import QBrush, QColor
from PySide6.QtCore import Qt

class InitEphys:
    def __init__(self, MW, filename):
        self.session_path = os.path.dirname(os.path.dirname(filename))
        self.MW = MW
        MW.ui.pushButton_anatRegion.clicked.connect(self.change_anatRegion)
        self.mrid = 'penta'

        self.Visualisation3D = Visualisation3D(self.session_path,self.MW,self.mrid)
        reader = NeuroScopeIO(filename)
        #print(xml_file.header() ,flush=True)
        read_data = reader.read_segment(lazy=True)
        self.VisEphys = VisualisationEphys(self.MW,self.Visualisation3D,read_data)

    ##TODO
    # read data and rhs file
    # read xml file for channel data
    # class neo.io.NeuroScopeIO(filename) - extensions = ['xml', 'dat', 'lfp', 'eeg']
    ## ask if file open okay

    def open_dat(self,filename):
        channels, skipped_ch = self.open_xml_file(filename)
        channels = np.arange(0,20)
        self.VisEphys.visualize_data(channels)

        self.Visualisation3D.manually_pick_point(point=[],idx=0)
        self.Visualisation3D.plotter.enable_parallel_projection()


    def open_xml_file(self,filename):
        xml_path = filename.replace('.dat', '.xml')
        tree = ET.parse(xml_path)
        root = tree.getroot()
        channels = {}
        skipped = {}

        for group_idx, group in enumerate(root.findall('.//group')):
            channels[group_idx] = []
            skipped[group_idx] = []
            for ch in group.findall('channel'):
                ch_id = int(ch.text)
                skip  = int(ch.get('skip', 0))
                if skip == 0:
                    channels[group_idx].append(ch_id)
                else:
                    skipped[group_idx].append(ch_id)

        return channels, skipped

        #os.path.join(filename[:-4] + '.xml')
        #print(reader.read_params,flush=True)
        #xml_file,flush=True)
        #xml -> mapp, tells you the order
        #- number of channels
        #- 16bits -> int16 (plus und minus Werte)
        #- Hz
        #- groups… (each has their own visualisation window); ich glaube pro tag 1group
        #- dead channels (if skip=1), aber option haben













    def change_anatRegion(self):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Change Anat Region")
        msg_box.setText("Are you sure to change the anat region of the selected channel")
        msg_box.addButton("Yes", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
        msg_box.exec()
        if msg_box.clickedButton()==btn_cancel:
            return
        dlg = CHANGE_AnatRegion(self.MW)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.MW.ui.comboBox_anatRegion.setCurrentIndex(self.MW.ui.comboBox_anatRegion.findText(self.MW.ui.comboBox_ChangeanatRegion.currentText()))
            points_electrodes_path = os.path.join(os.path.join(self.session_path,"analysed"),self.mrid,'channel_atlas_coordinates.xlsx')
            self.points_data = pd.read_excel(points_electrodes_path,header=0)
            #self.Visualisation3D
            new_index = self.MW.ui.comboBox_anatRegion.currentIndex()
            new_label = self.Visualisation3D.atlaslabelsdf['LABEL'].values[new_index]
            new_idx = self.Visualisation3D.atlaslabelsdf['IDX'].values[new_index]
            channel_numb = self.MW.ui.spinBox_channelID.value()
            self.points_data.loc[channel_numb,'Channel Label'] = new_label
            self.points_data.loc[channel_numb,'Channel'] = new_idx
            #save back in excel
            df = pd.DataFrame(self.points_data)
            excel_path = os.path.join(os.path.join(self.session_path,"analysed"),self.mrid,'channel_atlas_coordinates.xlsx')
            df.to_excel(excel_path, index=False)

            #change atlas incase new label was added
            if self.check_newlabel(new_idx):
                self.Visualisation3D.delete_volumes(self.mrid)


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




class CHANGE_AnatRegion(QDialog):
    def __init__(self, MW,parent=None):
        super().__init__(parent)
        self.MW = MW

        self.setWindowTitle("Change Anat Region")

        main_layout = QtWidgets.QVBoxLayout(self)

        text = QtWidgets.QLineEdit("Please select the correct anatomical region.")
        text.setReadOnly(True)

        main_layout.addWidget(text)
        self.group_box = self.MW.ui.groupBox_ChangeanatRegion
        self.original_parent = self.group_box.parent()
        main_layout.addWidget(self.group_box)
        self.MW.Ephys.old_index_anatregion = self.MW.ui.comboBox_anatRegion.currentIndex()
        #self.MW.ui.comboBox_ChangeanatRegion.setCurrentIndex(self.MW.ui.comboBox_anatRegion.currentIndex())
        self.MW.ui.spinBox_ChangechannelID.setValue(self.MW.ui.spinBox_channelID.value())

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        main_layout.addLayout(button_layout)

        self.fill_combobox()


    def done(self,result):
        """Return group_box to its original parent before dialog closes."""
        self.original_parent.layout().addWidget(self.group_box)  # restore to GUI to be reopened later
        super().done(result)


    def fill_combobox(self):
        ##please wait a moment until combobox is loaded
        self.MW.ui.comboBox_ChangeanatRegion.clear()

        x0 = self.MW.Ephys.Visualisation3D.coord_x.value()-1
        y0 = self.MW.Ephys.Visualisation3D.coord_y.value()-1
        z0 = self.MW.Ephys.Visualisation3D.coord_z.value()-1
        point_voxel = [x0,y0,z0]
        background_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"Files", 'Atlas', 'WHS_SD_rat_atlas_v4.nii.gz')
        img = nib.load(background_path)
        data = img.get_fdata()
        affine = img.affine
        labels = self.MW.Ephys.Visualisation3D.atlaslabelsdf['LABEL'].values #np.unique(data)
        labels = labels[labels != 0]

        voxel_sizes = np.sqrt((affine[:3, :3] ** 2).sum(axis=0))
        atlas_labels = np.unique(self.MW.Ephys.Visualisation3D.points_data.iloc[:, 1].values)

        ##limit to 5mm (sqrt(3²*3)=5.2mm)
        radius_mm = 3.0
        radius_vox = np.ceil(radius_mm / voxel_sizes).astype(int)
        x_min = max(point_voxel[0] - radius_vox[0], 0)
        x_max = min(point_voxel[0] + radius_vox[0] + 1, data.shape[0])
        y_min = max(point_voxel[1] - radius_vox[1], 0)
        y_max = min(point_voxel[1] + radius_vox[1] + 1, data.shape[1])
        z_min = max(point_voxel[2] - radius_vox[2], 0)
        z_max = min(point_voxel[2] + radius_vox[2] + 1, data.shape[2])
        # Sub-volume
        sub_data = data[x_min:x_max, y_min:y_max, z_min:z_max]
        mask = np.ones_like(sub_data, dtype=bool)
        coords = np.argwhere(mask) #sub_data>0
        coords += np.array([x_min, y_min, z_min])

        dists = np.linalg.norm((coords - point_voxel) * voxel_sizes, axis=1)
        labels_flat = data[coords[:, 0], coords[:, 1], coords[:, 2]]
        distances = {}
        for index,(label) in enumerate(np.unique(labels_flat)):
            distances[label] = dists[labels_flat == label].min()

        idx = 0
        for label, dist in sorted(distances.items(), key=lambda x: x[1]):
            index = self.MW.Ephys.Visualisation3D.atlaslabelsdf.index[self.MW.Ephys.Visualisation3D.atlaslabelsdf['IDX'] == label][0]
            label_name = self.MW.Ephys.Visualisation3D.atlaslabelsdf['LABEL'].values[index]
            text = str(f"{label_name} ({dist:.2f} mm)")
            if label in np.unique(self.MW.Ephys.Visualisation3D.points_data.iloc[:, 1].values):
                self.MW.ui.comboBox_ChangeanatRegion.insertItem(int(idx),str(text))
                self.MW.ui.comboBox_ChangeanatRegion.setItemData(idx, QBrush(QColor("red")), Qt.ForegroundRole) ##Change color
                idx += 1
            else:
                self.MW.ui.comboBox_ChangeanatRegion.addItem(text)
        #labels futher away than 5mm
        rest_of_labels = np.setdiff1d(self.MW.Ephys.Visualisation3D.atlaslabelsdf['IDX'].values,np.unique(labels_flat))

        self.MW.ui.comboBox_ChangeanatRegion.setCurrentIndex(0)
        for label in rest_of_labels:
            index = self.MW.Ephys.Visualisation3D.atlaslabelsdf.index[self.MW.Ephys.Visualisation3D.atlaslabelsdf['IDX'] == label][0]
            label_name = self.MW.Ephys.Visualisation3D.atlaslabelsdf['LABEL'].values[index]
            text = str(f"{label_name} (>5mm)")
            self.MW.ui.comboBox_ChangeanatRegion.addItem(text)



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = CHANGE_AnatRegion()
    #if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:

