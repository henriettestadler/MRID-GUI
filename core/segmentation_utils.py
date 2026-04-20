# This Python file uses the following encoding: utf-8
import numpy as np
import vtk
from vtk.util import numpy_support
from vtkmodules.vtkFiltersSources import vtkRegularPolygonSource
from vtkmodules.vtkRenderingCore import vtkActor,vtkPolyDataMapper
from PySide6.QtGui import QStandardItemModel,QFont,QStandardItem
import math
import SimpleITK as sitk
#import itk
from PySide6.QtWidgets import QStyle
import SimpleITK as sITK
import os
import nibabel as nib

class Segmentation:
    def __init__(self,LoadMRI):
        super().__init__()
        # Load original image
        self.LoadMRI = LoadMRI
        self.LoadMRI.vol_threshold = {}
        self.vol_threshold= self.LoadMRI.volumes[0].slices[0].astype(np.float32)

        # Default thresholds
        self.lower = 10
        self.upper = 50

        #if tab in toolbar is clicked on -> bounded thresholding
        self.threshold_mode = 'bounded'
        self.LoadMRI.threshold_on = True


    def only_update_displayed_image(self):
        #only display slices to the new cursor coordinates (without re-doing the smoothness calculations)
        [z, y, x] = self.LoadMRI.slice_indices[0]

        # Prepare slices
        vol_actors = {
            'axial': self.LoadMRI.th_img[z, :, :],
            'coronal': self.LoadMRI.th_img[:, y, :],
            'sagittal': np.fliplr(self.LoadMRI.th_img[:, :, x].T)
        }

        if not hasattr(self, 'mask_vtk'):
            self.mask_vtk = {}
            self.mask_actor = {}
            self.map_colors = {}

        for view_name in vol_actors:
            th_img_float = self.LoadMRI.th_img.astype(np.float32)  # convert to float
            if not hasattr(self, 'lut'):
                self.lut = {}
                #set to blue if outside threshold bounds
                self.lut = vtk.vtkLookupTable()
                self.lut.SetTableRange(th_img_float.min(), th_img_float.max())
                self.lut.SetNumberOfTableValues(256)
                self.lut.Build()
                for i in range(256):
                    val = th_img_float.min() + (th_img_float.max() - th_img_float.min()) * i / 255.0
                    if val < 0:
                        blue_intensity = -val / abs(th_img_float.min())  # scale 0 -> min_val to 0->1
                        self.lut.SetTableValue(i, 0, 0, blue_intensity, 1)  # blue
                    else:
                        gray = val / th_img_float.max()
                        self.lut.SetTableValue(i, gray, gray, gray, 1)  # grayscale


            """Convert 3D NumPy array to vtkImageData"""
            vtk_mask_data = numpy_support.numpy_to_vtk(vol_actors[view_name].ravel(), deep=True, array_type=vtk.VTK_SHORT)
            mask_vtk = vtk.vtkImageData()
            h, w = vol_actors[view_name].shape
            mask_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth< same as original image

            # Correct spacing per view
            if view_name == "axial":      # z fixed -> (y,x)
                spacing = (self.LoadMRI.volumes[0].spacing[2], self.LoadMRI.volumes[0].spacing[1], 1)
            elif view_name == "coronal": # y fixed -> (z,x)
                spacing = (self.LoadMRI.volumes[0].spacing[2], self.LoadMRI.volumes[0].spacing[0], 1)
            elif view_name == "sagittal":# x fixed -> (z,y)
                spacing = (self.LoadMRI.volumes[0].spacing[0], self.LoadMRI.volumes[0].spacing[1], 1)

            mask_vtk.SetSpacing(spacing)
            mask_vtk.GetPointData().SetScalars(vtk_mask_data)

            #display intensity
            #self.LoadMRI.intensity[0]= intensity
            #if 0 in self.LoadMRI.cursor.intensity:
            #   self.LoadMRI.cursor.intensity[0].setText(f"{intensity:.3f}")
            #print('TODO: intensity table')
            #if hasattr(self.LoadMRI,'SegInitialization'):
            #    self.LoadMRI.SegInitialization.update_bubbles_visible()


            map_colors = vtk.vtkImageMapToColors()
            map_colors.SetLookupTable(self.lut)
            map_colors.SetInputData(mask_vtk)
            map_colors.Update()

            #remove and read everytime, otherwise contrast and brightness changes
            if view_name in self.LoadMRI.actors_non_mainimage[0]:
                renderer = self.LoadMRI.renderers[0][view_name]
                renderer.RemoveActor(self.LoadMRI.actors_non_mainimage[0][view_name])
                del self.LoadMRI.actors_non_mainimage[0][view_name]

            mask_actor = vtk.vtkImageActor()
            mask_actor.GetMapper().SetInputConnection(map_colors.GetOutputPort())
            self.LoadMRI.renderers[0][view_name].AddActor(mask_actor)
            self.LoadMRI.actors_non_mainimage[0][view_name] = mask_actor

            self.LoadMRI.renderers[0][view_name].GetRenderWindow().Render()


    def smooth_binary_threshold(self,image, lower=None, upper=None, imin=None, imax=None):
        #update threshold data
        smoothness=3 #set to equal itk snap

        bidir = (lower is not None) and (upper is not None)

        # handle invalid bidirectional threshold -> black image
        if bidir and lower >= upper:
            return np.zeros_like(image, dtype=np.float32)

        factor_lower = 1.0 if lower is not None else 0.0
        factor_upper = 1.0 if upper is not None else 0.0
        shift = 1.0 - (factor_lower + factor_upper)

        if imin is None:
            imin = np.min(image)
        if imax is None:
            imax = np.max(image)

        # scaling factor based on smoothness
        if bidir:
            range_val = upper - lower
        else:
            range_val = (imax - imin) / 3.0  # ITK-SNAP default "arbitrary" choice

        eps = 10 ** (-smoothness)
        scaling_factor = np.log((2 - eps) / eps) / range_val

        # compute smooth threshold
        z = image.astype(np.float32)

        y_lower = factor_lower * np.tanh((z - lower) * scaling_factor) if lower is not None else 0
        y_upper = factor_upper * np.tanh((upper - z) * scaling_factor) if upper is not None else 0

        t = y_lower + y_upper + shift

        return (t * 0x7fff).astype(np.int16)




