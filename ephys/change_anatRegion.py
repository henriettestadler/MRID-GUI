# This Python file uses the following encoding: utf-8
import nibabel as nib
from PySide6.QtGui import QBrush, QColor
from PySide6.QtCore import Qt
import sys
from PySide6.QtWidgets import QHBoxLayout,QPushButton,QDialog
from PySide6 import QtWidgets
import numpy as np
import os

class Change_AnatRegion(QDialog):
    def __init__(self, MW,parent=None):
        super().__init__(parent)
        self.MW = MW
        self.MW.ui.comboBox_ChangeanatRegion.currentIndexChanged.connect(self.update_combobox_color)

        self.setWindowTitle("Change Anat Region")

        main_layout = QtWidgets.QVBoxLayout(self)

        text = QtWidgets.QLineEdit("Please select the correct anatomical region.")
        text.setReadOnly(True)

        main_layout.addWidget(text)
        self.group_box = self.MW.ui.groupBox_ChangeanatRegion
        self.original_parent = self.group_box.parent()
        main_layout.addWidget(self.group_box)
        self.MW.Ephys.old_index_anatregion = self.MW.ui.comboBox_anatRegion.currentIndex()
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
        self.update_combobox_color(idx=0)


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

        ##limit to 4mm (sqrt(2.52²*3)=4.36mm)
        radius_mm = 2.52
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
                r, g, b,a = self.MW.Ephys.Visualisation3D.cmap(label / self.MW.Ephys.Visualisation3D.atlaslabelsdf['IDX'].max())
                self.MW.ui.comboBox_ChangeanatRegion.setItemData(idx, QBrush(QColor(r*255,g*255,b*255)), Qt.ForegroundRole)
                idx += 1
            else:
                self.MW.ui.comboBox_ChangeanatRegion.addItem(text)
        #labels futher away than 4.37mm
        rest_of_labels = np.setdiff1d(self.MW.Ephys.Visualisation3D.atlaslabelsdf['IDX'].values,np.unique(labels_flat))

        self.MW.ui.comboBox_ChangeanatRegion.setCurrentIndex(0)
        for label in rest_of_labels:
            index = self.MW.Ephys.Visualisation3D.atlaslabelsdf.index[self.MW.Ephys.Visualisation3D.atlaslabelsdf['IDX'] == label][0]
            label_name = self.MW.Ephys.Visualisation3D.atlaslabelsdf['LABEL'].values[index]
            text = str(f"{label_name} (>4.37mm)")
            self.MW.ui.comboBox_ChangeanatRegion.addItem(text)

    def update_combobox_color(self, idx):
        color = self.MW.ui.comboBox_ChangeanatRegion.itemData(idx, Qt.ForegroundRole)
        if color:
            self.MW.ui.comboBox_ChangeanatRegion.setStyleSheet(
                f"QComboBox {{ color: rgb({color.color().red()}, {color.color().green()}, {color.color().blue()}); }}"
            )
        else:
            self.MW.ui.comboBox_ChangeanatRegion.setStyleSheet("QComboBox { color: white; }")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = Change_AnatRegion()
    #if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
