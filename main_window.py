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
from ephys.init_ephys import InitEphys
from PySide6.QtCore import Qt, QCoreApplication,QUrl
from gui_utils.visualization3D import Visualization3D
import qdarkstyle
from utils.zoom import Zoom

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

        #resize to inital size
        self.resize(1600, 900)
        self.setMinimumSize(1500,800)
        self.on_gui_resize()

        # Connect all buttons to open file
        self.ui.actionOpen.triggered.connect(self.open_user_dialog)
        self.ui.actionOpen_ephys_Data.triggered.connect(self.ephys_data)
        self.ui.actionQuit.triggered.connect(self.quit)

        # Re-render if tab changed
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        #save_path = "C:/Users/shadowfax/Downloads/atlas_filtered.nii.gz"
        #self.visualization_3D(save_path)

    def visualization_3D(self,save_path):
        ## Quick3D Visualization
        #self.ui.stackedWidget_heatmap.setCurrentIndex(1)
        QApplication.processEvents()
        self.ui.quickWidget_3D.setVisible(True)

        #self.volume_provider = Visualization3D(save_path)
        #self.ui.quickWidget_3D.engine().rootContext().setContextProperty("Visualization3D", self.volume_provider)

        qml_path = os.path.abspath("gui_utils/volumer_viewer.qml")
        self.ui.quickWidget_3D.setSource(QUrl.fromLocalFile(qml_path))

        print('fertig bin ich')
        self.ui.quickWidget_3D.setStyleSheet("background-color: magenta;")
        self.ui.quickWidget_3D.show()
        self.ui.quickWidget_3D.raise_()
        print("quickWidget geometry:", self.ui.quickWidget_3D.geometry())
        print("quickWidget visible:", self.ui.quickWidget_3D.isVisible())
        print("quickWidget source:", self.ui.quickWidget_3D.source())
        print("quickWidget format:", self.ui.quickWidget_3D.format())
        print("text visible:", self.ui.plainTextEdit.isVisible())
        print("File exists:", os.path.exists(os.path.abspath(qml_path)))



    def ephys_data(self):
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open ephys Data File",
            "",
            "Data files (*.dat)"
        )

        #User cancelled
        if not file_name:
            return

        self.ui.tabWidget.setCurrentIndex(2)
        self.Ephys = InitEphys(self,file_name)

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
                msg_box.setText(f"Please select the anatomical view of your 4D data called \n {file_name}")
                btn_axial = msg_box.addButton("Axial", QMessageBox.ActionRole)
                btn_coronal = msg_box.addButton("Coronal", QMessageBox.ActionRole)
                btn_sagittal = msg_box.addButton("Sagittal", QMessageBox.ActionRole)
                btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
                msg_box.exec()
                if msg_box.clickedButton()==btn_cancel:
                    return

            if hasattr(self, "LoadMRI"):
                #def open_as_new_file(self,buttons_gui3d,MW):
                """
                    Replace the currently loaded MRI file with the new resampled one.
                    Clears old renderers, actors, and measurement lines from the GUI.
                """
                data_index = 0
                self.LoadMRI.file_name[data_index] = file_name
                img = sITK.ReadImage(file_name)
                #new volume and spacing
                self.LoadMRI.volume[data_index] = {}
                self.LoadMRI.volume[data_index][0] = sITK.GetArrayFromImage(img)
                self.LoadMRI.volume[data_index][1] = sITK.GetArrayFromImage(img)
                self.LoadMRI.volume[data_index][2] = sITK.GetArrayFromImage(img)
                self.LoadMRI.ref_image = img
                self.LoadMRI.spacing = {}
                self.LoadMRI.spacing[data_index] = []
                self.LoadMRI.spacing[data_index] = img.GetSpacing()[::-1]
                self.LoadMRI.vol_dim = self.LoadMRI.volume[data_index][0].ndim

                self.LoadMRI.is_first_slice = False

                #delete measurement actors
                for view_name, line_actor,line_slice_index,text_actor in self.LoadMRI.measurement_lines:
                    renderer = self.LoadMRI.measurement_renderer[view_name]
                    renderer.RemoveActor(line_actor)
                    text_actor.SetVisibility(0)
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
                self.LoadMRI.file_name = {}
                self.LoadMRI.file_name[0]= file_name
                self.ui.comboBox_resamplefiles.addItem(os.path.basename(file_name)) #add to combobox for resampling
                if volume.ndim==4:
                    data_view = {btn_axial: "axial", btn_coronal: "coronal", btn_sagittal: "sagittal"}.get(msg_box.clickedButton())
                    self.restart_gui(file_name,data_view)
                else:
                    data_view = "coronal" #for 3d data
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

        if hasattr(self, 'LoadMRI'):
            if hasattr(self.LoadMRI,'minimap'):
                if self.LoadMRI.vol_dim == 3:
                    print('')
                    img_vtk = self.LoadMRI.img_vtks[0]["axial"]
                    self.LoadMRI.minimap.add_minimap('axial',img_vtk,0,self.LoadMRI.vtk_widgets[0]["axial"],0)
                    img_vtk = self.LoadMRI.img_vtks[0]["coronal"]
                    self.LoadMRI.minimap.add_minimap('coronal',img_vtk,0,self.LoadMRI.vtk_widgets[0]["coronal"],0)
                    img_vtk = self.LoadMRI.img_vtks[0]["sagittal"]
                    self.LoadMRI.minimap.add_minimap('sagittal',img_vtk,0,self.LoadMRI.vtk_widgets[0]["sagittal"],0)
                else:
                    print('i')
                    #for image_index,vtk_widget_image in self.vtk_widgets.items():
                    #    if data_view=='axial':
                    #        self.setup_vtkdata(self.volume[data_index][image_index][z, :, :], vtk_widget_image["axial"], "axial",image_index,data_index)
                    #    elif data_view=='coronal':
                    #        self.setup_vtkdata(self.volume[data_index][image_index][z, :, :], vtk_widget_image["coronal"], "coronal",image_index,data_index)
                    #    elif data_view=='sagittal':
                    #        self.setup_vtkdata(self.volume[data_index][image_index][z, :, :].T, vtk_widget_image["sagittal"], "sagittal",image_index,data_index)
                    for data_index in range(len(self.LoadMRI.vtk_widgets[0])):
                        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                            print(self.ui.groupBox_data0.title())
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
                    #self.LoadMRI.volume[data_index][i] = sITK.GetArrayFromImage(image)
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
            if self.LoadMRI.volume4D[0].shape[0]>7:
                self.LoadMRI.timestamp4D = [0,4,7]
            else:
                self.LoadMRI.timestamp4D = [0,2,5]
            self.LoadMRI.volume[data_index][0] = self.LoadMRI.volume4D[data_index][self.LoadMRI.timestamp4D[0],:, :, :].copy()
            #self.LoadMRI.volume[data_index][image_index] = (self.LoadMRI.volume4D[data_index][t].copy())
            self.LoadMRI.volume[data_index][1] = self.LoadMRI.volume4D[data_index][self.LoadMRI.timestamp4D[1],:, :, :].copy()
            self.LoadMRI.volume[data_index][2] = self.LoadMRI.volume4D[data_index][self.LoadMRI.timestamp4D[2],:, :, :].copy()
            self.LoadMRI.spacing[data_index] = [self.LoadMRI.spacing[data_index][1],self.LoadMRI.spacing[data_index][2],self.LoadMRI.spacing[data_index][3]]

        self.ui.tabWidget.setCurrentIndex(0)
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
                msg_box.setText("Please select the view you want to import the file in")
                button_to_view =  {}
                for image_index, vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                    for view_name in vtk_widget_image.keys():
                        # Only create a button if we haven't already
                        if view_name not in button_to_view.values():
                            btn = msg_box.addButton(view_name.capitalize(), QMessageBox.ActionRole)
                            button_to_view[btn] = view_name
                btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
                msg_box.exec()
                if msg_box.clickedButton()==btn_cancel:
                    return
                data_view = button_to_view.get(msg_box.clickedButton())
                if not hasattr(self.LoadMRI,"LoadImage4D"):
                    self.LoadMRI.LoadImage4D = LoadImage4D(self, file_name)
                vol = self.LoadMRI.LoadImage4D.open_file(file_name,data_view)
                if vol is not None:
                    #add to intensity table
                    keys = list(self.LoadMRI.vtk_widgets[0].keys())
                    idx = keys.index(data_view)
                    tabclass = getattr(self.LoadMRI, f"intensity_table{idx}")
                    tabclass.update_table(os.path.basename(file_name), vol,idx)
                    self.ui.contrast_data.setItemEnabled(idx, False)


    def restart_gui(self, file_name, data_view='coronal'):
        """
        Restart GUI if new main image is loaded.
        """
        # Disconnect any important signals
        if hasattr(self.LoadMRI, "minimap"):
            zoom_notifier.factorChanged.disconnect(self.LoadMRI.minimap.create_small_rectangle)

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
        self.LoadMRI.file_name = {}
        self.LoadMRI.file_name[0] = file_name
        image = sITK.ReadImage(file_name)
        volume = sITK.GetArrayFromImage(image)
        if volume.ndim==4:
            self.ui.groupBox_data0.setTitle(f"View: {data_view.upper()}")

        self.save_info_of_mainimage(data_view,0,file_name)

        zoom_notifier.factorChanged.connect(self.LoadMRI.minimap.create_small_rectangle)
        Zoom.fit_to_window(self.LoadMRI.vtk_widgets[0]["coronal"], self.LoadMRI.vtk_widgets.values(), self.LoadMRI.scale_bar, self.LoadMRI.vtk_widgets,0,data_3d=True)

        print('ende')
        return


    def quit(self):
        QtWidgets.QApplication.quit()


if __name__ == "__main__":
    #to mix vtk and QtQuick3D
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    #dark mode
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())

