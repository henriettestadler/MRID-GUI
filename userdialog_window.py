# This Python file uses the following encoding: utf-8
# pyside6-uic userdialog.ui -o ui_userdialog.py

from PySide6 import QtWidgets
from userdialog import Ui_Dialog
from PySide6.QtWidgets import QFileDialog
import SimpleITK as sITK
import os
import sys
import numpy as np
from core.load_other_file import LoadOtherFile

class UserDialog_Window(QtWidgets.QDialog, Ui_Dialog):
    """
    Dialog window for user to select a NIfTI MRI file (3D or 4D).

    Handles file loading, validation of volume dimensions, and updating
    the MainWindow with the selected MRI file.
    """

    def __init__(self,main_window):
        """Initialize the dialog and connect UI signals."""
        super().__init__()
        self.setupUi(self)
        self.MW = main_window

        #Connect load button
        self.toolButton_LoadFile.clicked.connect(self.open_file)
        self.checkBox_4Dto3D.clicked.connect(self.open_4Das3D)

        self.MW.LoadMRI.data_index = 0
        self.MW.LoadMRI.num_data_max = 1
        self.MW.LoadMRI.file_name = {}
        self.MW.LoadMRI.image = {}
        self.MW.LoadMRI.spacing = {}
        self.MW.LoadMRI.vol_dim = {}


    def open_file(self):
        """
        Open a file dialog for selecting a NIfTI file.
        Loads the file into the MainWindow's LoadMRI instance, validates
        dimensionality (3D or 4D), and updates the UI accordingly.
        """
        self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index], _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            "",
            "NIfTI files (*.nii.gz)"
        )

        #user cancelled
        if not self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index]:
            return

        # Load volume
        self.MW.LoadMRI.image[self.MW.LoadMRI.data_index] = sITK.ReadImage(self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index])
        self.MW.LoadMRI.ref_image = sITK.ReadImage(self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index])

        img = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index]
        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index] = {}
        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0] = sITK.GetArrayFromImage(img)
        self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index] = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index].GetSpacing()[::-1]
        filename = os.path.basename(self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index])

        if self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim == 3:
            self.plainTextEdit_file.setPlainText(f"3D File selected with name \n{filename}")
            self.plainTextEdit_file.setReadOnly(True)
            self.plainTextEdit_file.setStyleSheet("color: green; font-size: 8pt;")
            self.tab_index = 0
            ## FLIPPED
            img_dir = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index].GetDirection()
            img_dir = np.array(img_dir).reshape(3,3)
            self.img_dir_max = [max(col, key=abs) for col in zip(*img_dir)]
            # check signs along axes
            self.MW.LoadMRI.axes_to_flip = []
            for i in range(3): #Code is built on z being negative
                if (self.img_dir_max[i] < 0 and i!=2) or (self.img_dir_max[i] > 0 and i==2):
                    self.MW.LoadMRI.axes_to_flip.append(True)
                else:
                    self.MW.LoadMRI.axes_to_flip.append(False)

            img_flipped = sITK.Flip(self.MW.LoadMRI.image[self.MW.LoadMRI.data_index], self.MW.LoadMRI.axes_to_flip, flipAboutOrigin=False)
            vol = sITK.GetArrayFromImage(img_flipped)
            self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0] = vol

            self.enable_OK()
        elif self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim == 4:
            self.plainTextEdit_file.setPlainText(f"4D File selected with name \n{filename}")
            self.plainTextEdit_file.setReadOnly(True)
            self.plainTextEdit_file.setStyleSheet("color: green; font-size: 8pt;")
            self.infotext_4D.setStyleSheet("color: red; font-size: 8pt;")
            self.tab_index = 1
        else:
            self.plainTextEdit_file.setPlainText('You selected a volume which is not 3D nor 4D! Please select another file')
            self.plainTextEdit_file.setReadOnly(True)
            self.plainTextEdit_file.setStyleSheet("color: red; font-size: 8pt;")
            return

        self.MW.LoadMRI.vol_dim[self.MW.LoadMRI.data_index] = self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim

        self.tabWidget.setEnabled(True)
        self.tabWidget.setCurrentIndex(self.tab_index)
        self.MW.ui.tabWidget.setCurrentIndex(self.tab_index)

        #comboBox_view
        self.comboBox_view.currentIndexChanged.connect(self.enable_OK)


    def enable_OK(self):
        """
        Enable the OK button and update the MainWindow's displayed view.
        """
        self.MW.ui.text_displayed_view.setPlainText(f"{self.comboBox_view.currentText()}")
        self.plainTextEdit_file.setReadOnly(True)
        self.plainTextEdit_file.setStyleSheet("color: black; font-size: 8pt;")
        self.buttonBox_OK.setEnabled(True)

    def open_4Das3D(self):
        """
        Convert a loaded 4D volume to a 3D volume using the first time frame (timestamp 0).
        Applies axis flipping based on orientation metadata.
        """

        img_dir = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index].GetDirection()
        img_dir = np.array(img_dir).reshape(4,4)
        self.img_dir_max = [max(col, key=abs) for col in zip(*img_dir)]

        # check signs along axes
        self.MW.LoadMRI.axes_to_flip = []
        for i in range(3):
            if (self.img_dir_max[i] < 0 and i!=2) or (self.img_dir_max[i] > 0 and i==2):
                self.MW.LoadMRI.axes_to_flip.append(True)
            else:
                self.MW.LoadMRI.axes_to_flip.append(False)

        timestamp = 0
        img_flipped = sITK.Flip(self.MW.LoadMRI.image[self.MW.LoadMRI.data_index][:, :, :,timestamp] , self.MW.LoadMRI.axes_to_flip, flipAboutOrigin=False)
        vol4D = sITK.GetArrayFromImage(img_flipped)

        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index] = {}
        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0] = vol4D #echo 0
        self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index] = [self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index][1],self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index][2],self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index][3]]
        self.MW.LoadMRI.vol_dim[self.MW.LoadMRI.data_index] = self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim
        self.tabWidget.setEnabled(True)
        self.tabWidget.setCurrentIndex(self.tab_index)
        self.MW.ui.tabWidget.setCurrentIndex(0)

        self.enable_OK()



    def open_new_file(self):
        dlg = UserDialog_Files(self.MW)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            print('')



