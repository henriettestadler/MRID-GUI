# This Python file uses the following encoding: utf-8
from PySide6 import QtWidgets
from userdialog import Ui_Dialog
from PySide6.QtWidgets import QFileDialog
import SimpleITK as sITK
import os

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


    def open_file(self):
        """
        Open a file dialog for selecting a NIfTI file.
        Loads the file into the MainWindow's LoadMRI instance, validates
        dimensionality (3D or 4D), and updates the UI accordingly.
        """
        self.MW.LoadMRI.file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            "",
            "NIfTI files (*.nii.gz)"
        )

        #user cancelled
        if not self.MW.LoadMRI.file_name:
            return

        # Load volume
        self.MW.LoadMRI.image = sITK.ReadImage(self.MW.LoadMRI.file_name)
        self.MW.LoadMRI.volume[0] = sITK.GetArrayFromImage(self.MW.LoadMRI.image)
        self.MW.LoadMRI.spacing = self.MW.LoadMRI.image.GetSpacing()[::-1]
        filename = os.path.basename(self.MW.LoadMRI.file_name)

        if self.MW.LoadMRI.volume[0].ndim == 3:
            self.plainTextEdit_file.setPlainText(f"3D File selected with name \n{filename}")
            self.plainTextEdit_file.setReadOnly(True)
            self.plainTextEdit_file.setStyleSheet("color: green; font-size: 8pt;")
            self.tab_index = 0
            self.enable_OK()
        elif self.MW.LoadMRI.volume[0].ndim == 4:
            self.plainTextEdit_file.setPlainText(f"4D File selected with name \n{filename}")
            self.plainTextEdit_file.setReadOnly(True)
            self.plainTextEdit_file.setStyleSheet("color: green; font-size: 8pt;")
            self.tab_index = 1
            self.infotext_4D.setStyleSheet("color: red; font-size: 8pt;")
        else:
            self.plainTextEdit_file.setPlainText('You selected a volume which is not 3D nor 4D! Please select another file')
            self.plainTextEdit_file.setReadOnly(True)
            self.plainTextEdit_file.setStyleSheet("color: red; font-size: 8pt;")
            return

        self.MW.LoadMRI.vol_dim = self.MW.LoadMRI.volume[0].ndim

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


