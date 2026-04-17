# This Python file uses the following encoding: utf-8
import os
from core.mrid_tags import MRID_tags
from core.paintbrush import Paintbrush
from utils.contrast import Contrast
from utils.zoom import Zoom
from utils.minimap_handler import Minimap
from gui_utils.paintbrush_gui import PaintbrushGUI
from utils.mrid_inputdialog import MRID_InputDialog, ANAT_InputDialog,TRANSFORM_InputDialog
from PySide6 import QtWidgets
from core.electrode_localization import ElectrodeLoc
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog, QDockWidget,QVBoxLayout,QTableWidgetItem
from PySide6.QtCore import Qt
import SimpleITK as sITK
import numpy as np
from mplwidget import MplWidget
from file_handling.loadimage_into4D import LoadImage4D
from ephys.visualisation3D import Visualisation3D
import time

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
    def __init__(self,MW,data_index,data_view):
        """
           Initialize the 4D buttons GUI.

           Args:
               MW: The main window instance containing UI and MRI data references.
        """
        self.MW = MW
        self.ui = MW.ui
        self.LoadMRI = MW.LoadMRI

        self.buttons_4D(data_index,data_view)



    def buttons_4D(self,data_index,data_view):
        """
        Set up the UI components, VTK widgets, and basic initialization for 4D mode.
        """
        file_name = self.LoadMRI.volumes[data_index].file_path
        target = self.ui.file_name_displayed_4d
        target.setPlainText("File loaded " + data_view.upper() + ": " + os.path.basename(file_name))
        #target.setPlainText(os.path.basename(file_name))
        target.setReadOnly(True)
        target.setStyleSheet("color: white; font-size: 8pt;")

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
        self.ui.actionAddViewImage.triggered.connect(self.add_other_view)

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
            return
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
        lm.contrast[data_index] = Contrast(lm, data_index=0)

        self.LoadMRI.contrast_ui_elements[data_index]["brightness0"].valueChanged.connect(
            lambda value: self.LoadMRI.contrast[data_index].changed_sliders(value, image_index=0) # lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["contrast0"].valueChanged.connect(
            lambda value: self.LoadMRI.contrast[data_index].changed_sliders(value, image_index=0) # lm.contrastClass.changed_sliders(value,image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["auto0"].clicked.connect(
            lambda: self.LoadMRI.contrast[data_index].auto(image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["reset0"].clicked.connect(
            lambda: self.LoadMRI.contrast[data_index].reset(image_index=0)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["brightness1"].valueChanged.connect(
            lambda value: self.LoadMRI.contrast[data_index].changed_sliders(value, image_index=1) #  value: lm.contrastClass.changed_sliders(value,image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["contrast1"].valueChanged.connect(
            lambda value: self.LoadMRI.contrast[data_index].changed_sliders(value, image_index=1) # lm.contrastClass.changed_sliders(value,image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["auto1"].clicked.connect(
            lambda: self.LoadMRI.contrast[data_index].auto(image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["reset1"].clicked.connect(
            lambda: self.LoadMRI.contrast[data_index].reset(image_index=1) #lm.contrastClass.reset(image_index=1)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["brightness2"].valueChanged.connect(
            lambda value: self.LoadMRI.contrast[data_index].changed_sliders(value, image_index=2) #  lm.contrastClass.changed_sliders(value,image_index=2)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["contrast2"].valueChanged.connect(
            lambda value: self.LoadMRI.contrast[data_index].changed_sliders(value, image_index=2) #  lm.contrastClass.changed_sliders(value,image_index=2)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["auto2"].clicked.connect(
            lambda: self.LoadMRI.contrast[data_index].auto(image_index=2) # lm.contrastClass.auto(image_index=2)
        )
        self.LoadMRI.contrast_ui_elements[data_index]["reset2"].clicked.connect(
            lambda: self.LoadMRI.contrast[data_index].reset(image_index=2)
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
                'intensity0': self.ui.tableintensity_data0.item(0, 2),
                'intensity1': self.ui.tableintensity_data1.item(0, 2),
                'intensity2': self.ui.tableintensity_data2.item(0, 2),
                'scroll_0': self.ui.Scroll_data0,
                'scroll_1': self.ui.Scroll_data1,
                'scroll_2': self.ui.Scroll_data2,
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
            max_val = self.LoadMRI.volumes[data_index].array_4d.shape[0] - 1
            spinbox.setMaximum(max_val)
            combobox.setMaximum(max_val)
            spinbox.setValue(idx * 4)
            combobox.setValue(idx * 4)
            spinbox.valueChanged.connect(lambda val, i=idx: self.timestamp4D_changed(val, i, data_index,data_view))
            combobox.valueChanged.connect(lambda val, i=idx: self.timestamp4D_changed(val, i, data_index,data_view))

            groupBox = getattr(self.ui, f"groupBox_time{data_index}{idx}")
            title = f"Timestamp t={self.LoadMRI.volumes[data_index].timestamp4D[idx]}"
            groupBox.setTitle(title)
            tabBox = getattr(self.ui, f"tabWidget_time{data_index}")
            tabBox.setTabText(idx, title)




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
        if self.ui.stackedWidget_4D.currentIndex() == 0:
            # create a dock widget
            self.ui.groupBox_progressGUI.setVisible(True)

            self.ui.textEdit_progress.setPlainText("Creating unsupervised Heatmap...")
            self.LoadMRI.mrid_tags.progress = self.ui.progressBar
            self.LoadMRI.mrid_tags.progress.setValue(10)

            self.LoadMRI.vtk_widgets_legend = {}
            for idx in range(len(self.LoadMRI.vtk_widgets[0])):
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
            self.LoadMRI.mrid_tags.heatmap_unsuper = True
            self.ui.pushButton_segOK.clicked.connect(self.continue_mridtags)
            self.LoadMRI.PaintbrushGUI.activate_labels('segmentation')
            self.LoadMRI.mrid_tags.progress.setValue(30)
        else:
            self.LoadMRI.mrid_tags.heatmap_unsuper = False

        #save each niigz separate
        self.LoadMRI.mrid_tags.save_as_niigz()

        if self.ui.stackedWidget_4D.currentIndex() == 0:
            for idx in range(len(self.LoadMRI.vtk_widgets[0])):
                heatmap = getattr(self.ui,f"heatmap_data{idx}")
                heatmap.setVisible(True)
                legend = getattr(self.ui,f"groupbox_legend{idx}")
                legend.setVisible(True)

            self.ui.groupBox_progressGUI.setVisible(False)
            dlg_anat = ANAT_InputDialog(self.MW,1)
            if dlg_anat.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                filename_seg = dlg_anat.get_values()
                for i in range(len(filename_seg)):
                    if filename_seg[i][0] is not None:
                        file_name = filename_seg[i][0]
                        data_view = filename_seg[i][1]
                        if not  hasattr(self.LoadMRI,"LoadImage4D"):
                            self.LoadMRI.LoadImage4D = LoadImage4D(self, file_name)
                        self.LoadMRI.mrid_tags.file_name[i] = self.LoadMRI.volumes[i].file_path[:-7]
                        vol = self.LoadMRI.LoadImage4D.open_file(file_name,data_view)
                        if vol is not None:
                            #add to intensity table
                            keys = list(self.LoadMRI.vtk_widgets[0].keys())
                            idx = keys.index(data_view)
                            tabclass = self.LoadMRI.intensity_table[idx]
                            tabclass.update_table(os.path.basename(file_name), vol,idx)
                            self.ui.contrast_data.setItemEnabled(idx, False)
                        self.LoadMRI.mrid_tags.heatmap_unsuper = False
                        print('HIER DEN HEATMAP VERLINKEN', flush=True)
                        #directly generating supervised heatmap!
                        roi_indices = np.unique(vol)
                        self.LoadMRI.mrid_tags.update_heatmap(data_view,idx,roi_indices)

        if self.ui.stackedWidget_4D.currentIndex() == 0:
            self.LoadMRI.PaintbrushGUI.brush_4D(True,label=False)

        if self.ui.stackedWidget_4D.currentIndex() == 1:
            self.LoadMRI.PaintbrushGUI.brush_4D(False,label=False) #cursor on
            #close all paintbrush tings
            self.dock.close()
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Heatmap Generation Finsihed")
            msg_box.setText('MRID tags and anatomical regions were successfully identified. Segmentation, Anat and heatmap files were saved. \n Press START if you want to start with the Electrode Localization. \n Press Cancel to not directly start it. You can later do this through the Menu 4D Tools/Electrode Localization.')
            msg_box.addButton("START", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
            msg_box.exec()
            if msg_box.clickedButton()==btn_cancel:
                return
            self.get_gaussian_analysis()

        self.ui.stackedWidget_4D.setCurrentIndex(self.ui.stackedWidget_4D.currentIndex()+1)


    def open_input_dialog(self):
        """Open a dialog to input MRID tags and initialize painting tools."""
        self.initialize_paintbrush()

        dlg = MRID_InputDialog(self.MW)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            dlg_anat = ANAT_InputDialog(self.MW,0)
            if dlg_anat.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                num_tags, tag_data, num_regions, regions = dlg.get_values()
                filename_anat = dlg_anat.get_values()
                self.LoadMRI.tag_file = True

                # give the dock a unique object name
                dock_name = "dock_paintbrush4d"

                # check if it exists already
                dock = self.MW.findChild(QDockWidget, dock_name)
                if dock is None:
                    dock = QDockWidget("Paintbrush", self.MW)
                    dock.setObjectName(dock_name)
                    dock.setWidget(self.ui.groupBox_paintbrush)
                    self.MW.addDockWidget(Qt.BottomDockWidgetArea, dock)
                    dock.visibilityChanged.connect(lambda visible: setattr(self.LoadMRI, 'brush_on', False) if not visible else None)
                    self.dock = dock
                    if tag_data[0][0] == '' and regions[0][0] == '': #Label.txt was imported
                        self.ui.checkBox_Brush_MRID.setEnabled(True)
                        self.ui.stackedWidget_4D.setCurrentIndex(0)
                    else:
                        self.LoadMRI.mrid_tags = MRID_tags(self, tag_data,num_regions,regions)
                        self.LoadMRI.mrid_tags.create_labels()
                        self.LoadMRI.mrid_tags.generate_textfile()

                        #Save file
                        self.ui.pushButton_anatOK.clicked.connect(self.continue_mridtags)
                        self.ui.checkBox_Brush_MRID.setEnabled(True)
                        self.ui.stackedWidget_4D.setCurrentIndex(0)
                else:
                    dock.show()
                    dock.raise_()

                if len(filename_anat)>0:
                    self.LoadMRI.PaintbrushGUI = PaintbrushGUI(self.MW,True,label=False)
                else:
                    self.LoadMRI.PaintbrushGUI = PaintbrushGUI(self.MW,True,label=True)

                for i in range(len(filename_anat)):
                    if filename_anat[i][0] is not None:
                        file_name = filename_anat[i][0]
                        data_view = filename_anat[i][1]
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


    def update_zooming(self):
        """
        Reconfigure zoom and pan controls for updated rendering layout.

        !!! AT THE MOMENT NO ACTIVE PART OF THE GUI!!!
        """
        lm = self.LoadMRI
        #disconnect old buttons
        for image_index,views in lm.vtk_widgets.items():
            for idx, (view_name, widget) in enumerate(views.items()):
                zoom_in_btn = getattr(self.ui, f"zoom_in_data{idx}{image_index}")
                zoom_out_btn = getattr(self.ui, f"zoom_out_data{idx}{image_index}")
                zoom_in_btn.clicked.disconnect()
                zoom_out_btn.clicked.disconnect()
                fit_window_btn = getattr(self.ui, f"fit_to_zoom_data{idx}{image_index}")
                fit_window_btn.clicked.disconnect()


        #(re-)activate buttons for zooming and panning
        pan_distance = 0.4
        self.ui.go_down_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=0,diff_y=-pan_distance))
        self.ui.go_up_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=0,diff_y=pan_distance))
        self.ui.go_right_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=pan_distance,diff_y=0))
        self.ui.go_left_image4.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name='axial',diff_x=-pan_distance,diff_y=0))

        for image_index,views in lm.vtk_widgets.items():
            for idx, (view_name, widget) in enumerate(views.items()):
                if image_index!=3:
                    continue
                go_down_btn = getattr(self.ui, f"go_down_data{idx}{image_index}")
                go_up_btn = getattr(self.ui, f"go_up_data{idx}{image_index}")
                go_right_btn = getattr(self.ui, f"go_right_data{idx}{image_index}")
                go_left_btn = getattr(self.ui, f"go_left_data{idx}{image_index}")
                go_down_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=0,diff_y=-pan_distance,data_index=idx))
                go_up_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=0,diff_y=pan_distance,data_index=idx))
                go_right_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=pan_distance,diff_y=0,data_index=idx))
                go_left_btn.clicked.connect(lambda: self.LoadMRI.minimap.pan_arrows(view_name=view_name,diff_x=-pan_distance,diff_y=0,data_index=idx))

        for image_index,views in lm.vtk_widgets.items():
            for view_name, widget in views.items():
                zoom_in_btn = getattr(self.ui, f"zoom_in_data{idx}{image_index}")
                zoom_out_btn = getattr(self.ui, f"zoom_out_data{idx}{image_index}")
                zoom_in_btn.clicked.connect(lambda: Zoom.zoom(1.2, lm.scale_bar, lm.vtk_widgets))
                zoom_out_btn.clicked.connect(lambda: Zoom.zoom(0.8, lm.scale_bar, lm.vtk_widgets))
                fit_window_btn = getattr(self.ui, f"fit_to_zoom_data{idx}{image_index}")
                fit_window_btn.clicked.connect(lambda _, w=widget: Zoom.fit_to_window(w, lm.vtk_widgets.values(), lm.scale_bar, lm.vtk_widgets))


    def get_gaussian_analysis(self):
        """
        initialize GUI for Electrode Localisation
            1. Warping and Gaussian Centres Extraction
            2. Final localisation
        """
        dlg_transform = TRANSFORM_InputDialog(self.MW)
        if dlg_transform.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.transformation_files = dlg_transform.get_values()
            self.LoadMRI.ElectrodeLoc = ElectrodeLoc(self.LoadMRI,self.MW)

            self.ui.groupBox_progressGUI.setVisible(True)
            self.LoadMRI.ElectrodeLoc.groupBox_progressGUI = self.ui.groupBox_progressGUI
            self.ui.textEdit_progress.setPlainText("Finding Gaussian Centers...")
            self.LoadMRI.ElectrodeLoc.progress = self.ui.progressBar
            self.LoadMRI.ElectrodeLoc.progress.setValue(10)

            self.LoadMRI.ElectrodeLoc.get_gaussian_centers(self.transformation_files)
            #dock.close()
            #POPUP
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Electrode Localization")
            msg_box.setText("All Files warped and Gaussian Centers Warped. \n Press CONTINUE to receive final Electrode Localization.")
            msg_box.addButton("CONTINUE", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("Cancel", QMessageBox.ActionRole)
            msg_box.exec()
            if msg_box.clickedButton()==btn_cancel:
                self.LoadMRI.ElectrodeLoc.groupBox_progressGUI.setVisible(False)
                return

            self.electrode_localisation()


    def electrode_localisation(self):
        """
            Final localisation
            Takes the Coordinates and finds the best-fit to the real-life tag geometry.
        """
        self.LoadMRI.vtk_widgets[3] = {}

        if not hasattr(self.LoadMRI,'ElectrodeLoc'):
            self.LoadMRI.ElectrodeLoc = ElectrodeLoc(self.LoadMRI,self.MW)

        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
            self.LoadMRI.vtk_widgets[3][data_view]= getattr(self.ui,f"vtkWidget_data{idx}3")

        self.LoadMRI.ElectrodeLoc.groupBox_progressGUI = self.ui.groupBox_progressGUI
        self.ui.textEdit_progress.setPlainText("Finding Final Localisation. Might take a few minutes...")
        self.LoadMRI.ElectrodeLoc.progress = self.ui.progressBar
        self.LoadMRI.ElectrodeLoc.progress.setValue(10)

        start = time.time()
        result = self.LoadMRI.ElectrodeLoc.getCoordinates()
        end = time.time()
        print(f"Elapsed: {end - start:.4f} seconds",flush=True)

        if result is None:
            return
        else:
            roi_names,self.totaldf,self.totalbarcode_r,self.totalbarcode_d,self.totalmrid, self.totalCA1,self.totaldwi1Dsignal,self.totalregionNames,self.totalpyrChIdx,self.fitted_points,self.chMap,self.totalatlasCoordinates_pkl = result

        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            getattr(self.ui, f"groupBox_time{idx}1").setVisible(False)
            getattr(self.ui, f"groupBox_time{idx}2").setVisible(False)
            getattr(self.ui, f"heatmap_data{idx}").setVisible(False) #heatmap_data0
            getattr(self.ui, f"groupbox_legend{idx}").setVisible(False)
            getattr(self.ui, f"tabWidget_time{idx}").setCurrentIndex(0)
            getattr(self.ui, f"tabWidget_time{idx}").tabBar().setVisible(False)
            getattr(self.ui, f"gridLayout_data{idx}").addWidget(getattr(self.ui, f"groupBox_time{idx}0"), 0, 0, 1, 3)

        self.ui.stackedWidget_4D.setCurrentIndex(self.ui.stackedWidget_4D.currentIndex()+1)

        self.ui.groupBox_barcode.setVisible(True)#
        #save barcode figures
        for index, (i) in enumerate(self.totalmrid):
            #fill combobox
            self.ui.comboBox_mridBarcodes.addItem(str(i))
            barcode_r = self.totalbarcode_r[index]
            barcode_d = self.totalbarcode_d[index]
            mrid_tag = self.totalmrid[index]

            # detected barcode
            plot_d = MplWidget()
            plot_d.canvas.figure.clear()
            [barcode_design, ticks2, tickLabels2] = barcode_d
            # Create an axes object
            ax1 = plot_d.canvas.figure.add_subplot(111)
            ax1.imshow(barcode_design, cmap='gray')
            ax1.set_xticks(ticks2)
            ax1.set_xticklabels(tickLabels2,rotation=45)
            ax1.tick_params(axis='x', labelbottom=True)
            y_max = barcode_design.max()
            #ax1.set_yticks(range(0, int(y_max), 200))
            #print(y_max)
            ax1.figure.subplots_adjust(bottom=0.25)
            ax1.tick_params(axis='both', labelsize=8)
            # Refresh the canvas
            plot_d.canvas.draw()

            save_path = os.path.join(self.LoadMRI.session_path, 'analysed',mrid_tag)
            figname = "mrid_barcode-detected.pdf"
            plot_d.canvas.figure.savefig(os.path.join(save_path, figname),bbox_inches="tight",pad_inches=0.1)

            # reconstructed barcode
            plot_r = MplWidget()
            plot_r.canvas.figure.clear()
            [barcode_reconstructed, ticks, tickLabels] = barcode_r
            # Create an axes object
            ax1 = plot_r.canvas.figure.add_subplot(111)
            ax1.imshow(barcode_reconstructed, cmap='gray')
            ax1.set_xticks(ticks)
            ax1.set_xticklabels(tickLabels,rotation=45)
            #ax1.tight_layout()
            ax1.tick_params(axis='x', labelbottom=True)
            y_max = barcode_reconstructed.max()
            #ax1.set_yticks(range(0, int(y_max), 200))
            #print(y_max)
            ax1.figure.subplots_adjust(bottom=0.25)
            ax1.tick_params(axis='both', labelsize=8)
            # Refresh the canvas
            plot_r.canvas.draw()

            figname = "mrid_barcode-reconstructed.pdf"
            plot_r.canvas.figure.savefig(os.path.join(save_path, figname),bbox_inches="tight",pad_inches=0.1)

        #fill table and plot barcodes
        self.ca1_popup = None
        self.fill_table_and_plots(0)

        self.ui.comboBox_mridBarcodes.currentIndexChanged.connect(lambda index: self.fill_table_and_plots(index))

        self.ui.groupBox_progressGUI.setVisible(False)


    def fill_table_and_plots(self,index):
        #fill table and plot barcodes

        df = self.totaldf[index]
        barcode_r = self.totalbarcode_r[index]
        barcode_d = self.totalbarcode_d[index]
        #mrid_tag = self.totalmrid[index]


        table = self.ui.tableWidget_barcode
        mrid = df["mrid"]
        probabilities = df["probabilities"]
        similarities = df["similarities"]
        for i in range(len(mrid)):
            intensity_item = QTableWidgetItem(f"{probabilities[i]:.3e}")
            intensity_item.setFlags(intensity_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(0,i, intensity_item)
            intensity_item = QTableWidgetItem(f"{similarities[i]:.5f}")
            intensity_item.setFlags(intensity_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(1,i, intensity_item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()

        # detected barcode
        [barcode_design, ticks2, tickLabels2] = barcode_d
        self.ui.widget_barcode_detected.canvas.figure.clear()
        # Create an axes object
        ax1 = self.ui.widget_barcode_detected.canvas.figure.add_subplot(111)
        ax1.imshow(barcode_design, cmap='gray')
        ax1.set_xticks(ticks2)
        ax1.set_xticklabels(tickLabels2,rotation=45)
        ax1.tick_params(axis='x', labelbottom=True)
        y_max = barcode_design.max()
        #ax1.set_yticks(range(0, int(y_max), 200))
        #print(y_max)
        ax1.figure.subplots_adjust(bottom=0.25)
        ax1.tick_params(axis='both', labelsize=9)
        # Refresh the canvas
        self.ui.widget_barcode_detected.canvas.draw()

        #save_path = os.path.join(self.LoadMRI.session_path, 'analysed',mrid_tag)
        #figname = "mrid_barcode-detected.pdf"
        #self.ui.widget_barcode_detected.canvas.figure.savefig(os.path.join(save_path, figname),bbox_inches="tight",pad_inches=0.1)

        # reconstructed barcode
        [barcode_reconstructed, ticks, tickLabels] = barcode_r
        self.ui.widget_barcode_reconstructed.canvas.figure.clear()
        # Create an axes object
        ax1 = self.ui.widget_barcode_reconstructed.canvas.figure.add_subplot(111)
        ax1.imshow(barcode_reconstructed, cmap='gray')
        ax1.set_xticks(ticks)
        ax1.set_xticklabels(tickLabels,rotation=45)
        #ax1.tight_layout()
        ax1.tick_params(axis='x', labelbottom=True)
        y_max = barcode_reconstructed.max()
        #ax1.set_yticks(range(0, int(y_max), 200))
        #print(y_max)
        ax1.figure.subplots_adjust(bottom=0.25)
        ax1.tick_params(axis='both', labelsize=9)
        # Refresh the canvas
        self.ui.widget_barcode_reconstructed.canvas.draw()

        #figname = "mrid_barcode-reconstructed.pdf"
        #self.ui.widget_barcode_reconstructed.canvas.figure.savefig(os.path.join(save_path, figname),bbox_inches="tight",pad_inches=0.1)

        if self.ca1_popup is not None:
            self.ca1_popup.close()

        if self.totalCA1[index]:
            self.ui.ca1_signal_widget.canvas.figure.clear()
            #self.ca1_popup = self.ui.ca1_signal_widget #PlotPopup(self.ui.centralwidget, title="CA1 Signal")
            self.ui.ca1_signal_widget.fig.clear()
            ax1 = self.ui.ca1_signal_widget.fig.add_subplot(111)

            #popup = PlotPopup(self.MW, title="CA1 Signal")
            #ax1 = self.ca1_popup.fig.add_subplot(111)
            dwi1Dsignal = self.totaldwi1Dsignal[index]
            regionNames = self.totalregionNames[index]
            num_channels = dwi1Dsignal.shape[0]
            #self.ui.groupbox_CA1.setVisible(True)
            pixelValues = dwi1Dsignal
            pixelValues = (pixelValues - np.min(pixelValues)) / (np.max(pixelValues) - np.min(pixelValues))
            #plot = MplWidget()
            #self.ui.widget_CA1.canvas.figure.clear()
            #ax1 = self.ui.widget_CA1.canvas.figure.add_subplot(111)
            region_to_color = self.ui.ca1_signal_widget.get_region_colors(regionNames)
            # Plot line segments with color depending on region
            for i in range(len(pixelValues) - 1):
                region = regionNames[i]
                ax1.plot([i, i + 1], [pixelValues[i], pixelValues[i + 1]],
                         color=region_to_color[region], linewidth=2)

            # Optional: Add legend
            unique_regions = list(set(regionNames))
            for region in unique_regions:
                ax1.plot([], [], color=region_to_color[region], label=region)

            #ax1.axvline(x=dwi1Dsignal, color='red', linestyle='--', linewidth=2, label='Pyramidal Layer')
            ax1.axvline(x=self.totalpyrChIdx[index], color='red', linestyle='--', linewidth=2, label='Pyramidal Layer')
            ax1.set_xticks(np.linspace(0, num_channels - 1, num_channels))
            ax1.set_xticklabels(self.chMap[index])
            ax1.legend(title="Anatomical Region",fontsize=7)
            ax1.set_xlabel("Channel Index")
            ax1.set_ylabel("Pixel Value")
            ax1.set_title("Pixel Values by Region")
            ax1.tick_params(axis='both', labelsize=7)
            ax1.grid(True)
            self.ui.ca1_signal_widget.canvas.draw()

        if hasattr(self.LoadMRI,'Visualisation3D'):
            self.LoadMRI.Visualisation3D.index = index
            self.session_path = self.LoadMRI.session_path
            #table and combobox
            index = self.LoadMRI.Visualisation3D.comboBox_mrid.findText(self.totalmrid[index])
            if index != -1:
                self.LoadMRI.Visualisation3D.comboBox_mrid.setCurrentIndex(index)
            del self.LoadMRI.Visualisation3D.chMap
            #self.LoadMRI.Visualisation3D.delete_volumes(self.totalmrid[index],0, 0) #new_label_idx?
            self.LoadMRI.Visualisation3D.index = index
            self.LoadMRI.Visualisation3D.spinbox.blockSignals(True)
            self.LoadMRI.Visualisation3D.initialize_mridTag(self.totalmrid[index],chMap=self.chMap[index])
            self.LoadMRI.Visualisation3D.spinbox.blockSignals(False)

            self.LoadMRI.Visualisation3D.manually_pick_point(point=[],idx=self.chMap[index][0])
            self.LoadMRI.Visualisation3D.plotter.enable_parallel_projection()
        else:
            self.mrid_index = index
            self.LoadMRI.Visualisation3D = Visualisation3D(self.LoadMRI.session_path,self.MW,electrode_localisation=True)
            self.LoadMRI.Visualisation3D.index = index
            self.LoadMRI.Visualisation3D.initialize_mridTag(self.totalmrid[index],chMap=self.chMap[index])

        self.LoadMRI.ElectrodeLoc.add_point(self.fitted_points[index])


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
