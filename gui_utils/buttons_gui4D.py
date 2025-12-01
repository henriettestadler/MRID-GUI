# This Python file uses the following encoding: utf-8
import os
from core.mrid_tags import MRID_tags
from core.paintbrush import Paintbrush
from utils.contrast import Contrast
from utils.zoom import Zoom
from utils.minimap_handler import Minimap
from gui_utils.paintbrush_gui import PaintbrushGUI
from utils.mrid_inputdialog import MRID_InputDialog
from PySide6 import QtWidgets
from core.electrode_localization import ElectrodeLoc
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog, QDockWidget,QVBoxLayout
from PySide6.QtCore import Qt
import SimpleITK as sITK


class PopupDialog(QDialog):
    """
        Class for pop/up dialog for advanced manual control adjustment.
    """
    def __init__(self, parent=None, ui_widget=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Control Adjustments")
        layout = QVBoxLayout(self)
        layout.addWidget(ui_widget)

    def closeEvent(self, event):
        # Instead of destroying, just hide the window
        self.hide()
        event.ignore()



class ButtonsGUI_4D:
    """Handles setup of GUI components for 4D MRI data visualization and interaction."""
    def __init__(self,MW, vol_dim,data_index,data_view):
        """
           Initialize the 4D buttons GUI.

           Args:
               MW: The main window instance containing UI and MRI data references.
               vol_dim (int): The number of dimensions of the MRI data (expected 4).
        """
        self.MW = MW
        self.ui = MW.ui
        self.LoadMRI = MW.LoadMRI

        self.vol_dim = vol_dim

        self.buttons_4D(data_index,data_view)



    def buttons_4D(self,data_index,data_view):
        """
        Set up the UI components, VTK widgets, and basic initialization for 4D mode.
        """
        file_name = self.LoadMRI.file_name[data_index]
        target = self.ui.file_name_displayed_4d
        target.setPlainText("File loaded " + data_view.upper() + ": " + os.path.basename(file_name))
        #target.setPlainText(os.path.basename(file_name))
        target.setReadOnly(True)
        target.setStyleSheet("color: green; font-size: 8pt;")

        lm = self.LoadMRI
        lm.vtk_widgets = {}
        lm.vtk_widgets[0] = {
            f"{data_view}": self.ui.vtkWidget_data00,
        }
        lm.vtk_widgets[1] = {
            f"{data_view}": self.ui.vtkWidget_data01,
        }
        lm.vtk_widgets[2] = {
            f"{data_view}": self.ui.vtkWidget_data02,
        }

        #initialize everything
        self.LoadMRI.image_index = 0
        self.initialize_zoom_controls(data_index)
        self.initialize_contrast(data_index,data_view)
        self.initialize_cursor(data_index)
        self.initialize_timestamps(data_index,data_view)
        self.ui.paintbrush_dataview.addItem(data_view)

        self.ui.actionGaussian_Centers.triggered.connect(self.get_gaussian_analysis)
        self.ui.actionGet_Coordinates.triggered.connect(self.electrode_localisation)
        self.ui.actionStart_MRIDlabels.triggered.connect(self.open_input_dialog)
        self.ui.actionContrast_Adjustments.triggered.connect(self.contrast_adjustments)
        self.ui.actionAdd_Another_View.triggered.connect(self.add_other_view)

        layout = self.ui.gridLayout_data0
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 0)



    def add_other_view(self):
        """
        Add second view of the same brain as separate data.
        """

        lm = self.LoadMRI
        """ Open the initial User Dialog when the application starts. """
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
            self.add_other_view()
        else:
            #pop up asking for the view if 4D data used
            image = sITK.ReadImage(file_name)
            volume = sITK.GetArrayFromImage(image)
            if volume.ndim!=4:
                return
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Data view")
            msg_box.setText("Please select the view of your 4D data")
            btn_axial = msg_box.addButton("Axial", QMessageBox.ActionRole)
            btn_coronal = msg_box.addButton("Coronal", QMessageBox.ActionRole)
            btn_sagittal = msg_box.addButton("Sagittal", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
            msg_box.exec()
            if msg_box.clickedButton()==btn_cancel:
                return
            data_view = {btn_axial: "axial", btn_coronal: "coronal", btn_sagittal: "sagittal"}.get(msg_box.clickedButton())
            #add widgets and make them visible
            data_index = len(lm.vtk_widgets[0])
            lm.vtk_widgets[0].update({f"{data_view}": getattr(self.ui, f"vtkWidget_data{data_index}0")})
            lm.vtk_widgets[1].update({f"{data_view}": getattr(self.ui, f"vtkWidget_data{data_index}1")})
            lm.vtk_widgets[2].update({f"{data_view}": getattr(self.ui, f"vtkWidget_data{data_index}2")})
            widget = getattr(self.ui, f"groupBox_data{data_index}")
            widget.setVisible(True)
            heatmap = getattr(self.ui, f"heatmap_data{data_index}")
            heatmap.setVisible(False)
            legend = getattr(self.ui, f"groupbox_legend{data_index}")
            legend.setVisible(False)

            #add filename to title
            current_text = self.ui.file_name_displayed_4d.toPlainText()
            new_text = current_text + "\nFile loaded: " + data_view.upper() + ": " + os.path.basename(file_name)
            self.ui.file_name_displayed_4d.setPlainText(new_text)

            self.LoadMRI.file_name[data_index]= file_name
            self.MW.save_info_of_mainimage(data_view,data_index,file_name)
            self.LoadMRI.cursor.init_widgets(data_index,data_view)
            self.initialize_zoom_controls(data_index)

            box = getattr(self.ui, f"groupBox_data{data_index}")
            layout = box.layout()
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 1)
            layout.setColumnStretch(2, 1)
            layout.setColumnStretch(3, 0)
            box.setTitle(f"View: {data_view.upper()}")
            self.ui.paintbrush_dataview.addItem(data_view)

            self.MW.resize(1600,1000)


    def initialize_contrast(self,data_index,data_view):
        """
        Initialize contrast and brightness controls for multiple image views.
        """
        lm = self.LoadMRI

        lm.contrast_ui_elements[data_index] = {
            "contrast0": getattr(self.ui, f"changeContrast_data{data_index}0"),
            "contrast1": getattr(self.ui, f"changeContrast_data{data_index}1"),
            "contrast2": getattr(self.ui, f"changeContrast_data{data_index}2"),
            "brightness0": getattr(self.ui, f"changeBrightness_data{data_index}0"),
            "brightness1": getattr(self.ui, f"changeBrightness_data{data_index}1"),
            "brightness2": getattr(self.ui, f"changeBrightness_data{data_index}2"),
            "display_level0": getattr(self.ui, f"display_level_data{data_index}0"),
            "display_level1": getattr(self.ui, f"display_level_data{data_index}1"),
            "display_level2": getattr(self.ui, f"display_level_data{data_index}2"),
            "display_window0": getattr(self.ui, f"display_window_data{data_index}0"),
            "display_window1": getattr(self.ui, f"display_window_data{data_index}1"),
            "display_window2": getattr(self.ui, f"display_window_data{data_index}2"),
            "auto0": getattr(self.ui, f"pushButton_auto_data{data_index}0"),
            "auto1": getattr(self.ui, f"pushButton_auto_data{data_index}1"),
            "auto2": getattr(self.ui, f"pushButton_auto_data{data_index}2"),
            "reset0": getattr(self.ui, f"pushButton_reset_data{data_index}0"),
            "reset1": getattr(self.ui, f"pushButton_reset_data{data_index}1"),
            "reset2": getattr(self.ui, f"pushButton_reset_data{data_index}2"),
        }

        # initialize Contrast class (for each data_view once)
        setattr(lm, f"contrastClass_{data_index}", Contrast(lm, data_index))

        self.LoadMRI.contrast_ui_elements[data_index]["brightness0"].valueChanged.connect(
            lambda value: getattr(lm, f"contrastClass_{data_index}").changed_sliders(value, image_index=0) # lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["contrast0"].valueChanged.connect(
            lambda value: getattr(lm, f"contrastClass_{data_index}").changed_sliders(value, image_index=0) # lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["auto0"].clicked.connect(
            lambda: getattr(lm, f"contrastClass_{data_index}").auto(image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["reset0"].clicked.connect(
            lambda: getattr(lm, f"contrastClass_{data_index}").reset(image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["brightness1"].valueChanged.connect(
            lambda value: getattr(lm, f"contrastClass_{data_index}").changed_sliders(value, image_index=1) #  value: lm.contrastClass.changed_sliders(value,image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["contrast1"].valueChanged.connect(
            lambda value: getattr(lm, f"contrastClass_{data_index}").changed_sliders(value, image_index=1) # lm.contrastClass.changed_sliders(value,image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["auto1"].clicked.connect(
            lambda: getattr(lm, f"contrastClass_{data_index}").auto(image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["reset1"].clicked.connect(
            lambda: getattr(lm, f"contrastClass_{data_index}").reset(image_index=1) #lm.contrastClass.reset(image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["brightness2"].valueChanged.connect(
            lambda value: getattr(lm, f"contrastClass_{data_index}").changed_sliders(value, image_index=2) #  lm.contrastClass.changed_sliders(value,image_index=2)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["contrast2"].valueChanged.connect(
            lambda value: getattr(lm, f"contrastClass_{data_index}").changed_sliders(value, image_index=2) #  lm.contrastClass.changed_sliders(value,image_index=2)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["auto2"].clicked.connect(
            lambda: getattr(lm, f"contrastClass_{data_index}").auto(image_index=2) # lm.contrastClass.auto(image_index=2)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["reset2"].clicked.connect(
            lambda: getattr(lm, f"contrastClass_{data_index}").reset(image_index=2)
        )

        self.ui.contrast_data.setItemEnabled(data_index, True)
        self.ui.contrast_data.setItemText(data_index, data_view.upper())

    def initialize_cursor(self,data_index):
        """
        Configure spinboxes and connect cursor/contrast event handlers.
        """
        lm = self.LoadMRI

        if data_index==0:
            lm.cursor_ui = {
                'spin_x0': self.ui.spinBox_x_data0,
                'spin_y0': self.ui.spinBox_y_data0,
                'spin_z0': self.ui.spinBox_z_data0,
                'spin_x1': self.ui.spinBox_x_data1,
                'spin_y1': self.ui.spinBox_y_data1,
                'spin_z1': self.ui.spinBox_z_data1,
                'spin_x2': self.ui.spinBox_x_data2,
                'spin_y2': self.ui.spinBox_y_data2,
                'spin_z2': self.ui.spinBox_z_data2,
                'intensity0': self.ui.tableintensity_data0.item(0, 2), #self.ui.intensity_main_Post,
                'intensity1': self.ui.tableintensity_data1.item(0, 2), #self.ui.intensity_main_Post,
                'intensity2': self.ui.tableintensity_data2.item(0, 2), #self.ui.intensity_main_Post,
                'scroll_0': self.ui.Scroll_data0,
                'scroll_1': self.ui.Scroll_data1,
                'scroll_2': self.ui.Scroll_data2,
            }

        spin_x = lm.cursor_ui[f"spin_x{data_index}"]
        spin_y = lm.cursor_ui[f"spin_y{data_index}"]
        spin_z = lm.cursor_ui[f"spin_z{data_index}"]
        spin_x.setMaximum(lm.volume[data_index][0].shape[2])
        spin_y.setMaximum(lm.volume[data_index][0].shape[1])
        spin_z.setMaximum(lm.volume[data_index][0].shape[0])


    def initialize_paintbrush(self):
        """
        Initialize paintbrush tool controls for MRI segmentation.
        """
        self.LoadMRI.brush = {
            'size': self.ui.brush_size4d,
            'size_slider': self.ui.brush_sizeSlider4d,
            'label_occ': self.ui.doubleSpinBox_labelOcc,
            'label_occ_slider': self.ui.sizeSlider_labelOcc
        }
        #Connect paintbrush for segmentation and MRID-tags
        self.LoadMRI.paintbrush = Paintbrush(self.LoadMRI)


    def initialize_zoom_controls(self, data_index):
        """
        Connect zoom and pan buttons for all widgets.
        """
        lm = self.LoadMRI

        for image_index,views in lm.vtk_widgets.items():
            for idx, (view_name, widget) in enumerate(views.items()):
                if idx!=data_index:
                    continue
                zoom_in_btn = getattr(self.ui, f"zoom_in_data{idx}{image_index}")
                zoom_out_btn = getattr(self.ui, f"zoom_out_data{idx}{image_index}")
                fit_window_btn = getattr(self.ui, f"fit_to_zoom_data{idx}{image_index}")

                zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets, data_index))
                zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets, data_index))

                fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets, data_index))

        # initialize Minimap class
        if data_index==0:
            self.LoadMRI.minimap = Minimap(self.LoadMRI)

        pan_distance = 0.4
        for image_index,views in lm.vtk_widgets.items():
            for idx, (view_name, widget) in enumerate(views.items()):
                if idx!=data_index:
                    continue
                go_down_btn = getattr(self.ui, f"go_down_data{idx}{image_index}")
                go_up_btn = getattr(self.ui, f"go_up_data{idx}{image_index}")
                go_right_btn = getattr(self.ui, f"go_right_data{idx}{image_index}")
                go_left_btn = getattr(self.ui, f"go_left_data{idx}{image_index}")
                go_down_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=0,diff_y=-pan_distance,data_index=data_index))
                go_up_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=0,diff_y=pan_distance,data_index=data_index))
                go_right_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=pan_distance,diff_y=0,data_index=data_index))
                go_left_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=-pan_distance,diff_y=0,data_index=data_index))

    def initialize_timestamps(self,data_index,data_view):
        """
        Set up timestamp controls for navigating through 4D MRI frames.
        """
        for idx in range(3):
            spinbox = getattr(self.ui, f"displaytimestamp_data{data_index}{idx}")
            combobox = getattr(self.ui, f"changetimestamp_data{data_index}{idx}")
            spinbox.setMinimum(0)
            combobox.setMinimum(0)
            max_val = self.LoadMRI.volume4D[0].shape[0] - 1
            spinbox.setMaximum(max_val)
            combobox.setMaximum(max_val)
            spinbox.setValue(idx * 4)
            combobox.setValue(idx * 4)
            spinbox.valueChanged.connect(lambda val, i=idx: self.timestamp4D_changed(val, i, data_index,data_view))
            combobox.valueChanged.connect(lambda val, i=idx: self.timestamp4D_changed(val, i, data_index,data_view))



    def timestamp4D_changed(self,value:int, image_index: int, data_index:int,data_view:str):
        """
            Synchronize timestamp spinboxes, sliders and image titles when changed by the user.

            Args:
                value (int): The current timestamp index.
                image_index (int): Index of the image being updated.
        """
        spinbox = getattr(self.ui, f"displaytimestamp_data{data_index}{image_index}")
        combobox = getattr(self.ui, f"changetimestamp_data{data_index}{image_index}")
        spinbox.blockSignals(True)
        combobox.blockSignals(True)
        spinbox.setValue(value)
        combobox.setValue(value)
        spinbox.blockSignals(False)
        combobox.blockSignals(False)
        self.LoadMRI.timestamp4D_changed(value, image_index,data_index,data_view)

        groupBox = getattr(self.ui, f"groupBox_time{data_index}{image_index}")
        title = f"Timestamp t={value}"
        groupBox.setTitle(title)
        tabBox = getattr(self.ui, f"tabWidget_time{data_index}")
        index = tabBox.currentIndex()
        tabBox.setTabText(index, title)



    def continue_mridtags(self,data_view):
        """
        Continue MRID-tag workflow by saving data and updating GUI navigation.
        """

        if self.ui.stackedWidget_4D.currentIndex() == 1:
            #self.update_zooming()
            self.ui.pushButton_segfile.clicked.connect(self.MW.add_another_file)
            self.ui.stackedWidget_MRIDfiles.setCurrentIndex(1)
            self.LoadMRI.vtk_widgets_legend = {}
            for idx in range(len(self.LoadMRI.vtk_widgets[0])):
                heatmap = getattr(self.ui,f"heatmap_data{idx}")
                heatmap.setVisible(True)
                legend = getattr(self.ui,f"groupbox_legend{idx}")
                legend.setVisible(True)
                data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
                if idx==0:
                    self.LoadMRI.vtk_widgets[3] = {
                        data_view: getattr(self.ui, f"vtkWidget_data{idx}3"),
                    }
                else:
                    self.LoadMRI.vtk_widgets[3].update({
                        data_view: getattr(self.ui, f"vtkWidget_data{idx}3"),
                    })
                self.LoadMRI.vtk_widgets_legend[idx] = getattr(self.ui, f"vtkWidget_legend{idx}")

            self.ui.pushButton_segOK.clicked.connect(self.continue_mridtags)
            #resize

        self.ui.stackedWidget_4D.setCurrentIndex(self.ui.stackedWidget_4D.currentIndex()+1)
        #save each niigz separate
        self.LoadMRI.mrid_tags.save_as_niigz()
        if self.ui.stackedWidget_4D.currentIndex() == 3:
            self.ui.pushButton_ElecLoc.clicked.connect(self.get_gaussian_analysis)




    def open_input_dialog(self):
        """Open a dialog to input MRID tags and initialize painting tools."""
        self.initialize_paintbrush()

        dlg = MRID_InputDialog(self.MW)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.LoadMRI.tag_file = True
            num_tags, tag_data, num_regions, regions = dlg.get_values()
            dock = QDockWidget("Paintbrush", self.MW)
            dock.setWidget(self.ui.groupBox_paintbrush)     # use your existing widget from Designer
            self.MW.addDockWidget(Qt.RightDockWidgetArea, dock)
            self.dock = dock
            if tag_data[0][0] == '' and regions[0][0] == '': #Label.txt was imported
                self.LoadMRI.mrid_tags.heatmap_unsuper= True
                self.ui.checkBox_Brush_MRID.setEnabled(True)
                self.ui.stackedWidget_4D.setCurrentIndex(1)
            else:
                self.LoadMRI.mrid_tags = MRID_tags(self,num_tags, tag_data,num_regions,regions)
                self.LoadMRI.mrid_tags.create_labels()
                self.LoadMRI.PaintbrushGUI = PaintbrushGUI(self.MW,False)
                self.LoadMRI.mrid_tags.generate_textfile()

                #Save file
                self.ui.pushButton_anatOK.clicked.connect(self.continue_mridtags)
                self.ui.checkBox_Brush_MRID.setEnabled(True)
                self.ui.stackedWidget_4D.setCurrentIndex(1)
            #resize for heatmap and dock
            min_w = self.MW.minimumWidth()
            min_h = self.MW.minimumHeight()
            self.MW.setMinimumSize(min_w+400,min_h)
            self.ui.pushButton_anatfile.clicked.connect(self.MW.add_another_file)


    def update_zooming(self):
        """
        Reconfigure zoom and pan controls for updated rendering layout.

        !!! AT THE MOMENT NO ACTIVE PART OF THE GUI!!!
        """
        lm = self.LoadMRI
        #disconnect old buttons
        for image_index,views in lm.vtk_widgets.items():
            for view_name, widget in views.items():
                zoom_in_btn = getattr(self.ui, f"zoom_in_{view_name}_{image_index}")
                zoom_out_btn = getattr(self.ui, f"zoom_out_{view_name}_{image_index}")
                zoom_in_btn.clicked.disconnect()
                zoom_out_btn.clicked.disconnect()
                fit_window_btn = getattr(self.ui, f"fit_to_zoom_{view_name}_{image_index}")
                fit_window_btn.clicked.disconnect()


        #(re-)activate buttons for zooming and panning
        pan_distance = 0.4
        self.ui.go_down_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=0,diff_y=-pan_distance))
        self.ui.go_up_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=0,diff_y=pan_distance))
        self.ui.go_right_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=pan_distance,diff_y=0))
        self.ui.go_left_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=-pan_distance,diff_y=0))

        for image_index,views in lm.vtk_widgets.items():
            for view_name, widget in views.items():
                zoom_in_btn = getattr(self.ui, f"zoom_in_{view_name}_{image_index}")
                zoom_out_btn = getattr(self.ui, f"zoom_out_{view_name}_{image_index}")

                zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets))
                zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets))

                fit_window_btn = getattr(self.ui, f"fit_to_zoom_{view_name}_{image_index}")
                fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets))


    def get_gaussian_analysis(self):
        """
        initialize GUI for Electrode Localisation
            1. Warping and Gaussian Centres Extraction
            2. Final localisation
        """
        if not hasattr(self.LoadMRI,'PaintbrushGUI'):
            dock = QDockWidget("Electrode Localization", self.MW)
            dock.setWidget(self.ui.groupBox_paintbrush)     # use your existing widget from Designer
            self.MW.addDockWidget(Qt.RightDockWidgetArea, dock)
            self.ui.stackedWidget_4D.setCurrentIndex(4)
            self.ui.stackedWidget_MRIDfiles.setVisible(False)
            #resize for heatmap and dock
            min_w = self.MW.minimumWidth()
            min_h = self.MW.minimumHeight()
            self.MW.setMinimumSize(min_w+400,min_h)
        else:
            self.dock.setWindowTitle("Electrode Localization")
        self.ui.groupBox_paintbrush.setTitle("Electrode Localization")

        self.ui.stackedWidget_mrid.setCurrentIndex(1)
        self.ui.groupBox_trans0.setVisible(False)
        self.ui.groupBox_trans1.setVisible(False)
        self.ui.groupBox_trans2.setVisible(False)
        self.transformation_files = {}
        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
            getattr(self.ui,f"groupBox_trans{idx}").setVisible(True)
            getattr(self.ui,f"groupBox_trans{idx}").setTitle(data_view)
            getattr(self.ui,f"pushButton_trans{idx}").clicked.connect(lambda val,i=idx: self.get_transformation_files(val,i))

        self.ui.pushButton_Next.clicked.connect(self.start_localisation)

    def start_localisation(self):
        """
        Warping and Gaussian Centres Extraction
        """
        self.LoadMRI.ElectrodeLoc = ElectrodeLoc(self.LoadMRI)
        self.LoadMRI.ElectrodeLoc.get_gaussian_centers(self.transformation_files)
        self.ui.stackedWidget_4D.setCurrentIndex(self.ui.stackedWidget_4D.currentIndex()+1)
        self.ui.pushButton_Gaussian.clicked.connect(self.electrode_localisation)


    def get_transformation_files(self,val,idx):
        """
        Open FileDialog for User to select transformation matrix files.
        """
        files, _ = QFileDialog.getOpenFileNames(
            None,
            f"Please select all transformation files for selected data_view",
            "",
            "Text files (*.txt)"
        )
        if len(files)==1:
            transformation_files = [os.path.splitext(f)[0] for f in files]
            self.transformation_files[idx] = transformation_files[0]
        elif files:
            self.transformation_files[idx] = [os.path.splitext(f)[0] for f in files]
        text = "The following files were selected:\n" + "\n".join(files)
        textedit = getattr(self.ui, f"textEdit_trans{idx}")
        textedit.setText(text)


    def electrode_localisation(self):
        """
            Final localisation
            Takes the Coordinates and finds the best-fit to the real-life tag geometry.
        """
        self.LoadMRI.vtk_widgets[3] = {}
        if not hasattr(self.LoadMRI,'ElectrodeLoc'):
            self.LoadMRI.ElectrodeLoc = ElectrodeLoc(self.LoadMRI)

        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
            self.LoadMRI.vtk_widgets[3][data_view]= getattr(self.ui,f"vtkWidget_data{idx}3")
            groupBox = getattr(self.ui, f"heatmap_data{idx}") #heatmap_data0
            title = "Electrode Localizations"
            groupBox.setTitle(title)
            groupBox.setVisible(True)
        self.LoadMRI.ElectrodeLoc.getCoordinates()
        self.ui.stackedWidget_4D.setCurrentIndex(self.ui.stackedWidget_4D.currentIndex()+1)
        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
            if idx==0:
                layout = self.ui.gridLayout_data0
            else:
                box = getattr(self.ui, f"groupBox_data{idx}")
                layout = box.layout()
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 1)
            layout.setColumnStretch(2, 1)
            layout.setColumnStretch(3, 1)

    def contrast_adjustments(self):
        """
        Control Adjustment Popup for advanced settings.
        """
        if hasattr(self, "popup") and self.popup.isVisible():
            self.popup.raise_()
            self.popup.activateWindow()
            return
        w = self.ui.ManualContrastAdjustments  # widget inside main UI
        self.popup = PopupDialog(parent=self.MW,ui_widget=w)
        self.popup.resize(300, 300)
        self.popup.show()




