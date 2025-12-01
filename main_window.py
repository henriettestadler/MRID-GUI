# This Python file uses the following encoding: utf-8
# Important: You need to run the following command to generate the ui_form.py file: pyside6-uic form.ui -o ui_form.py

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from ui_form import Ui_MainWindow
from core.load_MRI_file import LoadMRI
import os
from utils.zoom import zoom_notifier
from PySide6 import QtCore
from PySide6.QtWidgets import QMessageBox
from gui_utils.intensity_table import IntensityTable
import numpy as np
from gui_utils.buttons_gui3D import ButtonsGUI_3D
from gui_utils.buttons_gui4D import ButtonsGUI_4D
from PySide6.QtWidgets import QFileDialog
import SimpleITK as sITK
from file_handling.loadimage_into3D import LoadImage3D
from file_handling.loadimage_into4D import LoadImage4D
from core.cursor import Cursor
from PySide6 import QtWidgets

class MainWindow(QMainWindow):
    """
    Main application window for MRI visualization.
    """
    def __init__(self, parent=None):
        """
        Initialize the main window
        """
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.resize_bool=True

        self.add_actions()

    def add_actions(self):
        """
        Initializes action triggers, GUI layout and setup UI elements.
        """
        #hide tab bars
        self.ui.tabWidget.tabBar().setVisible(False)

        # Connect all buttons to open file
        self.ui.actionOpen.triggered.connect(self.open_user_dialog)
        self.ui.actionQuit.triggered.connect(self.quit)


        # Re-render if tab changed
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

        #only show one row of views and center the three visible widgets
        self.ui.groupBox_data2.setVisible(False)
        self.ui.groupBox_data1.setVisible(False)
        self.ui.heatmap_data0.setVisible(False)

        self.ui.groupbox_legend0.setVisible(False)
        self.ui.contrast_data.setItemEnabled(0, False)
        self.ui.contrast_data.setItemEnabled(1, False)
        self.ui.contrast_data.setItemEnabled(2, False)

        #resize to inital size
        self.resize(1600, 900)
        self.setMinimumSize(1500,800)
        self.on_gui_resize()


    def resizeEvent(self, event):
        """
        re-rendering of vtk widgets if GUI resizes
        """
        super().resizeEvent(event)
        # Call on_gui_resize to re-render the vtk widgets
        if self.resize_bool==True:
            self.on_gui_resize()

    def open_user_dialog(self):
        """
        Open the initial User Dialog when the application starts.
        """
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            "",
            "NIfTI files (*.nii.gz)"
        )

        #User cancelled
        if not file_name:
            return

        #pop up asking for the view if 4D data used
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Open Main File")
        msg_box.setText(f"Do you want to open the file \n {file_name}?")
        btn_yes = msg_box.addButton("Yes", QMessageBox.ActionRole)
        btn_no = msg_box.addButton("No, other File", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
        msg_box.exec()
        if msg_box.clickedButton()==btn_cancel:
            return
        elif msg_box.clickedButton()==btn_no:
            self.open_user_dialog()

        else:
            #pop up asking for the view if 4D data used
            image = sITK.ReadImage(file_name)
            volume = sITK.GetArrayFromImage(image)
            if volume.ndim==4:
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Data view")
                msg_box.setText("Please select the anatomical view of your 4D data")
                btn_axial = msg_box.addButton("Axial", QMessageBox.ActionRole)
                btn_coronal = msg_box.addButton("Coronal", QMessageBox.ActionRole)
                btn_sagittal = msg_box.addButton("Sagittal", QMessageBox.ActionRole)
                btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
                msg_box.exec()
                if msg_box.clickedButton()==btn_cancel:
                    return

            if hasattr(self, "LoadMRI"):
                if volume.ndim==4:
                    data_view = {btn_axial: "axial", btn_coronal: "coronal", btn_sagittal: "sagittal"}.get(msg_box.clickedButton())
                    self.restart_gui(file_name,data_view)
                else:
                    self.restart_gui(file_name)
                return

            # Create loader
            self.LoadMRI = LoadMRI()
            self.LoadMRI.file_name = {}
            self.LoadMRI.file_name[0]= file_name

            self.ui.comboBox_resamplefiles.addItem(os.path.basename(file_name)) #add to combobox for resampling
            if volume.ndim==4:
                data_view = {btn_axial: "axial", btn_coronal: "coronal", btn_sagittal: "sagittal"}.get(msg_box.clickedButton())
                self.ui.groupBox_data0.setTitle(f"View: {data_view.upper()}")
            else:
                data_view = "coronal" #3d has all view_names

            self.save_info_of_mainimage(data_view,0,file_name)
            zoom_notifier.factorChanged.connect(self.LoadMRI.minimap.create_small_rectangle)
        return

    def on_gui_resize(self):
        """
        Re-render VTK widgets when GUI size changes.
        """
        self.ui.vtkWidget_data_sagittal.GetRenderWindow().Render()
        self.ui.vtkWidget_data_coronal.GetRenderWindow().Render()
        self.ui.vtkWidget_data_axial.GetRenderWindow().Render()
        self.ui.vtkWidget_data00.GetRenderWindow().Render()
        self.ui.vtkWidget_data01.GetRenderWindow().Render()
        self.ui.vtkWidget_data02.GetRenderWindow().Render()
        self.ui.vtkWidget_data03.GetRenderWindow().Render()
        self.ui.vtkWidget_legend0.GetRenderWindow().Render()
        self.ui.vtkWidget_data10.GetRenderWindow().Render()
        self.ui.vtkWidget_data11.GetRenderWindow().Render()
        self.ui.vtkWidget_data12.GetRenderWindow().Render()
        self.ui.vtkWidget_data13.GetRenderWindow().Render()
        self.ui.vtkWidget_legend1.GetRenderWindow().Render()
        self.ui.vtkWidget_data10.GetRenderWindow().Render()
        self.ui.vtkWidget_data11.GetRenderWindow().Render()
        self.ui.vtkWidget_data12.GetRenderWindow().Render()
        self.ui.vtkWidget_data13.GetRenderWindow().Render()
        self.ui.vtkWidget_legend2.GetRenderWindow().Render()


    def save_info_of_mainimage(self,data_view,data_index,file_name):
        """
           Load MRI volume, handle axis orientation, determine dimensionality (3D/4D),
           initialize GUI components, buttons, and tools accordingly.
        """

        # Load volume
        image = sITK.ReadImage(file_name)
        self.LoadMRI.volume[data_index] = {}
        self.LoadMRI.volume[data_index][0] = sITK.GetArrayFromImage(image)

        if data_index==0:
            self.LoadMRI.vol_dim = self.LoadMRI.volume[data_index][0].ndim
            self.LoadMRI.spacing = {}
            self.LoadMRI.opacity = {}
        self.LoadMRI.opacity[data_index] = 100
        self.LoadMRI.spacing[data_index] = image.GetSpacing()[::-1]

        #TODO: test if img_flipped = sITK.DICOMOrient(image, 'LSA') is better!
        if self.LoadMRI.volume[data_index][0].ndim == 3:
            tab_idx = 1
            #flip image if axes not align
            img_dir = image.GetDirection()
            img_dir = np.array(img_dir).reshape(3,3)
            self.img_dir_max = [max(col, key=abs) for col in zip(*img_dir)]
            # check signs along axes
            self.LoadMRI.axes_to_flip = {}
            self.LoadMRI.axes_to_flip[0] = []
            for i in range(3): #Code is built on z being negative
                if (self.img_dir_max[i] < 0 and i!=2) or (self.img_dir_max[i] > 0 and i==2):
                    self.LoadMRI.axes_to_flip[0].append(True)
                else:
                    self.LoadMRI.axes_to_flip[0].append(False)
            self.LoadMRI.axes_to_flip[data_index][2]=False
            img_flipped = sITK.Flip(image, self.LoadMRI.axes_to_flip[0], flipAboutOrigin=False)
            vol = sITK.GetArrayFromImage(img_flipped)
            self.LoadMRI.volume[data_index][0] = vol
            self.LoadMRI.volume[data_index][1] = vol
            self.LoadMRI.volume[data_index][2] = vol
            self.LoadMRI.axes_to_flip[1]=self.LoadMRI.axes_to_flip[0]
            self.LoadMRI.axes_to_flip[2]=self.LoadMRI.axes_to_flip[0]
        else: #4D data
            tab_idx=0
            if data_index==0:
                self.LoadMRI.volume4D = {}
                for i in 1,2:
                    self.LoadMRI.volume[data_index][i] = sITK.GetArrayFromImage(image)
                    self.LoadMRI.renderers[i] = {}  # store vtkRenderer for each view
                    self.LoadMRI.actors[i] = {}
                    self.LoadMRI.img_vtks[i] = {}
                self.LoadMRI.axes_to_flip = {}

            img_dir = image.GetDirection()
            img_dir = np.array(img_dir).reshape(4,4)
            img_dir_max = [img_dir[:, i][np.argmax(np.abs(img_dir[:, i]))] for i in range(4)] #[max(col, key=abs) for col in zip(*img_dir)]

            # check signs along axes
            self.LoadMRI.axes_to_flip[data_index] = []
            for i in range(3):
                if img_dir_max[i] < 0: # and i!=2) or (img_dir_max[i] > 0 and i==2):
                    self.LoadMRI.axes_to_flip[data_index].append(True)
                else:
                    self.LoadMRI.axes_to_flip[data_index].append(False)
            self.LoadMRI.axes_to_flip[data_index][2]=False

            flipped_volumes = []
            for t in range(image.GetSize()[3]):
                img_flipped = sITK.Flip(image[:, :, :,t], self.LoadMRI.axes_to_flip[data_index], flipAboutOrigin=True)
                flipped_volumes.append(sITK.GetArrayFromImage(img_flipped))
            self.LoadMRI.volume4D[data_index] = np.stack(flipped_volumes)
            self.LoadMRI.volume[data_index][0] = self.LoadMRI.volume4D[data_index][self.LoadMRI.timestamp4D[0],:, :, :]
            self.LoadMRI.volume[data_index][1] = self.LoadMRI.volume4D[data_index][self.LoadMRI.timestamp4D[1],:, :, :]
            self.LoadMRI.volume[data_index][2] = self.LoadMRI.volume4D[data_index][self.LoadMRI.timestamp4D[2],:, :, :]
            self.LoadMRI.spacing[data_index] = [self.LoadMRI.spacing[data_index][1],self.LoadMRI.spacing[data_index][2],self.LoadMRI.spacing[data_index][3]]


        self.ui.tabWidget.setCurrentIndex(1)
        self.ui.data_4d_3d.setCurrentIndex(tab_idx)

        #Initiate GUI and connect buttons
        if data_index==0:
            self.LoadMRI.session_path = os.path.dirname(os.path.dirname(self.LoadMRI.file_name[data_index]))
            if self.LoadMRI.vol_dim==3:
                self.ButtonsGUI_3D = ButtonsGUI_3D(self,self.LoadMRI.vol_dim,data_index)
            else:
                self.ButtonsGUI_4D = ButtonsGUI_4D(self,self.LoadMRI.vol_dim,data_index,data_view)
        else:
            self.ButtonsGUI_4D.initialize_contrast(data_index,data_view)
            self.ButtonsGUI_4D.initialize_timestamps(data_index,data_view)

        # Load file
        self.LoadMRI.slice_indices[data_index] = [int(self.LoadMRI.volume[data_index][0].shape[0]/2),int(self.LoadMRI.volume[data_index][0].shape[1]/2),int(self.LoadMRI.volume[data_index][0].shape[2]/2)]
        self.LoadMRI.load_file(self.LoadMRI.vol_dim,data_view,data_index)

        #Set table for images and intensities
        if self.LoadMRI.vol_dim == 3:
            table = self.ui.tableintensity_data3d
            vol =  sITK.GetArrayFromImage(image[:, :, :])
            self.LoadMRI.intensity_table0 = IntensityTable(self,data_index,table,vol)
        else:
            table = getattr(self.ui, f"tableintensity_data{data_index}")
            vol = sITK.GetArrayFromImage(image[:, :, :, 0])
            setattr(self.LoadMRI, f"intensity_table{data_index}", IntensityTable(self,data_index,table,vol))
        if data_index==0: #start cursor interaction
            self.LoadMRI.cursor = Cursor(self.LoadMRI, self.LoadMRI.cursor_ui,data_index,data_view)

        self.LoadMRI.cursor.start_cursor(True,data_index,data_view)



    def add_another_file(self):
        """
        Triggered if another file is uploaded by the user, saves it as highest layer.
        """
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            "",
            "NIfTI files (*.nii *.nii.gz);;Text files (*.txt)"
        )

        #User cancelled
        if not file_name:
            return

        #pop up asking for the view if 4D data used
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Add another File")
        msg_box.setText(f"Do you want to add the file \n {file_name}?")
        btn_yes = msg_box.addButton("Yes", QMessageBox.ActionRole)
        btn_no = msg_box.addButton("No, other File", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
        msg_box.exec()
        if msg_box.clickedButton()==btn_cancel:
            return
        elif msg_box.clickedButton()==btn_no:
            self.add_another_file()
        else:
            if self.LoadMRI.vol_dim==3:
                self.LoadMRI.LoadImage3D = LoadImage3D(self, file_name)
                vol = self.LoadMRI.LoadImage3D.open_file(file_name)
                #add to intensity table
                self.LoadMRI.intensity_table0.update_table(os.path.basename(file_name), vol,0)
                #add to registration combobox
                self.ui.comboBox_movingimg.addItem(os.path.basename(file_name))
                self.LoadMRI.movingimg_filename.append(file_name)
                self.LoadMRI.combo_Regimgname = self.ui.comboBox_movingimg
            else:
                #pop up asking for the view if 4D data used
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Select the correct view")
                msg_box.setText(f"Please select the view you want to import the file in")
                btn_axial = msg_box.addButton("Axial", QMessageBox.ActionRole)
                btn_coronal = msg_box.addButton("Coronal", QMessageBox.ActionRole)
                btn_sagittal = msg_box.addButton("Sagittal", QMessageBox.ActionRole)
                btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
                msg_box.exec()
                if msg_box.clickedButton()==btn_cancel:
                    return
                data_view = {btn_axial: "axial", btn_coronal: "coronal", btn_sagittal: "sagittal"}.get(msg_box.clickedButton())
                if not hasattr(self.LoadMRI,"LoadImage4D"):
                    self.LoadMRI.LoadImage4D = LoadImage4D(self, file_name)
                vol = self.LoadMRI.LoadImage4D.open_file(file_name,data_view)
                if vol is not None:
                    #add to intensity table
                    keys = list(self.LoadMRI.vtk_widgets[0].keys())
                    idx = keys.index(data_view)
                    tabclass = getattr(self.LoadMRI, f"intensity_table{idx}")
                    tabclass.update_table(os.path.basename(file_name), vol,idx)


    def restart_gui(self, file_name, data_view=None):
        """
        Restart GUI if new main image is loaded.
        """
        # Disconnect any important signals
        zoom_notifier.factorChanged.disconnect(self.LoadMRI.minimap.create_small_rectangle)

        # Clear stored references
        self.LoadMRI = None

        #restart GUI
        from ui_form import Ui_MainWindow
        self.resize_bool=False
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Create loader
        self.resize_bool=True
        self.add_actions()
        self.LoadMRI = LoadMRI()
        self.LoadMRI.file_name = {}
        self.LoadMRI.file_name[0] = file_name
        image = sITK.ReadImage(file_name)
        volume = sITK.GetArrayFromImage(image)
        if volume.ndim==4:
            self.ui.groupBox_data0.setTitle(f"View: {data_view.upper()}")

        self.save_info_of_mainimage(data_view,0,file_name)
        zoom_notifier.factorChanged.connect(self.LoadMRI.minimap.create_small_rectangle)

        return



    def quit(self):
        QtWidgets.QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())

