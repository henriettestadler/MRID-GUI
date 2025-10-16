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
        self.ui.toolButton_LoadFile.clicked.connect(lambda: self.LoadMRI.load_file(vol_dim=3))
        self.ui.toolButton_LoadFile_Post.clicked.connect(lambda: self.LoadMRI.load_file(vol_dim=4))
        #self.LoadMRI.mode = 'cursor'

        # Measurement checkbox
        self.ui.checkBox_measurement.stateChanged.connect(self.measurement_function)

        #Change of tab to rerender windows
        self.ui.tabWidget.currentChanged.connect(lambda index: self.on_tab_changed(index))
        self.LoadMRI.load_file(self.LoadMRI.vol_dim)

        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

        # Input for MRID tags
        self.ui.pushButton_MRIDtags.clicked.connect(self.open_input_dialog)



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

    def on_file_loaded(self, file_name: str, vol_dim: int):
        """
        Callback when an MRI file is successfully loaded.

        Sets up VTK widgets, cursor spinboxes, contrast UI, zoom controls,
        and minimap integration based on the volume dimension.
        """

        self.vol_dim = vol_dim
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
        if self.vol_dim  ==3:
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
                'intensity': self.ui.intensity_main,
                'scroll_x': self.ui.Scroll_sagittal,
                'scroll_y': self.ui.Scroll_coronal,
                'scroll_z': self.ui.Scroll_axial
            }
            lm.brush = {
                'size': self.ui.brush_size,
                'size_slider': self.ui.brush_sizeSlider
            }
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

            self.ui.spinBox_x_Post.setMaximum(lm.volume[0].shape[2])
            self.ui.spinBox_y_Post.setMaximum(lm.volume[0].shape[1])
            self.ui.spinBox_z_Post.setMaximum(lm.volume[0].shape[0])

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
                'intensity': self.ui.intensity_main_Post,
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
        self.setup_cursor_controls(vol_dim)

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
        if vol_dim == 4:
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
        lm.spinboxes['x'].setRange(1, lm.volume[0].shape[2])
        lm.spinboxes['y'].setRange(1, lm.volume[0].shape[1])
        lm.spinboxes['z'].setRange(1, lm.volume[0].shape[0])

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

        for idx in range(1, 5):
            for direction in ['up', 'down', 'left', 'right']:
                btn = getattr(self.ui, f"go_{direction}_image{idx}")
                btn.clicked.connect(lambda _, i=idx, d=direction: self.LoadMRI.minimap.create_small_rectangle(vn='axial',
                                                new_x=self.LoadMRI.rect_old_x + (0.025 if d=='right' else -0.025 if d=='left' else 0),
                                                new_y=self.LoadMRI.rect_old_y + (0.025 if d=='up' else -0.025 if d=='down' else 0)))
        for vn in 'axial','coronal','sagittal':
            for direction in ['up', 'down', 'left', 'right']:
                btn = getattr(self.ui, f"go_{direction}_{vn}")
                btn.clicked.connect(lambda _, i=idx, d=direction: self.LoadMRI.minimap.create_small_rectangle(vn='axial',
                                                new_x=self.LoadMRI.rect_old_x + (0.025 if d=='right' else -0.025 if d=='left' else 0),
                                                new_y=self.LoadMRI.rect_old_y + (0.025 if d=='up' else -0.025 if d=='down' else 0)))


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


    def paintbrush_function(self, vol_dim:int):
        """
        Set up paintbrush UI elements (size, type, labels, histogram) for segmentation.
        """
        self.LoadMRI.paintbrush.size = 5
        if self.LoadMRI.vol_dim == 3:
            self.ui.brush_size.setValue(self.LoadMRI.paintbrush.size)
            self.ui.brush_size.setRange(0,40)
            self.ui.brush_size.valueChanged.connect(self.LoadMRI.paintbrush.set_size)
            self.ui.brush_sizeSlider.setValue(self.LoadMRI.paintbrush.size)
            self.ui.brush_sizeSlider.setRange(0,40)
            self.ui.brush_sizeSlider.valueChanged.connect(self.LoadMRI.paintbrush.set_size)
            #pushButtons Type of Brush
            self.ui.paint_square.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'square')
            )
            self.ui.paint_round.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'round')
            )
            self.ui.paint_adjusted.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'adjusted')
            )
            # Fill combo Label box with color and names
            combo = self.ui.comboBox_activeLabels
            paint_over = self.ui.comboBox_paintOver
        else:
            #Post Surgery
            self.LoadMRI.brush['size'].setValue(self.LoadMRI.paintbrush.size)
            self.LoadMRI.brush['size'].setRange(1,20)
            self.LoadMRI.brush['size'].valueChanged.connect(self.LoadMRI.paintbrush.set_size)
            self.LoadMRI.brush['size_slider'].setValue(self.LoadMRI.paintbrush.size)
            self.LoadMRI.brush['size_slider'].setRange(1,20)
            self.LoadMRI.brush['size_slider'].valueChanged.connect(self.LoadMRI.paintbrush.set_size)
            #Post Surgery
            self.ui.paint_square_Post.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'square')
            )
            self.ui.paint_round_Post.clicked.connect(
                lambda checked=False: setattr(self.LoadMRI.paintbrush, 'brush_type', 'round')
            )
            combo = self.ui.comboBox_activeLabels_Post
            paint_over = self.ui.comboBox_paintOver_Post
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

        #if paintbrush is clicked in postsurgery
        self.ui.checkBox_Brush_MRID.stateChanged.connect(self.brush_post_surgery)


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
        if self.ui.checkBox_Brush_MRID.isChecked():
            self.ui.checkBox_Brush_MRID.setText("Brush ON")
            self.LoadMRI.paintbrush.start_paintbrush()
        else:
            self.ui.checkBox_Brush_MRID.setText("Brush OFF")


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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