class SegmentationInitialization:
    def __init__(self,LoadMRI):
        super().__init__()

        self.LoadMRI = LoadMRI
        self.actor_bubble = []
        self.index = 0
        self.selected = False
        self.actor_selected = []

        #Use threshold image
        self.th_img = self.LoadMRI.th_img

    def get_bubble_center(self,view_name):
        if view_name == "axial":      # z fixed -> (x,y)
            self.center = [
                self.LoadMRI.slice_indices[0][2]*self.LoadMRI.volumes[0].spacing[2],
                self.LoadMRI.slice_indices[0][1]*self.LoadMRI.volumes[0].spacing[1],
                1.1 #otherwise not visible
            ]
        elif view_name == "coronal": # y fixed -> (z,x)
            self.center = [
                self.LoadMRI.slice_indices[0][2]*self.LoadMRI.volumes[0].spacing[2],
                self.LoadMRI.slice_indices[0][0]*self.LoadMRI.volumes[0].spacing[0],
                1.1 #otherwise not visible
            ]
        elif view_name == "sagittal":# x fixed -> (y,z)
            self.center = [
                (self.LoadMRI.volumes[0].slices[0].shape[0]-self.LoadMRI.slice_indices[0][0])*self.LoadMRI.volumes[0].spacing[0],
                self.LoadMRI.slice_indices[0][1]*self.LoadMRI.volumes[0].spacing[1],
                1.1 #otherwise not visible
            ]
        self.center_px = self.LoadMRI.slice_indices[0].copy()


    def row_selected(self,selected,deselected):
        for ix in selected.indexes():
            self.row_index = ix.row()
            self.selected = True
            self.update_bubbles_visible()
            break

    def draw_bubble(self,push_btn):
        for view_name in 'axial','sagittal','coronal':
            #Get cursor position
            self.get_bubble_center(view_name)

            polygonSource = vtkRegularPolygonSource()
            polygonSource.GeneratePolygonOn()
            polygonSource.SetNumberOfSides(100)
            polygonSource.SetRadius(self.radius)
            polygonSource.SetCenter(self.center)

            mapper = vtkPolyDataMapper()
            mapper.SetInputConnection(polygonSource.GetOutputPort())

            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(1,0,0)
            actor.GetProperty().SetOpacity(0.3)

            renderer = self.LoadMRI.renderers[0][view_name]
            renderer.AddActor(actor)
            self.LoadMRI.renderers[0][view_name].GetRenderWindow().Render()
            self.actor_bubble.append([view_name,actor,self.center,self.radius,self.center_px,polygonSource])

            self.create_circle_around_selected_bubble(view_name,self.radius,self.center)

        self.selected = True
        row = self.model.rowCount()
        self.row_index = row
        self.model.insertRow(row)
        self.model.setItem(row,0, QStandardItem(str(self.center_px[2]+1)))
        self.model.setItem(row,1, QStandardItem(str(self.center_px[1]+1)))
        self.model.setItem(row,2, QStandardItem(str(self.center_px[0]+1)))
        self.model.setItem(row,3, QStandardItem(str(self.radius)))
        self.index += 1

        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()

        if not push_btn.isEnabled():
            push_btn.setEnabled(True)


    def create_table(self,table):
        self.table = table
        self.model = QStandardItemModel(0,4)
        self.model.setHorizontalHeaderLabels(["X","Y","Z","Radius"])
        header_font = QFont()
        header_font.setBold(True)

        self.table.setModel(self.model)

        self.table.setColumnWidth(0,35)
        self.table.setColumnWidth(1,35)
        self.table.setColumnWidth(2,35)
        self.table.setColumnWidth(3,60)

        self.table.horizontalHeader().setFont(header_font)
        self.table.verticalHeader().setVisible(False)
        self.table.show()


    def create_circle_around_selected_bubble(self,view_name,radius,center):
        for i,[view_name, actor,center,radius,c_px,_] in enumerate(self.actor_bubble):
            if i < len(self.actor_bubble)-1:
                #actor.SetVisibility(0)
                actor_cirlce = self.actor_selected[i]
                actor_cirlce[2].SetVisibility(0)

        polygonSource = vtkRegularPolygonSource()
        polygonSource.GeneratePolygonOff()
        polygonSource.SetNumberOfSides(100)
        polygonSource.SetRadius(radius)
        polygonSource.SetCenter(center)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(polygonSource.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1,0,0)
        actor.GetProperty().SetOpacity(1)

        renderer = self.LoadMRI.renderers[0][view_name]
        renderer.AddActor(actor)
        self.actor_selected.append([view_name,self.index,actor,polygonSource])


    def update_bubbles_visible(self):
        for i,[view_name, actor,center,radius,c_px,_] in enumerate(self.actor_bubble):
            # Correct spacing per view
            if view_name == "axial":      # z fixed -> (x,y)
                distance = (self.LoadMRI.slice_indices[0][0] - c_px[0])*self.LoadMRI.volumes[0].spacing[0]
            elif view_name == "sagittal":# x fixed -> (z,y)
                distance = (self.LoadMRI.slice_indices[0][2] - c_px[2])*self.LoadMRI.volumes[0].spacing[2]
            elif view_name == "coronal": # y fixed -> (x,z)
                distance = (self.LoadMRI.slice_indices[0][1] - c_px[1])*self.LoadMRI.volumes[0].spacing[1]

            if radius > abs(distance):
                actor.SetVisibility(1)
                radius_new = np.sqrt(radius**2-distance**2)
                self.update_bubble_radius(i, radius_new)
            else:
                #Make invisible: Actor and Outline-Circle
                actor.SetVisibility(0)
                actor_cirlce = self.actor_selected[i]
                actor_cirlce[2].SetVisibility(0)

        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()


    def update_bubble_radius(self, index, new_radius):
        actor_entry = self.actor_bubble[index]
        polygonSource = actor_entry[5]
        polygonSource.SetRadius(new_radius)
        polygonSource.Modified()

        #circles of selected bubbles
        if self.row_index == int(index/3) and self.selected:
            actor_entry = self.actor_selected[index]
            actor_entry[2].SetVisibility(1)
            polygonSource = actor_entry[3]
            polygonSource.SetRadius(new_radius)
            polygonSource.Modified()
        else:
            actor_entry = self.actor_selected[index]
            actor_entry[2].SetVisibility(0)

