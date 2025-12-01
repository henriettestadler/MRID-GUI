# This Python file uses the following encoding: utf-8
import os
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QTableWidgetItem, QToolButton, QDoubleSpinBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu
from vtk.util import numpy_support
import numpy as np
import SimpleITK as sITK
from PySide6.QtWidgets import QFileDialog
from PySide6 import QtWidgets

class IntensityTable:
    """GUI table for managing and visualizing MRI image layers with VTK integration."""
    def __init__(self, MW,data_index,table,vol):
        """
            Initialize the IntensityTable for the given main data_index.

            Args:
                MW: The main application window containing UI and MRI data references.
        """
        self.initialize_class(MW,data_index,table,vol)

    def initialize_class(self, MW,data_index,table,vol):
        """
            Initialize the IntensityTable for the given data_index.
        """
        self.MW = MW
        self.index = 0
        self.MW.LoadMRI.intensity = {}
        self.intensity_volumes = []
        self.intensity_volumes.append(vol)
        self.original_image = []
        self.file_name = []
        self.table = table

        self.create_table(data_index)

    def update_intensity_values(self,data_index):
        """
        Update the voxel intensity values displayed in the table based on the current slice index.
        """
        for i, vol in enumerate(self.intensity_volumes):
            z, y, x = self.MW.LoadMRI.slice_indices[data_index]
            intensity = vol[z,y,x]
            item = self.table.item(i, 2)
            item.setText(f"{intensity:.3f}")

    def create_table(self,data_index):
        """
        Initialize and populate the intensity table with the first loaded MRI volume.
        """
        if self.MW.LoadMRI.vol_dim==3:
            self.table.customContextMenuRequested.connect(lambda idx: self.show_context_menu(idx,data_index))

            self.table.setColumnWidth(0, 30)
            self.table.setColumnWidth(1, 102)
            self.table.setColumnWidth(2, 60)
            self.table.setColumnWidth(3, 60)
        else:
            self.table.customContextMenuRequested.connect(lambda idx: self.show_context_menu(idx,data_index))
            self.table.setColumnWidth(0, 30)
            self.table.setColumnWidth(1, 210)
            self.table.setColumnWidth(2, 60)
            self.table.setColumnWidth(3, 60)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)   # BIG COLUMN
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

        self.table.setRowCount(self.index+1)

        icon_dir = os.path.join(os.path.dirname(os.path.dirname((__file__))), "Icons/Internet")
        self.icon_visible = QIcon(os.path.join(icon_dir, "eye_open.png"))
        self.icon_hidden = QIcon(os.path.join(icon_dir, "eye_closed.png"))

        btn = QToolButton()
        btn.setCheckable(False)
        btn.setChecked(True)  # visible by default
        btn.setEnabled(False)
        btn.setIcon(self.icon_visible)
        btn.setToolTip("Toggle visibility")
        btn.setAutoRaise(True)
        btn.clicked.connect(lambda checked, r=self.index , b=btn: self.toggle_visibility(checked,r, b))
        btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
            }
            QToolButton:checked {
                background: transparent;
            }
        """)
        self.table.setCellWidget(self.index , 0, btn)

        # Column 1: Layer name
        layer_item = QTableWidgetItem(os.path.basename(self.MW.LoadMRI.file_name[data_index]))
        layer_item.setFlags(layer_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(self.index , 1, layer_item)

        # Column 2: Intensity
        z,y,x = self.MW.LoadMRI.slice_indices[data_index]
        intensity_item = QTableWidgetItem(f"{self.intensity_volumes[0][z,y,x]:.3f}")
        intensity_item.setTextAlignment(Qt.AlignCenter)
        intensity_item.setFlags(intensity_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(self.index , 2, intensity_item)

        self.MW.LoadMRI.intensity[self.index]=[]
        self.MW.LoadMRI.intensity[self.index] = self.table.item(self.index , 2)
        self.MW.LoadMRI.cursor_ui[f"intensity{self.index}"] = self.table.item(self.index , 2)

        # Column 3: Opacity [%]
        opacity_spin = QDoubleSpinBox()
        opacity_spin.setRange(0.0, 100.0)
        opacity_spin.setSingleStep(5.0)
        opacity_spin.setDecimals(1)
        opacity_spin.setValue(100)
        opacity_spin.setSuffix(" %")
        opacity_spin.setAlignment(Qt.AlignCenter)
        opacity_spin.setToolTip("Adjust layer opacity")
        opacity_spin.setEnabled(False)
        self.table.setCellWidget(self.index , 3, opacity_spin)
        self.MW.LoadMRI.cursor_ui[f"opacity{self.index }"] = opacity_spin

        # Layout
        self.original_image.append(None)
        self.file_name.append(os.path.basename(self.MW.LoadMRI.file_name[data_index]))

        return


    def update_table(self,layer_name:str,vol, data_index,org_img=None, visibility_enabled=True):
        """
        Add a new layer (e.g., heatmap, label, another file, etc.) to the table.
        """
        self.original_image.append(org_img)
        self.intensity_volumes.append(vol)
        self.file_name.append(layer_name)
        self.index+=1
        self.table.insertRow(self.index)

        btn = QToolButton()
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setEnabled(visibility_enabled)
        btn.setIcon(self.icon_visible)
        btn.setToolTip("Toggle visibility")
        btn.setAutoRaise(True)
        btn.clicked.connect(lambda checked, r=self.index , b=btn: self.toggle_visibility(checked,r, b))
        btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
            }
            QToolButton:checked {
                background: transparent;
            }
        """)
        self.table.setCellWidget(self.index , 0, btn)

        # Column 1: Layer name
        layer_item = QTableWidgetItem(layer_name)
        layer_item.setFlags(layer_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(self.index , 1, layer_item)

        # Column 2: Intensity
        z, y, x = self.MW.LoadMRI.slice_indices[data_index]
        intensity_item = QTableWidgetItem(f"{vol[z,y,x]:.3f}")
        intensity_item.setTextAlignment(Qt.AlignCenter)
        intensity_item.setFlags(intensity_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(self.index , 2, intensity_item)

        self.MW.LoadMRI.intensity[self.index ]=[]
        self.MW.LoadMRI.intensity[self.index ] = self.table.item(self.index , 2)
        self.MW.LoadMRI.cursor_ui[f"intensity{self.index}"] = self.table.item(self.index , 2)

        # Column 3: Opacity [%]
        opacity_spin = QDoubleSpinBox()
        opacity_spin.setRange(0.0, 100.0) # percentage (0–100)
        opacity_spin.setSingleStep(5.0)
        opacity_spin.setDecimals(1)
        opacity_spin.setValue(0.6 * 100)  # assume stored 0.0–1.0 internally
        opacity_spin.setSuffix(" %")
        opacity_spin.setAlignment(Qt.AlignCenter)
        opacity_spin.setEnabled(visibility_enabled)
        opacity_spin.setToolTip("Adjust layer opacity")
        opacity_spin.valueChanged.connect(lambda value, i=data_index:self.update_opacity(value,i))
        self.table.setCellWidget(self.index , 3, opacity_spin)
        self.MW.LoadMRI.cursor_ui[f"opacity{self.index }"] = opacity_spin


    def show_context_menu(self, pos,data_index):
        """
        Display right-click menu for saving or removing layers.
        """
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()

        menu = QMenu(self.MW)
        menu.addAction(f"Save image {self.file_name[row]}", lambda: self.save_layer(row))
        menu.addAction("Remove image", lambda: self.remove_layer(row,data_index))
        menu.exec(self.table.mapToGlobal(pos))



    def toggle_visibility(self,checked,row, btn,data_index):
        """
        Toggle visibility of a selected layer in all three orthogonal views.

        !!!At the moment, this function only works for 3D data!!!
        """
        for vn in 'axial','coronal','sagittal':
            if vn=='axial':
                slice = self.intensity_volumes[row][self.MW.LoadMRI.slice_indices[data_index][0],:,:]
            elif vn=='coronal':
                slice = self.intensity_volumes[row][:,self.MW.LoadMRI.slice_indices[data_index][1],:]
            elif vn=='sagittal': #different with .T flip; etc.
                slice = np.fliplr(self.intensity_volumes[row][:,:,self.MW.LoadMRI.slice_indices[data_index][2]].T)

            renderer = self.MW.LoadMRI.renderers[data_index][vn]
            actors = renderer.GetViewProps()
            actors.InitTraversal()

            for _ in range(actors.GetNumberOfItems()):
                actor = actors.GetNextProp()
                if actor.GetClassName()=="vtkOpenGLTextActor" or actor.GetClassName()=="vtkOpenGLActor" or actor.GetClassName()=="vtkActor2D":
                    continue

                image_data = actor.GetInput()
                if image_data.GetNumberOfScalarComponents()==4:
                    continue
                vtk_array = numpy_support.vtk_to_numpy(image_data.GetPointData().GetScalars())
                vtk_array = vtk_array.reshape(image_data.GetDimensions()[1], image_data.GetDimensions()[0])
                if np.allclose(vtk_array, slice):
                    selected_actor = actor

                    if checked:
                        btn.setIcon(self.icon_visible)
                        selected_actor.SetVisibility(True)
                        #should be image index!!
                        self.MW.LoadMRI.vtk_widgets[data_index][vn].GetRenderWindow().Render()
                    else:
                        btn.setIcon(self.icon_hidden)
                        selected_actor.SetVisibility(False)
                        self.MW.LoadMRI.vtk_widgets[data_index][vn].GetRenderWindow().Render()
                        self.MW.LoadMRI.update_slices(0)
                    break

    def update_opacity(self,value,data_index):
        """
        Adjust opacity of the selected layer across all three orientations.

        !!!At the moment, this function only works for 3D data!!!
        """
        row = self.table.currentRow()
        for vn in 'axial','coronal','sagittal':
            if vn=='axial':
                slice = self.intensity_volumes[row][self.MW.LoadMRI.slice_indices[data_index][0],:,:]
            elif vn=='coronal':
                slice = self.intensity_volumes[row][:,self.MW.LoadMRI.slice_indices[data_index][1],:]
            elif vn=='sagittal': #different with .T flip; etc.
                slice = np.fliplr(self.intensity_volumes[row][:,:,self.MW.LoadMRI.slice_indices[data_index][2]].T)

            renderer = self.MW.LoadMRI.renderers[data_index][vn]
            actors = renderer.GetViewProps()
            actors.InitTraversal()

            for _ in range(actors.GetNumberOfItems()):
                actor = actors.GetNextProp()
                if actor.GetClassName()=="vtkOpenGLTextActor" or actor.GetClassName()=="vtkOpenGLActor" or actor.GetClassName()=="vtkActor2D":
                    continue

                image_data = actor.GetInput()
                if image_data.GetNumberOfScalarComponents()==4:
                    continue
                vtk_array = numpy_support.vtk_to_numpy(image_data.GetPointData().GetScalars())
                vtk_array = vtk_array.reshape(image_data.GetDimensions()[1], image_data.GetDimensions()[data_index])
                if np.allclose(vtk_array, slice):
                    selected_actor = actor
                    selected_actor.GetProperty().SetOpacity(value/100)
                    self.MW.LoadMRI.vtk_widgets[data_index][vn].GetRenderWindow().Render()
                    self.MW.LoadMRI.update_slices(0,0,data_view='coronal')
                    break


    def save_layer(self,row):
        """
        Save selected image layer (anat, seg, or generic) as a NIfTI file.
        """
        img_to_save = self.original_image[row]
        file_name = self.file_name[row]

        if img_to_save is None:
            vol_to_save = self.intensity_volumes[row]
            if self.table.item(row,1).text()=='Label':
                if self.MW.LoadMRI.vol_dim==4:
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle("Choose which data to save")
                    msg_box.setText("Which data do you want to save?")
                    btn_anat = msg_box.addButton("Anat", QMessageBox.ActionRole)
                    btn_seg = msg_box.addButton("Segmentation", QMessageBox.ActionRole)
                    msg_box.exec_()

                    label_volume = self.MW.LoadMRI.paintbrush.label_volume.copy()
                    if btn_anat:
                        file_name = self.file_name[0][:-7]
                        file_name = f"{file_name}-anat.nii.gz"
                        vol_to_save[label_volume > self.MW.LoadMRI.mrid_tags.num_regions] = 0
                    elif btn_seg:
                        file_name = self.file_name[0][:-7]
                        file_name = f"{file_name}-segmentation.nii.gz"
                        vol_to_save[label_volume <= self.MW.LoadMRI.mrid_tags.num_regions] = 0
                else:
                    file_name = self.file_name[0][:-7]
                    file_name = f"{file_name}-label"

            img_to_save = sITK.GetImageFromArray(vol_to_save)
            size = list(self.intensity_volumes[row].shape[::-1]) + [0]

            # Extract 1 time frame
            img = sITK.ReadImage(self.MW.LoadMRI.file_name[0])
            reference_image = sITK.Extract(
                img,
                size=size,
                index=[0, 0, 0, 0]  # take time=0 frame
            )
            img_to_save.CopyInformation(reference_image)

        save_path, _ = QFileDialog.getSaveFileName(
            self.MW,
            "Save NIfTI File",
            file_name,
            "NIfTI Files (*.nii.gz);;All Files (*)"
        )

        if not save_path:
            return

        # Ensure the filename ends with .nii.gz
        if not save_path.lower().endswith(".nii.gz"):
            save_path += ".nii.gz"

        sITK.WriteImage(img_to_save, save_path)




    def remove_layer(self,row,data_index):
        """
        Remove a layer from VTK renderers and update the GUI table.

        !!! Only tested with 3D data!!!
        """
        if self.table.item(row,1).text()=='Label':
            for vn in 'axial','coronal','sagittal':
                renderer = self.MW.LoadMRI.renderers[data_index][vn]
                actor = self.overlay_actors[vn]
                renderer.RemoveActor(actor)
                self.MW.LoadMRI.vtk_widgets[0][vn].GetRenderWindow().Render()
                self.MW.LoadMRI.update_slices(0)
        else:
            for vn in 'axial','coronal','sagittal':
                if vn=='axial':
                    slice = self.intensity_volumes[row][self.MW.LoadMRI.slice_indices[data_index][0],:,:]
                elif vn=='coronal':
                    slice = self.intensity_volumes[row][:,self.MW.LoadMRI.slice_indices[data_index][1],:]
                elif vn=='sagittal': #different with .T flip; etc.
                    slice = np.fliplr(self.intensity_volumes[row][:,:,self.MW.LoadMRI.slice_indices[data_index][2]].T)

                renderer = self.MW.LoadMRI.renderers[data_index][vn]
                actors = renderer.GetViewProps()
                actors.InitTraversal()

                for _ in range(actors.GetNumberOfItems()):
                    actor = actors.GetNextProp()
                    if actor.GetClassName()=="vtkOpenGLTextActor" or actor.GetClassName()=="vtkOpenGLActor" or actor.GetClassName()=="vtkActor2D":
                        continue
                    image_data = actor.GetInput()

                    vtk_array = numpy_support.vtk_to_numpy(image_data.GetPointData().GetScalars())
                    vtk_array = vtk_array.reshape(image_data.GetDimensions()[1], image_data.GetDimensions()[0])
                    if np.allclose(vtk_array, slice):
                        renderer.RemoveActor(actor)
                        self.MW.LoadMRI.vtk_widgets[0][vn].GetRenderWindow().Render()
                        self.MW.LoadMRI.update_slices(0)
                        break

        #update table
        self.table_delete_row(row)



    def table_delete_row(self,row=int):
        """
        Remove a row from the GUI table and internal data lists.
        """
        #remove row in table
        self.table.removeRow(row)

        #remove from lists
        self.intensity_volumes.pop(row)
        self.original_image.pop(row)
        self.file_name.pop(row)
        self.index-=1
