# This Python file uses the following encoding: utf-8
# Important: You need to run the following command to generate the ui_form.py file: pyside6-uic form.ui -o ui_form.py

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from ui_form import Ui_MainWindow
from core.load_MRI_file import LoadMRI
import os
from utils.zoom import Zoom, zoom_notifier
from core.measurement import Measurement
from core.interactor_style import CustomInteractorStyle
from utils.minimap_handler import Minimap
from core.paintbrush import Paintbrush
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, QIcon, QColor
from utils.contrast import Contrast
from utils.inputdialog import InputDialog
from PySide6 import QtWidgets,QtCore
from core.mrid_tags import MRID_tags
from userdialog_window import UserDialog_Window
from core.resample_data import ResampleData
from core.segmentation.threshold import ThresholdSegmentation
from PySide6.QtWidgets import (
    QTableWidgetItem, QVBoxLayout, QToolButton, QDoubleSpinBox
)
from PySide6.QtGui import QStandardItem
from PySide6.QtCore import Qt
from core.segmentation.initialization import SegmentationInitialization
from core.segmentation.evolution import SegmentationEvolution
from core.registration import Registration



### TODO: divide this class in several smaller classes/files



class MainWindow(QMainWindow):
    """
    Main application window for MRI visualization.

    Handles loading MRI files (3D or 4D), cursor control, zooming,
    measurement activation, and interaction with the VTK widgets.
    """
    def __init__(self, parent=None):
        """Initialize the main window and setup UI elements."""
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.file_loaded = False

        # Create loader
        self.LoadMRI = LoadMRI()
        self.open_user_dialog()

        self.LoadMRI.fileLoaded.connect(self.on_file_loaded)

        #File loaded buttons
        self.ui.toolButton_LoadFile.clicked.connect(self.userdialog.open_new_file)
        self.ui.toolButton_LoadFile_Post.clicked.connect(self.userdialog.open_new_file)

        # Measurement checkbox
        self.ui.checkBox_measurement.stateChanged.connect(self.measurement_function)

        #Change of tab to rerender windows
        self.ui.tabWidget.currentChanged.connect(lambda index: self.on_tab_changed(index))
        self.LoadMRI.load_file(self.LoadMRI.vol_dim[self.LoadMRI.data_index])

        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

        # Input for MRID tags
        self.ui.pushButton_MRIDtags.clicked.connect(self.open_input_dialog)

        #Set table for images and intensities
        self.intensity_table()



    def open_user_dialog(self):
        """ Open the initial User Dialog when the application starts. """
        self.userdialog = UserDialog_Window(self)
        self.userdialog.exec()


    def on_tab_changed(self, index:int):
        if index == 0:
            self.ui.vtkWidget_axial.GetRenderWindow().Render()
            self.ui.vtkWidget_coronal.GetRenderWindow().Render()
            self.ui.vtkWidget_sagittal.GetRenderWindow().Render()
            self.ui.graphicsView_2.GetRenderWindow().Render()
        elif index == 1:
            self.ui.vtkWidget_axial_image1.GetRenderWindow().Render()
            self.ui.vtkWidget_coronal_image1.GetRenderWindow().Render()
            self.ui.vtkWidget_sagittal_image1.GetRenderWindow().Render()
            self.ui.vtkWidget_axial_image2.GetRenderWindow().Render()
            self.ui.vtkWidget_coronal_image2.GetRenderWindow().Render()
            self.ui.vtkWidget_sagittal_image2.GetRenderWindow().Render()
            self.ui.vtkWidget_axial_image3.GetRenderWindow().Render()
            self.ui.vtkWidget_coronal_image3.GetRenderWindow().Render()
            self.ui.vtkWidget_sagittal_image3.GetRenderWindow().Render()
            self.ui.vtkWidget_axial_image4.GetRenderWindow().Render()
            self.ui.vtkWidget_coronal_image4.GetRenderWindow().Render()
            self.ui.vtkWidget_sagittal_image4.GetRenderWindow().Render()

    def on_file_loaded(self):
        """
        Callback when an MRI file is successfully loaded.

        Sets up VTK widgets, cursor spinboxes, contrast UI, zoom controls,
        and minimap integration based on the volume dimension.
        """
        file_name = self.LoadMRI.file_name[0]
        self.vol_dim = self.LoadMRI.vol_dim[0]

        # Display loaded file name
        if self.vol_dim  == 3:
            target = self.ui.file_name_displayed
        else:
            target = self.ui.file_name_displayed_Post

        target.setPlainText(os.path.basename(file_name))
        target.setReadOnly(True)
        target.setStyleSheet("color: green; font-size: 8pt;")

        # Connect image to widget and store in LoadMRI
        lm = self.LoadMRI
        lm.vtk_widgets = {}
        if self.vol_dim==3:
            lm.vtk_widgets[0] = {
                "axial": self.ui.vtkWidget_axial,
                "coronal": self.ui.vtkWidget_coronal,
                "sagittal": self.ui.vtkWidget_sagittal
            }
            contrast_elements = {
                "contrast0": self.ui.changeContrast,
                "brightness0": self.ui.changeBrightness,
                "display_level0": self.ui.display_level,
                "display_window0": self.ui.display_window,
                "auto0": self.ui.pushButton_auto,
                "reset0": self.ui.pushButton_reset
            }
            lm.cursor_ui = {
                'spin_x': self.ui.spinBox_x,
                'spin_y': self.ui.spinBox_y,
                'spin_z': self.ui.spinBox_z,
                'intensity0': self.ui.tableWidget_images.item(0, 2), #self.ui.intensity_main,
                'scroll_x': self.ui.Scroll_sagittal,
                'scroll_y': self.ui.Scroll_coronal,
                'scroll_z': self.ui.Scroll_axial
            }
            lm.brush = {
                'size': self.ui.brush_size,
                'size_slider': self.ui.brush_sizeSlider,
                'label_occ': self.ui.spinbox_brush_label_opa,
                'label_occ_slider': self.ui.slider_brush_label_opa
            }

            #paintbrush_function -> checkBox_Brush
            self.initialization_first_time = True
            self.ui.toolbar.currentChanged.connect(self.on_tab3D_changed)
            self.ui.checkBox_threshold.stateChanged.connect(self.on_threshold_changed)
            #pushButtons Next and Back
            self.ui.pushButton_Next1.clicked.connect(self.active_bubbles)
            self.ui.pushButton_Back2.clicked.connect(self.threshold_seg)
            self.ui.pushButton_Next2.clicked.connect(self.evolution)
            self.ui.pushButton_Back3.clicked.connect(self.active_bubbles)
            #self.ui.pushButton_Finish.clicked.connect(self.seg_finsih)
        else:
            lm.vtk_widgets[0] = {
                "axial": self.ui.vtkWidget_axial_image1,
                "coronal": self.ui.vtkWidget_coronal_image1,
                "sagittal": self.ui.vtkWidget_sagittal_image1,
            }

            lm.vtk_widgets[1] = {
                "axial": self.ui.vtkWidget_axial_image2,
                "coronal": self.ui.vtkWidget_coronal_image2,
                "sagittal": self.ui.vtkWidget_sagittal_image2,
            }
            lm.vtk_widgets[2] = {
                "axial": self.ui.vtkWidget_axial_image3,
                "coronal": self.ui.vtkWidget_coronal_image3,
                "sagittal": self.ui.vtkWidget_sagittal_image3,
            }

            self.ui.spinBox_x_Post.setMaximum(lm.volume[self.LoadMRI.data_index][0].shape[2])
            self.ui.spinBox_y_Post.setMaximum(lm.volume[self.LoadMRI.data_index][0].shape[1])
            self.ui.spinBox_z_Post.setMaximum(lm.volume[self.LoadMRI.data_index][0].shape[0])

            contrast_elements = {
                "contrast0": self.ui.changeContrast_Post1,
                "contrast1": self.ui.changeContrast_Post2,
                "contrast2": self.ui.changeContrast_Post3,
                "brightness0": self.ui.changeBrightness_Post1,
                "brightness1": self.ui.changeBrightness_Post2,
                "brightness2": self.ui.changeBrightness_Post3,
                "display_level0": self.ui.display_level_Post1,
                "display_level1": self.ui.display_level_Post2,
                "display_level2": self.ui.display_level_Post3,
                "display_window0": self.ui.display_window_Post1,
                "display_window1": self.ui.display_window_Post2,
                "display_window2": self.ui.display_window_Post3,
                "auto0": self.ui.pushButton_auto_Post1,
                "auto1": self.ui.pushButton_auto_Post2,
                "auto2": self.ui.pushButton_auto_Post3,
                "reset0": self.ui.pushButton_reset_Post1,
                "reset1": self.ui.pushButton_reset_Post2,
                "reset2": self.ui.pushButton_reset_Post3,
            }
            lm.cursor_ui = {
                'spin_x': self.ui.spinBox_x_Post,
                'spin_y': self.ui.spinBox_y_Post,
                'spin_z': self.ui.spinBox_z_Post,
                'intensity0': self.ui.tableWidget_images.item(0, 2), #self.ui.intensity_main_Post,
                'scroll_x': self.ui.Scroll_sagittal_Post,
                'scroll_y': self.ui.Scroll_coronal_Post,
                'scroll_z': self.ui.Scroll_axial_Post
            }

            lm.brush = {
                'size': self.ui.brush_size_Post,
                'size_slider': self.ui.brush_sizeSlider_Post,
                'label_occ': self.ui.doubleSpinBox_labelOcc,
                'label_occ_slider': self.ui.sizeSlider_labelOcc
            }


        #Setup zoom controls
        self.setup_zoom_controls()

        # set up corsur with UI
        self.setup_cursor_controls(self.vol_dim)

        #connect all contrast UI
        lm.contrast_ui_elements = contrast_elements

        #Connect paintbrush for segmentation and MRID-tags
        self.LoadMRI.paintbrush = Paintbrush(self.LoadMRI)

        lm.image_index = 0

        # initialize Contrast class
        lm.contrastClass = Contrast(lm)
        self.LoadMRI.minimap.minimap_renderers = {}

        self.LoadMRI.contrast_ui_elements["brightness0"].valueChanged.connect(
            lambda value: lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements["contrast0"].valueChanged.connect(
            lambda value: lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements["auto0"].clicked.connect(
            lambda: lm.contrastClass.auto(image_index=0)
        )
        self.LoadMRI.contrast_ui_elements["reset0"].clicked.connect(
            lambda: lm.contrastClass.reset(image_index=0)
        )
        if self.vol_dim == 4:
            self.LoadMRI.contrast_ui_elements["brightness1"].valueChanged.connect(
                lambda value: lm.contrastClass.changed_sliders(value,image_index=1)
            )
            self.LoadMRI.contrast_ui_elements["contrast1"].valueChanged.connect(
                lambda value: lm.contrastClass.changed_sliders(value,image_index=1)
            )
            self.LoadMRI.contrast_ui_elements["auto1"].clicked.connect(
                lambda: lm.contrastClass.auto(image_index=1)
            )
            self.LoadMRI.contrast_ui_elements["reset1"].clicked.connect(
                lambda: lm.contrastClass.reset(image_index=1)
            )
            self.LoadMRI.contrast_ui_elements["brightness2"].valueChanged.connect(
                lambda value: lm.contrastClass.changed_sliders(value,image_index=2)
            )
            self.LoadMRI.contrast_ui_elements["contrast2"].valueChanged.connect(
                lambda value: lm.contrastClass.changed_sliders(value,image_index=2)
            )
            self.LoadMRI.contrast_ui_elements["auto2"].clicked.connect(
                lambda: lm.contrastClass.auto(image_index=2)
            )
            self.LoadMRI.contrast_ui_elements["reset2"].clicked.connect(
                lambda: lm.contrastClass.reset(image_index=2)
            )
            self.set_timestampChange()

        #resampling function
        self.LoadMRI.Resample = ResampleData(self.LoadMRI)
        self.ui.pushButton_resample100um.clicked.connect(self.LoadMRI.Resample.resampling100um)
        self.ui.pushButton_resample25um.clicked.connect(self.LoadMRI.Resample.resampling25um)
        self.ui.pushButton_registration.clicked.connect(self.registration)

    def set_timestampChange(self):
        """Connect timestamp spinboxes and sliders for 4D volumes."""
        lm = self.LoadMRI
        for idx in range(3):
            spinbox = getattr(self.ui, f"displaytimestamp_image{idx+1}")
            combobox = getattr(self.ui, f"changetimestamp_image{idx+1}")
            spinbox.setMinimum(0)
            combobox.setMinimum(0)
            max_val = lm.volume4D.shape[0] - 1
            spinbox.setMaximum(max_val)
            combobox.setMaximum(max_val)
            spinbox.setValue(idx * 4)
            combobox.setValue(idx * 4)
            spinbox.valueChanged.connect(lambda val, i=idx: self.timestamp4D_changed(val, i))
            combobox.valueChanged.connect(lambda val, i=idx: self.timestamp4D_changed(val, i))


    def timestamp4D_changed(self,value, image_index: int):
        """Change displayed values in timestamp spinboxes and sliders if changed by user."""
        spinbox = getattr(self.ui, f"displaytimestamp_image{image_index+1}")
        combobox = getattr(self.ui, f"changetimestamp_image{image_index+1}")
        spinbox.blockSignals(True)
        combobox.blockSignals(True)
        spinbox.setValue(value)
        combobox.setValue(value)
        spinbox.blockSignals(False)
        combobox.blockSignals(False)
        self.LoadMRI.timestamp4D_changed(value, image_index)


    def setup_cursor_controls(self,vol_dim:int):
        """
        Connect spinboxes to cursor coordinate updates.
        """
        lm = self.LoadMRI
        # Select spinboxes based on volume type
        if vol_dim == 3:
            lm.spinboxes = {
                'x': self.ui.spinBox_x,
                'y': self.ui.spinBox_y,
                'z': self.ui.spinBox_z
            }
        else:
            lm.spinboxes = {
                'x': self.ui.spinBox_x_Post,
                'y': self.ui.spinBox_y_Post,
                'z': self.ui.spinBox_z_Post
            }
        # Set ranges
        lm.spinboxes['x'].setRange(1, lm.volume[self.LoadMRI.data_index][0].shape[2])
        lm.spinboxes['y'].setRange(1, lm.volume[self.LoadMRI.data_index][0].shape[1])
        lm.spinboxes['z'].setRange(1, lm.volume[self.LoadMRI.data_index][0].shape[0])

        # Connect spinboxes to your cursor_coord_changed method
        for axis, spinbox in lm.cursor_ui.items():
            lm.cursor_ui['spin_x'].valueChanged.connect(lambda val, ax=axis: self.LoadMRI.cursor.cursor_coord_changed(ax, val))


    def setup_zoom_controls(self):
        """
        Connect all zoom in/out and fit-to-window buttons for all views.
        Initializes the Minimap class and connects pan buttons.
        """
        lm = self.LoadMRI

        # Loop through the vtk_widgets dict directly
        for view_name in ["axial", "coronal", "sagittal"]:
            zoom_in_btn = getattr(self.ui, f"zoom_in_{view_name}")
            zoom_out_btn = getattr(self.ui, f"zoom_out_{view_name}")
            zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets))
            zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets))

        for image_index,views in lm.vtk_widgets.items():
            for view_name, widget in views.items():
                zoom_in_btn = getattr(self.ui, f"zoom_in_{view_name}_{image_index}")
                zoom_out_btn = getattr(self.ui, f"zoom_out_{view_name}_{image_index}")

                zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets))
                zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets))

                fit_window_btn = getattr(self.ui, f"fit_to_zoom_{view_name}_{image_index}")
                fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets))

                fit_window_btn = getattr(self.ui, f"fit_to_zoom_{view_name}")
                fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets))

        # initialize Minimap class
        self.LoadMRI.minimap = Minimap(self.LoadMRI)

        zoom_notifier.factorChanged.connect(self.LoadMRI.minimap.create_small_rectangle)

        pan_distance = 0.025
        self.ui.go_down_image1.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y-pan_distance))
        self.ui.go_up_image1.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y+pan_distance))
        self.ui.go_right_image1.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x+pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_left_image1.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x-pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_down_image2.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y-pan_distance))
        self.ui.go_up_image2.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y+pan_distance))
        self.ui.go_right_image2.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x+pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_left_image2.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x-pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_down_image3.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y-pan_distance))
        self.ui.go_up_image3.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y+pan_distance))
        self.ui.go_right_image3.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x+pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_left_image3.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x-pan_distance,new_y=self.LoadMRI.rect_old_y))


        self.ui.go_down_axial.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y-pan_distance))
        self.ui.go_up_axial.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_y+pan_distance))
        self.ui.go_right_axial.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x+pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_left_axial.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='axial',new_x=self.LoadMRI.rect_old_x-pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_down_coronal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='coronal',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_z-pan_distance))
        self.ui.go_up_coronal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='coronal',new_x=self.LoadMRI.rect_old_x,new_y=self.LoadMRI.rect_old_z+pan_distance))
        self.ui.go_right_coronal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='coronal',new_x=self.LoadMRI.rect_old_x+pan_distance,new_y=self.LoadMRI.rect_old_z))
        self.ui.go_left_coronal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='coronal',new_x=self.LoadMRI.rect_old_x-pan_distance,new_y=self.LoadMRI.rect_old_z))
        self.ui.go_down_sagittal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='sagittal',new_x=self.LoadMRI.rect_old_z,new_y=self.LoadMRI.rect_old_y-pan_distance))
        self.ui.go_up_sagittal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='sagittal',new_x=self.LoadMRI.rect_old_z,new_y=self.LoadMRI.rect_old_y+pan_distance))
        self.ui.go_right_sagittal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='sagittal',new_x=self.LoadMRI.rect_old_z-pan_distance,new_y=self.LoadMRI.rect_old_y))
        self.ui.go_left_sagittal.clicked.connect(lambda: self.LoadMRI.minimap.create_small_rectangle(vn='sagittal',new_x=self.LoadMRI.rect_old_z+pan_distance,new_y=self.LoadMRI.rect_old_y))


    def measurement_function(self):
        """
        Toggle measurement mode for MRI views.
        """
        checkbox = self.ui.checkBox_measurement
        if checkbox.isChecked():
            checkbox.setText("ON")
            self.LoadMRI.cursor.start_cursor(False)
            measurement = Measurement(self.LoadMRI)

            for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, vtk_widget in vtk_widget_image.items():
                    interactor = vtk_widget.GetRenderWindow().GetInteractor()
                    interactor.SetInteractorStyle(None)
                    interactor.SetInteractorStyle(CustomInteractorStyle(self.LoadMRI.cursor, view_name,image_index,measurement))
        else:
            checkbox.setText("OFF")
            self.LoadMRI.cursor.start_cursor(True)

    def on_threshold_changed(self, checked):
        if checked:  # If true, original images not needed
            self.LoadMRI.threshold_on = True
            #Segmentation
            self.LoadMRI.Threshold = ThresholdSegmentation(self.LoadMRI)
            #threshold limits
            self.ui.doubleSpinBox_lower.setValue(self.LoadMRI.Threshold.lower)
            self.ui.ScrollBar_lower.setValue(self.LoadMRI.Threshold.lower)
            self.ui.doubleSpinBox_upper.setValue(self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_upper.setValue(self.LoadMRI.Threshold.upper)
            self.ui.doubleSpinBox_lower.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.ScrollBar_lower.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.doubleSpinBox_upper.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.ScrollBar_upper.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.doubleSpinBox_lower.valueChanged.connect(self.on_spin_changed_lower)
            self.ui.ScrollBar_lower.valueChanged.connect(self.on_scroll_changed_lower)
            self.ui.doubleSpinBox_upper.valueChanged.connect(self.on_spin_changed_upper)
            self.ui.ScrollBar_upper.valueChanged.connect(self.on_scroll_changed_upper)

            #threshold buttons
            self.ui.radioButton_bounded.toggled.connect(
                lambda checked: (setattr(self.LoadMRI.Threshold, 'threshold_mode', 'bounded'), self.update_threshold_display()) if checked else None
            )
            self.ui.radioButton_lower.toggled.connect(
                lambda checked: (setattr(self.LoadMRI.Threshold, 'threshold_mode', 'lower'), self.update_threshold_display()) if checked else None
            )
            self.ui.radioButton_upper.toggled.connect(
                lambda checked: (setattr(self.LoadMRI.Threshold, 'threshold_mode', 'upper'), self.update_threshold_display()) if checked else None
            )

            #threshold ON/OFF
            self.ui.checkBox_threshold.setText("Threshold ON")
            self.update_threshold_display()
            self.intensity_table()
        else:  # If false, original images needed and loaded incase indexes have changed
            self.LoadMRI.threshold_on = False
            self.ui.checkBox_threshold.setText("Threshold OFF")
            for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, widget in vtk_widget_image.items():
                    if view_name in self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx]:
                        renderer = self.LoadMRI.renderers[0][view_name]
                        renderer.RemoveActor(self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx][view_name])
                        del self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx][view_name]
                        widget.GetRenderWindow().Render()

            self.LoadMRI.volume[self.LoadMRI.thres_idx] = {}
            self.LoadMRI.num_data_max -= 1
            ##if more files!!!
            self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx] = {}
            self.intensity_table()
            self.LoadMRI.update_slices(0)

    def paintbrush_function(self, vol_dim:int):
        """
        Set up paintbrush UI elements (size, type, labels, histogram) for segmentation.
        """
        self.LoadMRI.paintbrush.size = 5
        if self.LoadMRI.vol_dim[0] == 3:
            #pushButtons Type of Brush
            self.ui.paint_square.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'square')
            )
            self.ui.paint_round.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'round')
            )
            # Fill combo Label box with color and names
            combo = self.ui.comboBox_activeLabels
            paint_over = self.ui.comboBox_paintOver
        else:
            #Post Surgery
            self.ui.paint_square_Post.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'square')
            )
            self.ui.paint_round_Post.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'round')
            )
            combo = self.ui.comboBox_activeLabels_Post
            paint_over = self.ui.comboBox_paintOver_Post

        #Post Surgery
        self.LoadMRI.brush['size'].setValue(self.LoadMRI.paintbrush.size)
        self.LoadMRI.brush['size'].setRange(1,20)
        self.LoadMRI.brush['size'].valueChanged.connect(self.LoadMRI.paintbrush.set_size)
        self.LoadMRI.brush['size_slider'].setValue(self.LoadMRI.paintbrush.size)
        self.LoadMRI.brush['size_slider'].setRange(1,20)
        self.LoadMRI.brush['size_slider'].valueChanged.connect(self.LoadMRI.paintbrush.set_size)
        #Label Occupancy
        self.LoadMRI.paintbrush.label_occ = 0.3
        self.LoadMRI.brush['label_occ'].setValue(self.LoadMRI.paintbrush.label_occ)
        self.LoadMRI.brush['label_occ'].setRange(0,1)
        self.LoadMRI.brush['label_occ'].valueChanged.connect(self.LoadMRI.paintbrush.set_label_occupancy)
        self.LoadMRI.brush['label_occ_slider'].setValue(self.LoadMRI.paintbrush.label_occ*100)
        self.LoadMRI.brush['label_occ_slider'].setRange(0,100)
        self.LoadMRI.brush['label_occ_slider'].valueChanged.connect(self.LoadMRI.paintbrush.set_label_occupancy)


        # Fill Combobox with Colors
        for i, color_name in enumerate(self.LoadMRI.paintbrush.color_combobox):
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(color_name))
            icon = QIcon(pixmap)
            combo.addItem(icon, self.LoadMRI.paintbrush.labels_combobox[i])
        combo.setIconSize(QSize(20, 20))
        combo.show()
        combo.setCurrentIndex(1) #set red as default

        combo.currentIndexChanged.connect(
            lambda index: setattr(self.LoadMRI.paintbrush, "brush_color", self.LoadMRI.paintbrush.color_combobox[index])
        )

        ## Fill paintover Box with Colors
        for i, color_name in enumerate(self.LoadMRI.paintbrush.color_paintover):
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(color_name))
            icon = QIcon(pixmap)
            paint_over.addItem(icon, self.LoadMRI.paintbrush.labels_paintover[i])
        paint_over.setIconSize(QSize(20, 20))
        paint_over.show()
        paint_over.setCurrentIndex(1) #set clear labels as default

        paint_over.currentIndexChanged.connect(
            lambda index: setattr(self.LoadMRI.paintbrush, "paintover_color", self.LoadMRI.paintbrush.color_paintover[index])
        )

        #if paintbrush is clicked
        self.ui.checkBox_Brush_MRID.stateChanged.connect(self.brush_post_surgery)
        self.ui.checkBox_Brush.stateChanged.connect(self.brush_post_surgery)


        ##Histogram
        self.LoadMRI.paintbrush.widget_histogram = self.ui.widget_histogram

        histo = self.ui.histogram_label
        for i, color_name in enumerate(self.LoadMRI.paintbrush.color_histogram):
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(color_name))
            icon = QIcon(pixmap)
            histo.addItem(icon, self.LoadMRI.paintbrush.labels_histogram[i])
        histo.setIconSize(QSize(20, 20))
        self.ui.widget_histogram.setLabel("left", "Intensity")
        self.ui.widget_histogram.setLabel("bottom", "Number of Voxels")
        histo.show()
        histo.setCurrentIndex(0) #set red as default
        self.ui.histogram_label.currentIndexChanged.connect(
            lambda index: (setattr(self.LoadMRI.paintbrush, "histogram_color", self.LoadMRI.paintbrush.color_histogram[index]),
                           self.LoadMRI.paintbrush.histogram())  # call histogram immediately
        )


    def brush_post_surgery(self,state:bool):
        """Enable or disable the post-surgery paintbrush for MRI tagging. """
        self.LoadMRI.brush_post = state
        if state: #self.ui.checkBox_Brush_MRID.isChecked():
            self.ui.checkBox_Brush_MRID.setText("Brush ON")
            self.LoadMRI.paintbrush.start_paintbrush()
        else:
            self.ui.checkBox_Brush_MRID.setText("Brush OFF")
            #delete brush
            for view_name in 'axial','coronal','sagittal':
                for i in range(self.LoadMRI.num_images):
                    renderer = self.LoadMRI.renderers[i][view_name] ## FOR ALL IMAGES
                    if self.LoadMRI.paintbrush.paint_actors.get(view_name) is not None:
                        renderer.RemoveActor(self.LoadMRI.paintbrush.paint_actors[view_name])
                    self.LoadMRI.vtk_widgets[i][view_name].GetRenderWindow().Render() ## FOR ALL IMAGES
                self.LoadMRI.paintbrush.paint_actors[view_name] = None


    def open_input_dialog(self):
        """Open a dialog to input MRID tags and initialize painting tools."""
        dlg = InputDialog(self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.LoadMRI.tag_file = True
            num_tags, tag_data, num_regions, regions = dlg.get_values()
            self.LoadMRI.mrid_tags = MRID_tags(self.LoadMRI,num_tags, tag_data,num_regions,regions)
            self.LoadMRI.mrid_tags.create_labels()
            self.paintbrush_function(self.vol_dim)
            self.LoadMRI.mrid_tags.generate_textfile()

            self.ui.plainTextEdit_MRID.setPlainText('Please paint the anatomical regions and then save the file! ')
            self.ui.plainTextEdit_MRID.setReadOnly(True)
            self.ui.plainTextEdit_MRID.setStyleSheet("color: red; font-size: 8pt;")

            #Save file
            self.ui.toolButton_ExportFile_Post.clicked.connect(self.LoadMRI.mrid_tags.save_as_niigz)
            self.ui.checkBox_Brush_MRID.setEnabled(True)


    def on_tab3D_changed(self,val):
        if val == 2:
            # Labels
            num_tags = 0
            tag_data = []
            regions = [('Label 1', 1), ('Label 2', 1), ('Label 3', 1),('Label 4', 1), ('Label 5', 1),('Label 6', 1)]
            num_regions = 6
            self.LoadMRI.mrid_tags = MRID_tags(self.LoadMRI,num_tags, tag_data,num_regions,regions)
            self.LoadMRI.mrid_tags.create_labels()

            self.paintbrush_function(self.vol_dim)
            self.brush_post_surgery(True)

    def update_threshold_display(self):
        #update whole threshold display
        if self.LoadMRI.Threshold.threshold_mode == 'bounded':
            self.LoadMRI.th_img = self.LoadMRI.Threshold.smooth_binary_threshold(self.LoadMRI.volume[self.LoadMRI.thres_idx][0], lower=self.LoadMRI.Threshold.lower, upper=self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_lower.setEnabled(True)
            self.ui.doubleSpinBox_lower.setEnabled(True)
            self.ui.ScrollBar_upper.setEnabled(True)
            self.ui.doubleSpinBox_upper.setEnabled(True)
        elif self.LoadMRI.Threshold.threshold_mode == 'lower':
            self.LoadMRI.th_img = self.LoadMRI.Threshold.smooth_binary_threshold(self.LoadMRI.volume[self.LoadMRI.thres_idx][0], lower=self.LoadMRI.Threshold.lower, upper=None)
            self.ui.ScrollBar_lower.setEnabled(True)
            self.ui.doubleSpinBox_lower.setEnabled(True)
            self.ui.ScrollBar_upper.setEnabled(False)
            self.ui.doubleSpinBox_upper.setEnabled(False)
        elif self.LoadMRI.Threshold.threshold_mode == 'upper':
            self.LoadMRI.th_img = self.LoadMRI.Threshold.smooth_binary_threshold(self.LoadMRI.volume[self.LoadMRI.thres_idx][0], lower=None, upper=self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_lower.setEnabled(False)
            self.ui.doubleSpinBox_lower.setEnabled(False)
            self.ui.ScrollBar_upper.setEnabled(True)
            self.ui.doubleSpinBox_upper.setEnabled(True)
        self.LoadMRI.Threshold.only_update_displayed_image()

    def on_spin_changed_lower(self,val):
        self.LoadMRI.Threshold.lower = val
        self.ui.ScrollBar_lower.setValue(self.LoadMRI.Threshold.lower)
        self.check_rangeLow()
        self.update_threshold_display()

    def on_spin_changed_upper(self,val):
        self.LoadMRI.Threshold.upper = val
        self.ui.ScrollBar_upper.setValue(self.LoadMRI.Threshold.upper)
        self.check_rangeUp()
        self.update_threshold_display()

    def on_scroll_changed_lower(self,val):
        self.LoadMRI.Threshold.lower = val
        self.ui.doubleSpinBox_lower.setValue(self.LoadMRI.Threshold.lower)
        self.check_rangeLow()
        self.update_threshold_display()

    def on_scroll_changed_upper(self,val):
        self.LoadMRI.Threshold.upper = val
        self.ui.doubleSpinBox_upper.setValue(self.LoadMRI.Threshold.upper)
        self.check_rangeUp()
        self.update_threshold_display()

    def check_rangeUp(self):
        if self.LoadMRI.Threshold.upper < self.LoadMRI.Threshold.lower:
            self.LoadMRI.Threshold.lower = self.LoadMRI.Threshold.upper
            self.ui.doubleSpinBox_lower.setValue(self.LoadMRI.Threshold.lower)
            self.ui.ScrollBar_lower.setValue(self.LoadMRI.Threshold.lower)

    def check_rangeLow(self):
        if self.LoadMRI.Threshold.lower > self.LoadMRI.Threshold.upper:
            self.LoadMRI.Threshold.upper = self.LoadMRI.Threshold.lower
            self.ui.doubleSpinBox_upper.setValue(self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_upper.setValue(self.LoadMRI.Threshold.upper)


    def intensity_table(self):
        self.ui.tableWidget_images.setColumnWidth(0, 30)
        self.ui.tableWidget_images.setColumnWidth(1, 102)
        self.ui.tableWidget_images.setColumnWidth(2, 60)
        self.ui.tableWidget_images.setColumnWidth(3, 60)

        self.ui.tableWidget_images.setRowCount(self.LoadMRI.num_data_max)
        icon_dir = os.path.join(os.path.dirname(__file__), "Icons/Internet")
        self.icon_visible = QIcon(os.path.join(icon_dir, "eye_open.png"))
        self.icon_hidden = QIcon(os.path.join(icon_dir, "eye_closed.png"))

        self.LoadMRI.cursor.intensity = {}
        for idx in range(self.LoadMRI.num_data_max):
            btn = QToolButton()
            if idx==0:
                btn.setCheckable(False)
            else:
                btn.setCheckable(True)
            btn.setChecked(True)  # visible by default
            btn.setIcon(self.icon_visible)
            btn.setToolTip("Toggle visibility")
            btn.setAutoRaise(True)
            btn.clicked.connect(lambda checked, r=idx, b=btn: self.toggle_visibility(checked,r, b))
            btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                }
                QToolButton:checked {
                    background: transparent;
                }
            """)
            self.ui.tableWidget_images.setCellWidget(idx, 0, btn)

            # Column 1: Layer name
            layer_item = QTableWidgetItem(os.path.basename(self.LoadMRI.file_name[idx]))
            layer_item.setFlags(layer_item.flags() & ~Qt.ItemIsEditable)  # read-only
            self.ui.tableWidget_images.setItem(idx, 1, layer_item)

            # Column 2: Intensity
            intensity_item = QTableWidgetItem(f"{self.LoadMRI.intensity[idx]:.3f}")
            intensity_item.setTextAlignment(Qt.AlignCenter)
            intensity_item.setFlags(intensity_item.flags() & ~Qt.ItemIsEditable)  # read-only
            self.ui.tableWidget_images.setItem(idx, 2, intensity_item)

            self.LoadMRI.cursor.intensity[idx]=[]
            self.LoadMRI.cursor.intensity[idx] = self.ui.tableWidget_images.item(idx, 2)
            self.LoadMRI.cursor_ui[f"intensity{idx}"] = self.ui.tableWidget_images.item(idx, 2)

            # Column 3: Opacity [%]
            self.LoadMRI.opacity = {}
            self.LoadMRI.opacity[idx] = 1
            opacity_spin = QDoubleSpinBox()
            opacity_spin.setRange(0.0, 100.0)          # percentage (0–100)
            opacity_spin.setSingleStep(5.0)
            opacity_spin.setDecimals(1)
            opacity_spin.setValue(self.LoadMRI.opacity[idx] * 100)  # assume stored 0.0–1.0 internally
            opacity_spin.setSuffix(" %")
            opacity_spin.setAlignment(Qt.AlignCenter)
            # Optional styling
            opacity_spin.setToolTip("Adjust layer opacity")
            # Connect to a slot (update VTK actor opacity, for example)
            if idx != 0:
                if hasattr(self.LoadMRI, 'thres_idx') and self.LoadMRI.thres_idx==idx:
                    opacity_spin.setEnabled(False)
                else:
                    opacity_spin.valueChanged.connect(lambda val, i=idx: self.LoadMRI.loadOther.change_opacity(i, val))
            else:
                opacity_spin.setEnabled(False)
            # Place the widget in the table
            self.ui.tableWidget_images.setCellWidget(idx, 3, opacity_spin)
            # Store a reference if you need to access it later
            self.LoadMRI.cursor_ui[f"opacity{idx}"] = opacity_spin


        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.ui.tableWidget_images)
        self.setLayout(layout)
        self.setWindowTitle("Image Layers")

    def toggle_visibility(self,checked,row,btn):
        if row==0: #main images is always visible
            return
        if checked:
            btn.setIcon(self.icon_visible)
            for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, widget in vtk_widget_image.items():
                    if view_name in self.LoadMRI.actors_non_mainimage[row]:
                        self.LoadMRI.actors_non_mainimage[row][view_name].SetVisibility(True)
                        widget.GetRenderWindow().Render()
            if hasattr(self.LoadMRI, 'thres_idx') and self.LoadMRI.thres_idx==row:
                self.LoadMRI.threshold_on = True
        else:
            btn.setIcon(self.icon_hidden)
            for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, widget in vtk_widget_image.items():
                    if view_name in self.LoadMRI.actors_non_mainimage[row]:
                        self.LoadMRI.actors_non_mainimage[row][view_name].SetVisibility(False)
                        widget.GetRenderWindow().Render()
            if hasattr(self.LoadMRI, 'thres_idx') and self.LoadMRI.thres_idx==row:
                    self.LoadMRI.threshold_on = False
            self.LoadMRI.update_slices(0)

    def active_bubbles(self):
        self.ui.stackedWidget.setCurrentIndex(1)
        if self.initialization_first_time:
            #Get radius
            self.LoadMRI.SegInitialization = SegmentationInitialization(self.LoadMRI)
            table = self.ui.tableView_activeBub
            self.LoadMRI.SegInitialization.create_table(table)
            self.LoadMRI.SegInitialization.radius = 2
            self.ui.doubleSpinBox_Bubradius.setValue(self.LoadMRI.SegInitialization.radius)
            self.ui.horizontalSlider_Bubradius.setValue(self.LoadMRI.SegInitialization.radius*100)
            self.ui.doubleSpinBox_Bubradius.setRange(0.01,6)
            self.ui.horizontalSlider_Bubradius.setRange(1,6*100)
            self.ui.doubleSpinBox_Bubradius.valueChanged.connect(lambda val: self.get_bubble_radius('SpinBox',val=val))
            self.ui.horizontalSlider_Bubradius.valueChanged.connect(lambda val: self.get_bubble_radius('Slider',val=val))
            self.ui.pushButton_addBubbles.clicked.connect(lambda val: self.LoadMRI.SegInitialization.draw_bubble(self.ui.pushButton_Next2))
            #info if row in table is selected
            self.ui.tableView_activeBub.selectionModel().selectionChanged.connect(self.LoadMRI.SegInitialization.row_selected)
            #delete bubble
            self.ui.pushButton_delete.clicked.connect(self.delete_bubble)

            self.initialization_first_time = False
        else:
            self.LoadMRI.SegInitialization.table.show()
            #if not self.evolution_first_time:
            #    self.LoadMRI.SegEvolution.update_evolution_initializtion(128)

    def get_bubble_radius(self,mode,val):
        if mode == 'SpinBox':
            self.LoadMRI.SegInitialization.radius = val
            self.ui.horizontalSlider_Bubradius.setEnabled(False)
            self.ui.horizontalSlider_Bubradius.setValue(int(self.LoadMRI.SegInitialization.radius*100))
            self.ui.horizontalSlider_Bubradius.setEnabled(True)
        elif mode == 'Slider':
            self.LoadMRI.SegInitialization.radius = val /100
            self.ui.doubleSpinBox_Bubradius.setEnabled(False)
            self.ui.doubleSpinBox_Bubradius.setValue(self.LoadMRI.SegInitialization.radius)
            self.ui.doubleSpinBox_Bubradius.setEnabled(True)

        if self.LoadMRI.SegInitialization.selected:
            for i in 0,1,2:
                self.LoadMRI.SegInitialization.actor_bubble[self.LoadMRI.SegInitialization.row_index*3+i][3] = self.LoadMRI.SegInitialization.radius
            self.LoadMRI.SegInitialization.update_bubbles_visible()
            self.LoadMRI.SegInitialization.model.setItem(self.LoadMRI.SegInitialization.row_index,3, QStandardItem(str(self.LoadMRI.SegInitialization.radius)))

    def delete_bubble(self):
        for i,[view_name,actor,_,_,_,_] in enumerate(self.LoadMRI.SegInitialization.actor_bubble):
            #remove from renderer
            if int(i/3) == self.LoadMRI.SegInitialization.row_index:
                renderer = self.LoadMRI.renderers[0][view_name]
                renderer.RemoveActor(actor)

                actor_entry = self.LoadMRI.SegInitialization.actor_selected[i]
                renderer.RemoveActor(actor_entry[2])

        #remove from list (3 enteries)
        self.LoadMRI.SegInitialization.actor_bubble.pop(self.LoadMRI.SegInitialization.row_index*3+2)
        self.LoadMRI.SegInitialization.actor_bubble.pop(self.LoadMRI.SegInitialization.row_index*3+1)
        self.LoadMRI.SegInitialization.actor_bubble.pop(self.LoadMRI.SegInitialization.row_index*3)
        self.LoadMRI.SegInitialization.actor_selected.pop(self.LoadMRI.SegInitialization.row_index*3+2)
        self.LoadMRI.SegInitialization.actor_selected.pop(self.LoadMRI.SegInitialization.row_index*3+1)
        self.LoadMRI.SegInitialization.actor_selected.pop(self.LoadMRI.SegInitialization.row_index*3)
        self.LoadMRI.SegInitialization.index -= 1

        #remove from table
        self.ui.tableView_activeBub.selectionModel().selectionChanged.disconnect(self.LoadMRI.SegInitialization.row_selected)
        self.LoadMRI.SegInitialization.model.removeRow(self.LoadMRI.SegInitialization.row_index)
        self.ui.tableView_activeBub.selectionModel().selectionChanged.connect(self.LoadMRI.SegInitialization.row_selected)

        self.LoadMRI.SegInitialization.row_index = min(self.LoadMRI.SegInitialization.row_index, self.LoadMRI.SegInitialization.model.rowCount()-1)

        self.LoadMRI.SegInitialization.update_bubbles_visible()

        for view_name in 'axial','coronal','sagittal':
            self.LoadMRI.renderers[0][view_name].GetRenderWindow().Render()

        if self.LoadMRI.SegInitialization.model.rowCount() == 0:
            self.ui.pushButton_Next2.setEnabled(False)


    #Start segmentation process
    def threshold_seg(self):
        self.ui.stackedWidget.setCurrentIndex(0)
        self.update_threshold_display()

    def evolution(self):
        self.ui.stackedWidget.setCurrentIndex(2)
        #if self.evolution_first_time:
            # SChange button icons: play, pause
        button = self.ui.toolButton_runEvo
        self.LoadMRI.SegEvolution = SegmentationEvolution(self.LoadMRI,self.LoadMRI.SegInitialization,self.LoadMRI.Threshold,button)
        self.ui.toolButton_runEvo.clicked.connect(self.LoadMRI.SegEvolution.initialize_segmentation_itk)
        #    self.evolution_first_time = False
        #else:
        #    self.load_mri.SegEvolution.new_evolution()

    def registration(self):
        self.LoadMRI.Registration = Registration(self.LoadMRI)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
