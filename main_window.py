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
        self.Load_MRI = LoadMRI()
        self.Load_MRI.fileLoaded.connect(self.on_file_loaded)

        #File loaded buttons
        self.ui.toolButton_LoadFile.clicked.connect(lambda: self.Load_MRI.load_file(vol_dim=3))
        self.ui.toolButton_LoadFile_Post.clicked.connect(lambda: self.Load_MRI.load_file(vol_dim=4))
        self.Load_MRI.mode = 'cursor'

        # Measurement checkbox
        self.ui.checkBox_measurement.stateChanged.connect(self.measurement_function)


    def on_file_loaded(self, file_name: str, vol_dim: int):
        """
        Callback when an MRI file is successfully loaded.

        Sets up VTK widgets, cursor spinboxes, contrast UI, zoom controls,
        and minimap integration based on the volume dimension.
        """

        # Display laoded file name
        if vol_dim == 3:
            target = self.ui.file_name_displayed
        else:
            target = self.ui.file_name_displayed_Post

        target.setPlainText(os.path.basename(file_name))
        target.setReadOnly(True)
        target.setStyleSheet("color: green; font-size: 8pt;")

        # Connect image to widget and store in LoadMRI
        lm = self.Load_MRI
        if vol_dim ==3:
            lm.vtk_widgets = {
                "axial": self.ui.vtkWidget_axial,
                "coronal": self.ui.vtkWidget_coronal,
                "sagittal": self.ui.vtkWidget_sagittal
            }
            contrast_elements = {
                "contrast": self.ui.changeContrast,
                "brightness": self.ui.changeBrightness,
                "display_level": self.ui.display_level,
                "display_window": self.ui.display_window,
                "auto": self.ui.pushButton_auto,
                "reset": self.ui.pushButton_reset
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
        else:
            lm.vtk_widgets = {
                "axial": self.ui.vtkWidget_axial_Post,
                "coronal": self.ui.vtkWidget_coronal_Post,
                "sagittal": self.ui.vtkWidget_sagittal_Post
            }

            self.ui.spinBox_x_Post.setMaximum(lm.volume.shape[2])
            self.ui.spinBox_y_Post.setMaximum(lm.volume.shape[1])
            self.ui.spinBox_z_Post.setMaximum(lm.volume.shape[0])

            contrast_elements = {
                "contrast": self.ui.changeContrast_Post,
                "brightness": self.ui.changeBrightness_Post,
                "display_level": self.ui.display_level_Post,
                "display_window": self.ui.display_window_Post,
                "auto": self.ui.pushButton_auto_Post,
                "reset": self.ui.pushButton_reset_Post
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

        #Setup zoom controls
        self.setup_zoom_controls()

        # set up corsur with UI
        self.setup_cursor_controls(vol_dim)

        #connect all contrast UI
        lm.contrast_ui_elements = contrast_elements

        #Connect timestamp combobox for 4D volume
        self.ui.comboBox_timestamp.currentIndexChanged.connect(self.Load_MRI.timestamp4D_changed)


    def setup_cursor_controls(self,vol_dim:int):
        """
        Connect spinboxes to cursor coordinate updates.
        """
        lm = self.Load_MRI
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
        lm.spinboxes['x'].setRange(1, lm.volume.shape[2])
        lm.spinboxes['y'].setRange(1, lm.volume.shape[1])
        lm.spinboxes['z'].setRange(1, lm.volume.shape[0])

        # Connect spinboxes to your cursor_coord_changed method
        for axis, spinbox in lm.cursor_ui.items():
            lm.cursor_ui['spin_x'].valueChanged.connect(lambda val, ax=axis: self.Load_MRI.cursor.cursor_coord_changed(ax, val))


    def setup_zoom_controls(self):
        """
        Connect all zoom in/out and fit-to-window buttons for all views.
        """
        lm = self.Load_MRI

        # Loop through the vtk_widgets dict directly
        for view_name, widget in lm.vtk_widgets.items():
            zoom_in_btn = getattr(self.ui, f"zoom_in_{view_name}")
            zoom_out_btn = getattr(self.ui, f"zoom_out_{view_name}")
            zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets))
            zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets))
            zoom_in_btn = getattr(self.ui, f"zoom_in_{view_name}_Post")
            zoom_out_btn = getattr(self.ui, f"zoom_out_{view_name}_Post")
            zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets))
            zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets))
            fit_window_btn = getattr(self.ui, f"fit_to_zoom_{view_name}")
            fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets))
            fit_window_btn = getattr(self.ui, f"fit_to_zoom_{view_name}_Post")
            fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets))

        # initialize Minimap class
        self.Load_MRI.minimap = Minimap(self.Load_MRI)
        zoom_notifier.factorChanged.connect(self.Load_MRI.minimap.create_small_rectangle)


    def measurement_function(self):
        """
        Toggle measurement mode for MRI views.
        """
        checkbox = self.ui.checkBox_measurement
        if checkbox.isChecked():
            checkbox.setText("ON")
            self.Load_MRI.cursor.start_cursor(False)
            measurement = Measurement(self.Load_MRI)

            for view_name, vtk_widget in self.Load_MRI.vtk_widgets.items():
                interactor = vtk_widget.GetRenderWindow().GetInteractor()
                interactor.SetInteractorStyle(None)
                interactor.SetInteractorStyle(CustomInteractorStyle(self.Load_MRI.cursor, view_name,measurement))
        else:
            checkbox.setText("OFF")
            self.Load_MRI.cursor.start_cursor(True)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
