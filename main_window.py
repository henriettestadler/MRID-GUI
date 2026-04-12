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
from gui_utils.buttons_gui3D import ButtonsGUI_3D
from gui_utils.buttons_gui4D import ButtonsGUI_4D
from PySide6.QtWidgets import QFileDialog, QDockWidget
import SimpleITK as sitk
from file_handling.loadimage_into3D import LoadImage3D
from file_handling.loadimage_into4D import LoadImage4D
from core.cursor import Cursor
from PySide6 import QtWidgets
from ephys.init_ephys import InitEphys
from PySide6.QtCore import Qt, QCoreApplication,QResource
import qdarkstyle
from utils.zoom import Zoom
from core.mri_volume import MRIVolume


class MainWindow(QMainWindow):
    """
    Main application window for MRI visualization.
    """
    def __init__(self, parent=None):
        """
        Initialize the main window
        """
        super().__init__(parent)
        self.resize_bool=True
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.add_actions()

    def add_actions(self):
        """
        Initializes action triggers, GUI layout and setup UI elements.
        """
        #hide tab bars
        self.ui.tabWidget.tabBar().setVisible(False)
        self.ui.tabWidget_visualisation.tabBar().setVisible(False)

        #only show one row of views and center the three visible widgets
        self.ui.groupBox_data2.setVisible(False)
        self.ui.groupBox_data1.setVisible(False)
        self.ui.heatmap_data0.setVisible(False)
        self.ui.groupBox_barcode.setVisible(False)
        self.ui.groupbox_legend0.setVisible(False)
        self.ui.contrast_data.setItemEnabled(0, True)
        self.ui.contrast_data.setCurrentIndex(0)
        self.ui.contrast_data.setItemEnabled(1, False)
        self.ui.contrast_data.setItemEnabled(2, False)
        self.ui.groupBox_progressGUI.setVisible(False)
        self.ui.dockWidget_ephys.setVisible(False)

        #resize to inital size
        self.resize(1600, 900)
        self.setMinimumSize(1500,800)
        self.on_gui_resize()

        # Connect all buttons to open file
        self.ui.actionOpen.triggered.connect(self.open_user_dialog)
        self.ui.actionOpen_ephys_Data.triggered.connect(self.open_ephys_data)
        self.ui.actionQuit.triggered.connect(self.quit)

        # Re-render if tab changed
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)


    def open_ephys_data(self):
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open ephys Data File",
            "",
            "Data files (*.dat)"
        )

        #User cancelled
        if not file_name:
            return

        #pop up asking for the view if 4D data used
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Open Main File")
        msg_box.setText(f"Do you want to open the file \n {file_name}?")
        msg_box.addButton("Yes", QMessageBox.ActionRole)
        btn_no = msg_box.addButton("No, other File", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
        msg_box.exec()
        if msg_box.clickedButton()==btn_cancel:
            return
        elif msg_box.clickedButton()==btn_no:
            self.open_ephys_data()

        self.ui.dockWidget_ephys.setVisible(True)
        self.ui.stackedWidget_video.setCurrentIndex(1)
        self.ui.textEdit_ephys.setText(f"File loaded: {file_name}")
        self.ui.tabWidget.setCurrentIndex(2)
        self.Ephys = InitEphys(self,file_name)
        self.Ephys.open_dat(file_name)

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
        msg_box.addButton("Yes", QMessageBox.ActionRole)
        btn_no = msg_box.addButton("No, other File", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
        msg_box.exec()
        if msg_box.clickedButton()==btn_cancel:
            return
        elif msg_box.clickedButton()==btn_no:
            self.open_user_dialog()

        else:
            #pop up asking for the view if 4D data used
            image = sitk.ReadImage(file_name)
            volume = sitk.GetArrayFromImage(image)
            if volume.ndim==4:
                if 'coronal' in file_name or 'Coronal' in file_name:
                    data_view = "coronal"
                elif 'sagittal' in file_name or 'Sagittal' in file_name:
                    data_view = "sagittal"
                elif 'axial' in file_name or 'Axial' in file_name:
                    data_view = "axial"
                else:
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle("Data view")
                    msg_box.setText(f"Could not automatically detect the data view. \n Please select the anatomical view of your 4D data called \n {file_name}")
                    btn_axial = msg_box.addButton("Axial", QMessageBox.ActionRole)
                    btn_coronal = msg_box.addButton("Coronal", QMessageBox.ActionRole)
                    btn_sagittal = msg_box.addButton("Sagittal", QMessageBox.ActionRole)
                    btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
                    msg_box.exec()
                    if msg_box.clickedButton()==btn_cancel:
                        return
                    data_view = {btn_axial: "axial", btn_coronal: "coronal", btn_sagittal: "sagittal"}.get(msg_box.clickedButton())

            if hasattr(self, "LoadMRI"):
                #def open_as_new_file(self,buttons_gui3d,MW):
                """
                    Replace the currently loaded MRI file with the new resampled one.
                    Clears old renderers, actors, and measurement lines from the GUI.
                """
                data_index = 0
                #new volume and spacing
                self.LoadMRI.volumes[data_index] = MRIVolume.from_file(file_name)

                self.LoadMRI.is_first_slice = False

                #delete measurement actors
                for view_name, line_actor,line_slice_index,text_actor,_,dashed_lines,points in self.LoadMRI.measurement_lines:
                    renderer = self.LoadMRI.measurement_renderer[view_name]
                    renderer.RemoveActor(line_actor)
                    text_actor.SetVisibility(0)
                    renderer.RemoveActor(dashed_lines[1])
                    renderer.RemoveActor(dashed_lines[3])
                    renderer.RemoveActor(points[2])
                self.LoadMRI.measurement_lines = []

                for idx in self.LoadMRI.minimap.minimap_renderers:
                    for vn in self.LoadMRI.minimap.minimap_renderers[idx]:
                        self.LoadMRI.minimap.minimap_renderers[idx][vn].RemoveAllViewProps()
                    self.LoadMRI.minimap.minimap_renderers[idx] = {}


                for idx in self.LoadMRI.renderers:
                    for vn in self.LoadMRI.renderers[idx]:
                        self.LoadMRI.renderers[idx][vn].RemoveAllViewProps()
                    self.LoadMRI.renderers[idx] = {}
                    self.LoadMRI.actors[idx] = {}
                    self.LoadMRI.img_vtks[idx] = {}

                for data_index in range(len(self.LoadMRI.vtk_widgets[0])):
                    if hasattr(self.LoadMRI, f"intensity_table{data_index}"):
                        intensity_class = self.LoadMRI.intensity_table[data_index]
                        intensity_class.table.viewport().removeEventFilter(self)
                        #intensity_class.table = None

                #remove old renderers
                for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                    for view_name, vtk_widget in vtk_widget_image.items():                        
                        ren_win = vtk_widget.GetRenderWindow()
                        ren_coll = ren_win.GetRenderers()

                        renderers_to_remove = [ren_coll.GetItemAsObject(i) for i in range(ren_coll.GetNumberOfItems())]

                        for old_renderer in renderers_to_remove:
                            ren_win.RemoveRenderer(old_renderer)

                #load file again, update cursor
                self.LoadMRI = LoadMRI()
                self.ui.comboBox_resamplefiles.addItem(os.path.basename(file_name)) #add to combobox for resampling
                if volume.ndim==4:
                    self.restart_gui(file_name,data_view)
                else:
                    data_view = "coronal" #for 3d data
                    self.restart_gui(file_name)
                return

            # Create loader
            self.LoadMRI = LoadMRI()

            self.ui.comboBox_resamplefiles.addItem(os.path.basename(file_name)) #add to combobox for resampling
            if volume.ndim==4:
                self.ui.groupBox_data0.setTitle(f"View: {data_view.upper()}")
            else:
                data_view = "coronal" #3d has all view_names

            self.save_info_of_mainimage(data_view,0,file_name)
            zoom_notifier.factorChanged.connect(self.LoadMRI.minimap.create_small_rectangle)
            if volume.ndim==3:
                Zoom.fit_to_window(self.LoadMRI.vtk_widgets[0]["coronal"], self.LoadMRI.vtk_widgets.values(), self.LoadMRI.scale_bar, self.LoadMRI.vtk_widgets,0,data_3d=True)
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
        #barcode sachen

        self.ui.vtkWidget_ephys.GetRenderWindow().Render()


        if hasattr(self, 'LoadMRI'):
            if hasattr(self.LoadMRI,'minimap') and not self.LoadMRI.volumes[0].is_4d:
                    img_vtk = self.LoadMRI.img_vtks[0]["axial"]
                    self.LoadMRI.minimap.add_minimap('axial',img_vtk,0,self.LoadMRI.vtk_widgets[0]["axial"],0,data_3d=True)
                    img_vtk = self.LoadMRI.img_vtks[0]["coronal"]
                    self.LoadMRI.minimap.add_minimap('coronal',img_vtk,0,self.LoadMRI.vtk_widgets[0]["coronal"],0,data_3d=True)
                    img_vtk = self.LoadMRI.img_vtks[0]["sagittal"]
                    self.LoadMRI.minimap.add_minimap('sagittal',img_vtk,0,self.LoadMRI.vtk_widgets[0]["sagittal"],0,data_3d=True)
            else:
                if hasattr(self.LoadMRI, 'vtk_widgets'):
                    for data_index in range(len(self.LoadMRI.vtk_widgets[0])):
                        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                            if "CORONAL" in self.ui.groupBox_data0.title():
                                view_name = "coronal"
                            elif "AXIAL" in self.ui.groupBox_data0.title():
                                view_name = "axial"
                            elif "SAGITTAL" in self.ui.groupBox_data0.title():
                                view_name = "sagittal"
                            if image_index in self.LoadMRI.img_vtks:
                                img_vtk = self.LoadMRI.img_vtks[image_index][view_name]
                                self.LoadMRI.minimap.add_minimap(view_name,img_vtk,image_index,vtk_widget_image[view_name],data_index)



    def save_info_of_mainimage(self,data_view,data_index,file_name):
        """
           Load MRI volume, handle axis orientation, determine dimensionality (3D/4D),
           initialize GUI components, buttons, and tools accordingly.
        """
        self.prepare_volume(data_index, file_name)
        self.init_gui(data_view, data_index)


    def prepare_volume(self, data_index, file_name):
        """Pure data preparation — no Qt, no VTK widgets."""
        self.LoadMRI.volumes[data_index] = MRIVolume.from_file(file_name)

        if data_index==0:
            self.LoadMRI.opacity = {}
        self.LoadMRI.opacity[data_index] = 100

        # Load file
        self.LoadMRI.slice_indices[data_index] = [
            int(self.LoadMRI.volumes[data_index].slices[0].shape[0]/2),
            int(self.LoadMRI.volumes[data_index].slices[0].shape[1]/2),
            int(self.LoadMRI.volumes[data_index].slices[0].shape[2]/2)
        ]

        if self.LoadMRI.volumes[data_index].is_4d and data_index==0:
            for i in 1,2:
                self.LoadMRI.renderers[i] = {}  # store vtkRenderer for each view
                self.LoadMRI.actors[i] = {}
                self.LoadMRI.img_vtks[i] = {}

    def init_gui(self, data_view, data_index):
        #TODO: test if img_flipped = sitk.DICOMOrient(image, 'LSA') is better!
        vol = self.LoadMRI.volumes[data_index]
        tab_idx = 0 if vol.is_4d else 1

        self.ui.tabWidget.setCurrentIndex(0)
        self.ui.data_4d_3d.setCurrentIndex(tab_idx)

        #Initiate GUI and connect buttons
        if data_index==0:
            self.LoadMRI.session_path = os.path.dirname(os.path.dirname(vol.file_path))
            if not vol.is_4d:
                self.ButtonsGUI_3D = ButtonsGUI_3D(self,data_index)
            else:
                self.ButtonsGUI_4D = ButtonsGUI_4D(self,data_index,data_view)
        else:
            self.ButtonsGUI_4D.initialize_contrast(data_index,data_view)
            self.ButtonsGUI_4D.initialize_timestamps(data_index,data_view)

        self.LoadMRI.load_file(data_view,data_index)

        #Set table for images and intensities
        if not vol.is_4d:
            self.LoadMRI.intensity_table[data_index] = IntensityTable(self,data_index,self.ui.tableintensity_data3d,vol.slices[0])
        else:
            table = getattr(self.ui, f"tableintensity_data{data_index}")
            self.LoadMRI.intensity_table[data_index] = IntensityTable(self,data_index,table,vol.slices[0])

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
        msg_box.addButton("Yes", QMessageBox.ActionRole)
        btn_no = msg_box.addButton("No, other File", QMessageBox.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
        msg_box.exec()
        if msg_box.clickedButton()==btn_cancel:
            return
        elif msg_box.clickedButton()==btn_no:
            self.add_another_file()
        else:
            if not self.LoadMRI.volumes[0].is_4d:
                self.LoadMRI.LoadImage3D = LoadImage3D(self, file_name)
                vol = self.LoadMRI.LoadImage3D.open_file(file_name)
                #add to intensity table
                self.LoadMRI.intensity_table[0].update_table(os.path.basename(file_name), vol,0)
                #add to registration combobox
                self.ui.comboBox_movingimg.addItem(os.path.basename(file_name))
                self.LoadMRI.movingimg_filename.append(file_name)
                self.LoadMRI.combo_Regimgname = self.ui.comboBox_movingimg
            else:
                #pop up asking for the view if 4D data used
                if 'coronal' in file_name:
                    data_view = "coronal"
                elif 'sagittal' in file_name:
                    data_view = "sagittal"
                elif 'axial' in file_name:
                    data_view = "axial"
                else:
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle("Data view")
                    msg_box.setText(f"Could not automatically detect the data view. \n Please select the anatomical view of your 4D data called \n {file_name}")
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
                    tabclass = self.LoadMRI.intensity_table[idx]
                    tabclass.update_table(os.path.basename(file_name), vol,idx)
                    self.ui.contrast_data.setItemEnabled(idx, False)


    def restart_gui(self, file_name, data_view='coronal'):
        """
        Restart GUI if new main image is loaded.
        """
        # Disconnect any important signals
        if hasattr(self.LoadMRI, "minimap"):
            zoom_notifier.factorChanged.disconnect(self.LoadMRI.minimap.create_small_rectangle)
        dock_name = "dock_paintbrush4d"
        dock = self.findChild(QDockWidget, dock_name)
        if dock:
            dock.close()
            dock.deleteLater()

        # Clear stored references
        self.LoadMRI = None

        #restart GUI
        from ui_form import Ui_MainWindow
        self.resize_bool=False
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.add_actions()
        self.show()
        QApplication.processEvents()

        # Create loader
        self.resize_bool=True
        self.LoadMRI = LoadMRI()
        image = sitk.ReadImage(file_name)
        volume = sitk.GetArrayFromImage(image)
        if volume.ndim==4:
            self.ui.groupBox_data0.setTitle(f"View: {data_view.upper()}")

        self.save_info_of_mainimage(data_view,0,file_name)

        zoom_notifier.factorChanged.connect(self.LoadMRI.minimap.create_small_rectangle)
        Zoom.fit_to_window(self.LoadMRI.vtk_widgets[0][data_view], self.LoadMRI.vtk_widgets.values(), self.LoadMRI.scale_bar, self.LoadMRI.vtk_widgets,0,data_3d=True)

        return


    def quit(self):
        QtWidgets.QApplication.quit()


if __name__ == "__main__":
    # Register the .qrc file dynamically

    script_dir = os.path.dirname(__file__)
    file_path = os.path.join(script_dir, "resources.rcc")
    print(file_path,flush=True)
    os.chdir(os.path.dirname(__file__))

    QResource.registerResource(file_path)
    #to mix vtk and QtQuick3D
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    #dark mode
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
    #app.setWindowIcon(QIcon("Icons/Internet/eye_closed.png"))  # PNG or SVG
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())