class UserDialog_Files(QtWidgets.QDialog):
    """
        Dialog to manage changing current main MRI image and adding additional images to the session.
    """
    def __init__(self, MW, parent=None):
        """Initialize the input dialog UI and connect signals."""
        super().__init__(parent)
        self.MW = MW
        self.setWindowTitle("Open new Main Image or Add Another Image")
        self.setModal(True)
        self.resize(400, 400)

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        text = QtWidgets.QPlainTextEdit("Open new Main Image or Add Another Image")
        text.setReadOnly(True)
        text.setFixedSize(400, 50)
        main_layout.addWidget(text)

        #main image
        main_image = QtWidgets.QGroupBox("Main Image")
        main_image_layout = QtWidgets.QVBoxLayout(main_image)
        # Horizontal layout for label + button
        h_layout = QtWidgets.QHBoxLayout()

        # Left: label
        self.main_file_text = QtWidgets.QPlainTextEdit(self.MW.LoadMRI.file_name[0])
        self.main_file_text.setReadOnly(True)  # make it non-editable
        self.main_file_text.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.main_file_text.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                QtWidgets.QSizePolicy.Policy.Preferred)
        h_layout.addWidget(self.main_file_text)


        # Right: push button with icon
        button = QtWidgets.QPushButton()
        style = QtWidgets.QApplication.style()
        icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton)
        button.setIcon(icon)
        button.setFixedSize(50, 50)
        h_layout.addWidget(button)

        # Align left label to the left and button to the right
        h_layout.setStretch(0, 1)
        h_layout.setStretch(1, 0)

        # Add horizontal layout to the group box
        main_image_layout.addLayout(h_layout)
        main_layout.addWidget(main_image)

        #button change_main_image
        button.clicked.connect(self.change_main_image)


        ## ANOTHER IMAGE
        #main image
        other_images = QtWidgets.QGroupBox("Other Images")
        main_image_layout = QtWidgets.QVBoxLayout(other_images)
        # Horizontal layout for label + button
        h_layout = QtWidgets.QHBoxLayout()

        # Left: label
        self.file_text = QtWidgets.QPlainTextEdit('file name of another image')
        self.file_text.setReadOnly(True)  # make it non-editable
        self.file_text.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.file_text.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                QtWidgets.QSizePolicy.Policy.Preferred)
        h_layout.addWidget(self.file_text)


        # Right: push button with icon
        button_anotherimage = QtWidgets.QPushButton()
        style = QtWidgets.QApplication.style()
        icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton)
        button_anotherimage.setIcon(icon)
        button_anotherimage.setFixedSize(50, 50)
        h_layout.addWidget(button_anotherimage)
        button_anotherimage.clicked.connect(self.add_another_image)

        # Align left label to the left and button to the right
        h_layout.setStretch(0, 1)
        h_layout.setStretch(1, 0)

        # Add horizontal layout to the group box
        main_image_layout.addLayout(h_layout)
        main_layout.addWidget(other_images)

        # OK / Cancel buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )

        # Connect buttons to dialog actions
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Add to main layout
        main_layout.addWidget(buttons)


    def change_main_image(self):
        """
           Replace the currently loaded main MRI image with a new file.
           Loads the file and Clears all renderers and actors from the previous dataset.
        """
        #reset main image
        self.MW.LoadMRI.data_index = 0
        self.MW.LoadMRI.file_name[0] = None
        self.MW.LoadMRI.image[0] = []
        self.MW.LoadMRI.spacing[0] = []
        self.MW.LoadMRI.vol_dim[0] = []

        self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index], _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            "",
            "NIfTI files (*.nii.gz)"
        )
        #user cancelled
        if not self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index]:
            return

        # Load volume
        self.MW.LoadMRI.image[self.MW.LoadMRI.data_index] = sITK.ReadImage(self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index])
        filename = os.path.basename(self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index])

        img = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index]
        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index] = {}
        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0] = sITK.GetArrayFromImage(img)
        self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index] = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index].GetSpacing()[::-1]

        self.MW.LoadMRI.is_first_slice = False
        if self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim == 3:
            self.main_file_text.setPlainText(f"3D File selected with name \n{filename}")
            self.main_file_text.setReadOnly(True)
            self.main_file_text.setStyleSheet("color: green; font-size: 8pt;")
            self.tab_index = 0
        elif self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim == 4:
            self.main_file_text.setPlainText(f"4D File selected with name \n{filename}")
            self.main_file_text.setReadOnly(True)
            self.main_file_text.setStyleSheet("color: green; font-size: 8pt;")
            self.tab_index = 1
        else:
            self.main_file_text.setPlainText('You selected a volume which is not 3D nor 4D! Please select another file')
            self.main_file_text.setReadOnly(True)
            self.main_file_text.setStyleSheet("color: red; font-size: 8pt;")
            return

        self.MW.LoadMRI.vol_dim[self.MW.LoadMRI.data_index] = self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim

        #delete measurement actors
        for view_name, line_actor,line_slice_index,text_actor in self.MW.LoadMRI.measurement_lines:
            renderer = self.MW.LoadMRI.measurement_renderer[view_name]
            renderer.RemoveActor(line_actor)
            text_actor.SetVisibility(0)
        self.MW.LoadMRI.measurement_lines = []

        for idx in self.MW.LoadMRI.minimap.minimap_renderers:
            for vn in self.MW.LoadMRI.minimap.minimap_renderers[idx]:
                self.MW.LoadMRI.minimap.minimap_renderers[idx][vn].RemoveAllViewProps()
            self.MW.LoadMRI.minimap.minimap_renderers[idx] = {}

        for idx in self.MW.LoadMRI.renderers:
            for vn in self.MW.LoadMRI.renderers[idx]:
                self.MW.LoadMRI.renderers[idx][vn].RemoveAllViewProps()
            self.MW.LoadMRI.renderers[idx] = {}
            self.MW.LoadMRI.actors[idx] = {}
            self.MW.LoadMRI.img_vtks[idx] = {}

        #remove old renderers
        for image_index,vtk_widget_image in self.MW.LoadMRI.vtk_widgets.items():
            for view_name, vtk_widget in vtk_widget_image.items():
                ren_win = vtk_widget.GetRenderWindow()
                ren_coll = ren_win.GetRenderers()

                renderers_to_remove = [ren_coll.GetItemAsObject(i) for i in range(ren_coll.GetNumberOfItems())]

                for old_renderer in renderers_to_remove:
                    ren_win.RemoveRenderer(old_renderer)


        z, y, x = self.MW.LoadMRI.slice_indices
        x = min(x,self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].shape[0]-1)
        y = min(y,self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].shape[1]-1)
        z = min(z,self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].shape[2]-1)
        self.MW.LoadMRI.slice_indices = [z,y,x]
        #load file again, update cursor
        self.MW.LoadMRI.is_first_slice = True
        self.MW.LoadMRI.load_file(self.MW.LoadMRI.vol_dim[self.MW.LoadMRI.data_index],True)
        self.MW.LoadMRI.cursor.init_widgets()



    def add_another_image(self):
        """
            Add an additional MRI file to the existing session.
            Loads another 3D/4D volume and updates intensity table in the main window.
        """
        self.MW.LoadMRI.data_index += 1
        self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index], _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            "",
            "NIfTI files (*.nii.gz)"
        )

        #user cancelled
        if not self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index]:
            return

        # Load volume
        self.MW.LoadMRI.image[self.MW.LoadMRI.data_index] = sITK.ReadImage(self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index])
        img = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index]
        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index] = {}
        self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0] = sITK.GetArrayFromImage(img)
        self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index] = self.MW.LoadMRI.image[self.MW.LoadMRI.data_index].GetSpacing()[::-1]
        filename = os.path.basename(self.MW.LoadMRI.file_name[self.MW.LoadMRI.data_index])

        if self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim == 3:
            vol_dim = 3
            self.file_text.setPlainText(f"3D File selected with name \n{filename}")
            self.file_text.setReadOnly(True)
            self.file_text.setStyleSheet("color: green; font-size: 8pt;")
            self.tab_index = 0
        elif self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim == 4 and self.MW.LoadMRI.num_images == 1:
            vol_dim = 4
            print(self.MW.LoadMRI.volume[0][0].ndim)
            self.file_text.setPlainText('You selected a volume which is not 4D! The first timestamp will be used to convert it into a 3D volume.')
            self.file_text.setReadOnly(True)
            self.file_text.setStyleSheet("color: red; font-size: 8pt;")

            #convert to 3d volume
            volume4D = self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].copy()
            self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index] = {}
            self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0] = volume4D[0, :, :, :] #echo 0
            self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index] = [self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index][1],
                    self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index][2],self.MW.LoadMRI.spacing[self.MW.LoadMRI.data_index][3]]
            #img3d.CopyInformation(img4d)
        elif self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim == 4:
            vol_dim = 4
            self.file_text.setPlainText(f"3D File selected with name \n{filename}")
            self.file_text.setReadOnly(True)
            self.file_text.setStyleSheet("color: green; font-size: 8pt;")
            self.tab_index = 0
            ## 4 images
            volume4D = self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].copy()
            self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index] = {}
            for i in 1,2: #,3:
                self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][i] = sITK.GetArrayFromImage(self.MW.LoadMRI.image[self.MW.LoadMRI.data_index])
            self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0] = volume4D[self.MW.LoadMRI.timestamp4D[0], :, :, :]
            self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][1] = volume4D[self.MW.LoadMRI.timestamp4D[1], :, :, :]
            self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][2] = volume4D[self.MW.LoadMRI.timestamp4D[2], :, :, :]
        else:
            self.file_text.setPlainText('You selected a volume which is not 3D! Please select another file')
            self.file_text.setReadOnly(True)
            self.file_text.setStyleSheet("color: red; font-size: 8pt;")
            return

        self.MW.LoadMRI.vol_dim[self.MW.LoadMRI.data_index] = self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0].ndim
        self.MW.LoadMRI.num_data_max += 1

        #load image
        self.MW.LoadMRI.loadOther = LoadOtherFile(self.MW.LoadMRI,self.MW.LoadMRI.data_index,vol_dim)

        #update table with filenames and intensities
        intensity = self.MW.LoadMRI.volume[self.MW.LoadMRI.data_index][0][self.MW.LoadMRI.slice_indices[0],self.MW.LoadMRI.slice_indices[1],self.MW.LoadMRI.slice_indices[2]]
        self.MW.LoadMRI.intensity[self.MW.LoadMRI.data_index] = intensity
        self.MW.intensity_table()






if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = UserDialog_Window()
    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        data = dlg.get_values()
