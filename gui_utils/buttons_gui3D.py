# This Python file uses the following encoding: utf-8
import os
from core.paintbrush import Paintbrush
from utils.contrast import Contrast
from core.resample_data import ResampleData
from utils.zoom import Zoom
from core.measurement import Measurement
from core.interactor_style import CustomInteractorStyle
from utils.minimap_handler import Minimap
from gui_utils.paintbrush_gui import PaintbrushGUI
from core.registration import Registration
from core.segmentation_utils import Segmentation
from gui_utils.segmentation_gui import SegmentationGUI

# This Python file uses the following encoding: utf-8
from PySide6.QtWidgets import QDockWidget,QDialog,QVBoxLayout
from PySide6.QtCore import Qt
import SimpleITK as sITK
from pathlib import Path
from PySide6.QtWidgets import QMessageBox



class PopupDialog(QDialog):
    def __init__(self,parent=None, ui_widget=None):
        super().__init__(parent)
        self.setWindowTitle("Resampling Function")
        layout = QVBoxLayout(self)
        layout.addWidget(ui_widget)
        self.resize(1000,400)

    def closeEvent(self, event):
        # Instead of destroying, just hide the window
        self.hide()
        event.ignore()



class ButtonsGUI_3D:
    def __init__(self,MW,data_index):
        """
           Initialize the 3D buttons GUI.

           Args:
               MW: The main window instance containing UI and MRI data references.
        """
        self.MW = MW
        self.ui = MW.ui
        self.LoadMRI = MW.LoadMRI

        self.buttons_3D(data_index)



    def buttons_3D(self,data_index):
        """
        Set up the UI components, VTK widgets, and basic initialization for 3D mode.
        """
        file_name = self.LoadMRI.volumes[data_index].file_path
        target = self.ui.file_name_displayed_4d
        target.setPlainText("File loaded: " + os.path.basename(file_name))
        #target.setPlainText(os.path.basename(file_name))
        target.setReadOnly(True)
        target.setStyleSheet("color: white; font-size: 8pt;")

        lm = self.LoadMRI
        lm.vtk_widgets = {}
        lm.vtk_widgets[0] = {
            "coronal": self.ui.vtkWidget_data_coronal,
            "sagittal": self.ui.vtkWidget_data_sagittal,
            "axial": self.ui.vtkWidget_data_axial,
        }

        print('lm.vtk_widgets created', flush=True)

        self.ui.actionAddViewImage.triggered.connect(self.MW.add_another_file)


        #initialize everything
        self.LoadMRI.image_index = 0
        self.initialize_zoom_controls(data_index)
        self.initialize_contrast(data_index)
        self.initialize_cursor(data_index)

        self.LoadMRI.movingimg_filename = []
        self.ui.actionRegister.triggered.connect(self.initialize_registration)
        self.ui.actionResample.triggered.connect(self.initialize_resampling)
        self.ui.actionPaintbrush.triggered.connect(self.initialize_paintbrush)
        self.ui.actionSegmentation.triggered.connect(self.initialize_segmentation)
        self.ui.actionMeasurement.triggered.connect(self.initialize_measurement)




    def initialize_contrast(self,data_index):
        """
        Initialize contrast and brightness controls for multiple image views.
        """
        lm = self.LoadMRI

        lm.contrast_ui_elements[0] = {
            "contrast0": self.ui.changeContrast_data3d,
            "brightness0": self.ui.changeBrightness_data3d,
            "display_level0": self.ui.display_level_data3d,
            "display_window0": self.ui.display_window_data3d,
            "auto0": self.ui.pushButton_auto_data3d,
            "reset0": self.ui.pushButton_reset_data3d,
        }

        # initialize Contrast class (for each data_view once)
        lm.contrast[0] = Contrast(lm, data_index=0)

        self.LoadMRI.contrast_ui_elements[0]["brightness0"].valueChanged.connect(
            lambda value: lm.contrast[0].changed_sliders(value, image_index=0) # lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[0]["contrast0"].valueChanged.connect(
            lambda value: lm.contrast[0].changed_sliders(value, image_index=0) # lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[0]["auto0"].clicked.connect(
            lambda: lm.contrast[0].auto(image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[0]["reset0"].clicked.connect(
            lambda: lm.contrast[0].reset(image_index=0)
        )


    def initialize_cursor(self,data_index):
        """
        Configure spinboxes and connect cursor/contrast event handlers.
        """
        lm = self.LoadMRI

        if data_index==0:
            lm.cursor_ui = {
                'spin_x0': self.ui.spinBox_x_data3d,
                'spin_y0': self.ui.spinBox_y_data3d,
                'spin_z0': self.ui.spinBox_z_data3d,
                'intensity0': self.ui.tableintensity_data3d.item(0, 2), #self.ui.intensity_main_Post,
                'scroll_0': self.ui.Scroll_data3d0,
                'scroll_1': self.ui.Scroll_data3d1,
                'scroll_2': self.ui.Scroll_data3d2,
            }

        spin_x = lm.cursor_ui[f"spin_x{data_index}"]
        spin_y = lm.cursor_ui[f"spin_y{data_index}"]
        spin_z = lm.cursor_ui[f"spin_z{data_index}"]
        spin_x.setMaximum(lm.volumes[data_index].slices[0].shape[2])
        spin_y.setMaximum(lm.volumes[data_index].slices[0].shape[1])
        spin_z.setMaximum(lm.volumes[data_index].slices[0].shape[0])


    def initialize_paintbrush(self):
        """
        Initialize paintbrush tool controls for MRI segmentation.
        """
        # give the dock a unique object name
        dock_name = "dock_paintbrush"

        # check if it exists already
        dock = self.MW.findChild(QDockWidget, dock_name)
        if dock is None:
            dock = QDockWidget("Paintbrush", self.MW)
            dock.setObjectName(dock_name)
            dock.setWidget(self.ui.groupBox_paintbrush_3d)
            self.MW.addDockWidget(Qt.RightDockWidgetArea, dock)
            dock.visibilityChanged.connect(lambda visible: setattr(self.LoadMRI, 'brush_on', False) if not visible else None)

            self.LoadMRI.brush = {
                'size': self.ui.brush_size3d,
                'size_slider': self.ui.brush_sizeSlider3d,
                'label_occ': self.ui.doubleSpinBox_labelOcc3d,
                'label_occ_slider': self.ui.sizeSlider_labelOcc3d
            }
            #Connect paintbrush for segmentation and MRID-tags
            self.LoadMRI.paintbrush = Paintbrush(self.LoadMRI)
            self.LoadMRI.PaintbrushGUI = PaintbrushGUI(self.MW,True)
        else:
            dock.show()
            dock.raise_()



    def initialize_zoom_controls(self, data_index):
        """
        Connect zoom and pan buttons for all image views.
        """
        lm = self.LoadMRI
        for _,views in lm.vtk_widgets.items():
            for idx, (_, widget) in enumerate(views.items()):
                zoom_in_btn = getattr(self.ui, f"zoom_in_data3d{idx}")
                zoom_out_btn = getattr(self.ui, f"zoom_out_data3d{idx}")
                zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets, data_index,data_3d=True))
                zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets, data_index,data_3d=True))
                fit_window_btn = getattr(self.ui, f"fit_to_zoom_data3d{idx}")
                fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets, data_index,data_3d=True))

        # initialize Minimap class
        if data_index==0:
            self.LoadMRI.minimap = Minimap(self.LoadMRI)
        idx=0
        pan_distance = 0.4
        go_down_btn = getattr(self.ui, f"go_down_data3d{idx}")
        go_up_btn = getattr(self.ui, f"go_up_data3d{idx}")
        go_right_btn = getattr(self.ui, f"go_right_data3d{idx}")
        go_left_btn = getattr(self.ui, f"go_left_data3d{idx}")
        go_down_btn.clicked.connect(lambda _, v='coronal', i=0: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=0,diff_y=-pan_distance,data_index=idx,data_3d=True))
        go_up_btn.clicked.connect(lambda _, v='coronal', i=0: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=0,diff_y=pan_distance,data_index=idx,data_3d=True))
        go_right_btn.clicked.connect(lambda _, v='coronal', i=0: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=pan_distance,diff_y=0,data_index=idx,data_3d=True))
        go_left_btn.clicked.connect(lambda _, v='coronal', i=0: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=-pan_distance,diff_y=0,data_index=idx,data_3d=True))
        idx=1
        go_down_btn = getattr(self.ui, f"go_down_data3d{idx}")
        go_up_btn = getattr(self.ui, f"go_up_data3d{idx}")
        go_right_btn = getattr(self.ui, f"go_right_data3d{idx}")
        go_left_btn = getattr(self.ui, f"go_left_data3d{idx}")
        go_down_btn.clicked.connect(lambda _, v='sagittal', i=1: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=0,diff_y=-pan_distance,data_index=idx,data_3d=True))
        go_up_btn.clicked.connect(lambda _, v='sagittal', i=1: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=0,diff_y=pan_distance,data_index=idx,data_3d=True))
        go_right_btn.clicked.connect(lambda _, v='sagittal', i=1: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=pan_distance,diff_y=0,data_index=idx,data_3d=True))
        go_left_btn.clicked.connect(lambda _, v='sagittal', i=1: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=-pan_distance,diff_y=0,data_index=idx,data_3d=True))
        idx=2
        go_down_btn = getattr(self.ui, f"go_down_data3d{idx}")
        go_up_btn = getattr(self.ui, f"go_up_data3d{idx}")
        go_right_btn = getattr(self.ui, f"go_right_data3d{idx}")
        go_left_btn = getattr(self.ui, f"go_left_data3d{idx}")
        go_down_btn.clicked.connect(lambda _, v='axial', i=2: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=0,diff_y=-pan_distance,data_index=idx,data_3d=True))
        go_up_btn.clicked.connect(lambda _, v='axial', i=2: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=0,diff_y=pan_distance,data_index=idx,data_3d=True))
        go_right_btn.clicked.connect(lambda _, v='axial', i=2: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=pan_distance,diff_y=0,data_index=idx,data_3d=True))
        go_left_btn.clicked.connect(lambda _, v='axial', i=2: self.LoadMRI.minimap.pan_arrows(view_name=v,diff_x=-pan_distance,diff_y=0,data_index=idx,data_3d=True))


    def initialize_measurement(self):
        """
        Toggle measurement mode for MRI views and update interactor styles.
        """

        # give the dock a unique object name
        dock_name = "dock_measurement"

        # check if it exists already
        dock = self.MW.findChild(QDockWidget, dock_name)
        if dock is None:
            dock = QDockWidget("Measurement", self.MW)
            dock.setObjectName(dock_name)
            dock.setWidget(self.ui.groupBox_measurement)
            self.MW.addDockWidget(Qt.RightDockWidgetArea, dock)

            self.ui.checkBox_measurement.stateChanged.connect(self.measurement_function)
        else:
            dock.show()
            dock.raise_()

        checkbox = self.ui.checkBox_measurement
        data_view = 'coronal'
        if checkbox.isChecked():
            checkbox.setText("ON")
            self.LoadMRI.cursor.start_cursor(False,0,data_view)
            self.LoadMRI.measurement_table = self.ui.tableWidget_meaurement
            measurement = Measurement(self.LoadMRI)
            self.ui.pushButton_deleteMeasurement.clicked.connect(measurement.delete_measurement)
            #self.ui.comboBox_measurementColors.currentIndexChanged.connect(lambda index: measurement.change_color(index))
            self.ui.comboBox_measurementColors.currentIndexChanged.connect(
                lambda index: (setattr(measurement, "color_index", index), measurement.change_color(index))
            )
            for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, vtk_widget in vtk_widget_image.items():
                    interactor = vtk_widget.GetRenderWindow().GetInteractor()
                    interactor.SetInteractorStyle(None)
                    interactor.SetInteractorStyle(CustomInteractorStyle(self.LoadMRI.cursor, view_name,image_index,measurement,0))
        else:
            checkbox.setText("OFF")
            self.LoadMRI.cursor.start_cursor(True,0,data_view)

    def measurement_function(self):
        checkbox = self.ui.checkBox_measurement
        data_view = 'coronal'
        if checkbox.isChecked():
            checkbox.setText("ON")
            self.LoadMRI.cursor.start_cursor(False,0,data_view)
            measurement = Measurement(self.LoadMRI)
            for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, vtk_widget in vtk_widget_image.items():
                    interactor = vtk_widget.GetRenderWindow().GetInteractor()
                    interactor.SetInteractorStyle(None)
                    interactor.SetInteractorStyle(CustomInteractorStyle(self.LoadMRI.cursor, view_name,image_index,measurement,0))
        else:
            checkbox.setText("OFF")
            self.LoadMRI.cursor.start_cursor(True,0,data_view)

    def initialize_resampling(self):
        """
        Initialize resampling controls.
        """
        if hasattr(self, "popup") and self.popup.isVisible():
            self.popup.raise_()
            self.popup.activateWindow()
            return
        w = self.ui.groupBox_resample  # widget inside main UI
        self.popup = PopupDialog(parent=self.MW,ui_widget=w)
        self.popup.resize(300, 300)
        self.popup.show()

        self.LoadMRI.Resample = ResampleData(self.LoadMRI)
        #get the current index of the combobox
        self.ui.pushButton_resample100um.clicked.connect(
            lambda: self.resample100um(
                self.ui.comboBox_resamplefiles.currentIndex()
            )
        )

        self.ui.pushButton_resample25um.clicked.connect(
            lambda: self.resample25um(
                self.ui.comboBox_resamplefiles.currentIndex()
            )
        )
        self.ui.pushButton_openfile100um.clicked.connect(lambda: self.LoadMRI.Resample.open_as_new_file(self,self.MW))
        self.ui.pushButton_done.clicked.connect(self.popup.close)

        filename_end = 'resampled100um.nii.gz'
        file_name = self.LoadMRI.volumes[0].file_path[:-7]
        default_name = f"{file_name}_{filename_end}" #"label_volume.nii.gz"
        file_path = os.path.join(self.LoadMRI.session_path, default_name)
        file_path = Path(file_path)
        if file_path.is_file():
            self.ui.textEdit_resample100.setText(f"A file called \n {default_name} \n already exists. You can directly open this file.")
            self.ui.pushButton_openfile100um.setEnabled(True)
            self.LoadMRI.Resample.file_name100um = file_name

        filename_end = 'resampled.nii.gz'
        default_name = f"{file_name}_{filename_end}" #"label_volume.nii.gz"
        file_path = os.path.join(self.LoadMRI.session_path, default_name)
        file_path = Path(file_path)
        if file_path.is_file():
            self.ui.textEdit_resample25.setText(f"A file called \n {default_name} \n already exists.")


    def resample100um(self,index):
        print('index combobox',self.ui.comboBox_resamplefiles.currentIndex(),flush=True)
        self.LoadMRI.Resample.progressbar = self.ui.progressBar_100um
        filename_end = 'resampled100um.nii.gz'
        file_name = self.LoadMRI.volumes[index].file_path[:-7]
        default_name = f"{file_name}_{filename_end}"
        file_path = os.path.join(self.LoadMRI.session_path, default_name)
        file_path = Path(file_path)

        if file_path.is_file():
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Overwriting File")
            msg_box.setText(f"A file called \n {default_name} \n already exists. Are you sure you want to overwrite it?")
            msg_box.addButton("Yes", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
            msg_box.exec()
            if msg_box.clickedButton()==btn_cancel:
                self.ui.textEdit_resample100.setText(f"Existing file \n {default_name}")
                self.ui.pushButton_openfile100um.setEnabled(True)
                self.LoadMRI.Resample.file_name100um = default_name
                return

        default_name = self.LoadMRI.Resample.resampling100um(index)
        self.ui.textEdit_resample100.setText(f"Resampling Done with saved as \n {default_name}")
        self.ui.pushButton_openfile100um.setEnabled(True)

    def resample25um(self,index):
        self.LoadMRI.Resample.progressbar = self.ui.progressBar_25um
        filename_end = 'resampled.nii.gz'
        file_name = self.LoadMRI.volumes[index].file_path[:-7]
        default_name = f"{file_name}_{filename_end}" #"label_volume.nii.gz"
        file_path = os.path.join(self.LoadMRI.session_path, default_name)
        file_path = Path(file_path)

        if file_path.is_file():
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Overwriting File")
            msg_box.setText(f"A file called {default_name} already exists. Are you sure you want to overwrite it?")
            msg_box.addButton("Yes", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
            msg_box.exec()
            if msg_box.clickedButton()==btn_cancel:
                self.ui.textEdit_resample25.setText(f"Existing file \n {default_name}")
                return

        default_name = self.LoadMRI.Resample.resampling25um(index)
        self.ui.textEdit_resample25.setText(f"Resampling Done with saved as \n {default_name}")


    def initialize_registration(self):
        """
        Initialize registration workflow.
        """
        if hasattr(self, "popup") and self.popup.isVisible():
            self.popup.raise_()
            self.popup.activateWindow()
            return
        w = self.ui.groupBox_register
        self.popup = PopupDialog(parent=self.MW,ui_widget=w)
        self.popup.resize(300, 300)
        self.popup.show()

        self.ui.comboBox_movingimg.currentIndexChanged.connect(lambda index: self.check_dimensions_movingimg(index))

        self.ui.pushButton_registration.clicked.connect(
            lambda: setattr(self.LoadMRI, "Registration", Registration(self.LoadMRI,self,self.ui.comboBox_movingimg.currentIndex()))
        )

        self.LoadMRI.progressbar_registration = self.ui.progressBar_registration

        self.ui.pushButton_regCancel.clicked.connect(self.cancel_reg)

        if len(self.LoadMRI.movingimg_filename):
            self.check_dimensions_movingimg(0)
        else:
            self.MW.ui.textEdit_pixels.setVisible(False)

        self.LoadMRI.coarsest_index = 1 #comboBox_coarsest
        self.LoadMRI.finest_index = 0 #comboBox_finest
        self.ui.comboBox_coarest.setCurrentIndex(self.LoadMRI.coarsest_index)
        self.ui.comboBox_coarest.currentIndexChanged.connect(
            lambda idx: setattr(self.LoadMRI, "coarsest_index", idx)
        )
        self.ui.comboBox_finest.currentIndexChanged.connect(
            lambda idx: setattr(self.LoadMRI, "finest_index", idx)
        )

    def cancel_reg(self):
         self.popup.close()

    def check_dimensions_movingimg(self,index):
        image = sITK.ReadImage(self.LoadMRI.movingimg_filename[index])
        volume = sITK.GetArrayFromImage(image)
        moving_ind = self.LoadMRI.movingimg_filename[index][:-7].split("ind_")[1]
        fixed_ind = self.MW.LoadMRI.volumes[0].file_path[:-7].split("ind_")[1]
        transform_filename = f"transformation_ind_{moving_ind}-to-ind_{fixed_ind}.txt"
        file_path = os.path.join(self.LoadMRI.session_path, 'anat',transform_filename)
        file_path1 = Path(file_path)
        transform_filename = f"transformation_ind_{fixed_ind}-to-ind_{moving_ind}.txt"
        file_path = os.path.join(self.LoadMRI.session_path, 'anat',transform_filename)
        file_path2 = Path(file_path)

        if file_path1.is_file() or file_path2.is_file():
            self.MW.ui.textEdit_pixels.setText('A transformation file between these two files already exists.')
            self.MW.ui.textEdit_pixels.setVisible(True)
            self.MW.ui.pushButton_registration.setEnabled(False)
            return

        if volume.shape[1]<4 or volume.shape[2]<4 or volume.shape[3]<4:
            self.MW.ui.textEdit_pixels.setText('Please select other file. The MRI Scan needs at least 4pixels in each direction.')
            self.MW.ui.textEdit_pixels.setVisible(True)
            self.MW.ui.pushButton_registration.setEnabled(False)
        else:
            self.MW.ui.pushButton_registration.setEnabled(True)
            self.MW.ui.textEdit_pixels.setVisible(False)




    def initialize_segmentation(self):
        """
        Initialize segmenation workflow.
        """
        # give the dock a unique object name
        dock_name = "dock_segmentation"

        # check if it exists already
        dock = self.MW.findChild(QDockWidget, dock_name)
        if dock is None:
            dock = QDockWidget("Segmentation", self.MW)
            dock.setObjectName(dock_name)
            dock.setWidget(self.ui.groupBox_segmentation)
            self.MW.addDockWidget(Qt.RightDockWidgetArea, dock)

            #Connect paintbrush for segmentation and MRID-tags
            self.LoadMRI.SegmentationGUI = SegmentationGUI(self.MW)
            #self.LoadMRI.Segmentation = Segmentation(self.LoadMRI)
        else:
            dock.show()
            dock.raise_()

        self.LoadMRI.SegmentationGUI.on_threshold_changed(checked=True)







