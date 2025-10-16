# This Python file uses the following encoding: utf-8

import vtk
import numpy as np
from vtkmodules.util import numpy_support
from PySide6.QtGui import  QColor
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkPolyData
)


class Paintbrush:
    """
    Paintbrush tool for voxel-wise annotation on MRI volumes.
    Supports square and round brushes, paint-over logic, and overlay rendering.
    """
    def __init__(self,LoadMRI):
        """Initialiye paintbrush tool"""
        super().__init__()
        self.LoadMRI = LoadMRI

        #default brush type is squared and red label and all lable scan be overpainted
        self.brush_type= 'square'
        self.brush_color = "red"
        self.paintover_color = "white"
        self.histogram_color = "red"
        self.paint_actors = {}
        self.paint_actors_fixed = {
            'coronal': [],
            'axial': [],
            'sagittal': []
        }
        # Dictionary to hold actors
        self.overlay_actors = {}
        self.vtk_label_images = {}
        self.color_mappers = {}


    def start_paintbrush(self):
        """ Initialize label volume and setup overlay tables for each view."""
        self.label_volume = np.zeros_like(self.LoadMRI.volume[0], dtype=np.uint8)
        z,y,x = self.LoadMRI.slice_indices
        self.setup_table(self.label_volume[z, :, :], 'axial')
        self.setup_table(self.label_volume[:, y, :], 'coronal')
        self.setup_table(np.fliplr(self.label_volume[:, :, x].T), 'sagittal')


    def set_size(self,var:int):
        """Set brush size and update GUI sliders."""
        self.size = var
        self.LoadMRI.brush['size'].setEnabled(False)
        self.LoadMRI.brush['size_slider'].setEnabled(False)
        self.LoadMRI.brush['size'].setValue(self.size)
        self.LoadMRI.brush['size_slider'].setValue(self.size)
        self.LoadMRI.brush['size'].setEnabled(True)
        self.LoadMRI.brush['size_slider'].setEnabled(True)


    def get_brush_type(self,brush_type:str):
        """Set brush type: 'square' or 'round'."""
        self.brush_type = brush_type


    def mouse_moves(self,paintbrush_pos:tuple[int, int, int],filled:bool,view_name:str):
        """
        Called whenever the mouse moves. Paints overlay at voxel coordinates.
        Uses current brush size and color.
        """
        self.mouse_pos = paintbrush_pos

        if not filled:
            # Create square / circle
            self.get_paint_settings(filled,view_name,paintbrush_pos)
            return

        label_value = self.LoadMRI.paintbrush.color_combobox.index(self.brush_color)
        paintover_value = self.LoadMRI.paintbrush.color_paintover.index(self.paintover_color)

        # Determine voxel radius according to view spacing
        z, y, x = map(int, paintbrush_pos)
        nz, ny, nx = self.label_volume.shape
        half = int(self.size // 2)

        if self.brush_type == 'square':
            if view_name == 'axial':  # XY plane, spacing Z ignored
                x0, x1 = max(0, x-half), min(nx - 1, x +half+ (0 if self.size % 2 == 0 else 1))
                y0, y1 = max(0, y-half), min(ny - 1, y +half+ (0 if self.size % 2 == 0 else 1))
                # Only overwrite voxels with paintover_value
                if paintover_value != 0:
                    mask = self.label_volume[z, y0:y1, x0:x1] == paintover_value-1
                    self.label_volume[z, y0:y1, x0:x1][mask] = int(label_value)
                elif paintover_value == 0:
                    self.label_volume[z, y0:y1, x0:x1] = int(label_value)

            elif view_name == 'coronal':  # XZ plane, spacing Y ignored
                x0, x1 = max(0, x - half), min(nx - 1, x + half+ (0 if self.size % 2 == 0 else 1))
                z0, z1 = max(0, z - half), min(nz - 1, z + half+ (0 if self.size % 2 == 0 else 1))
                if paintover_value != 0:
                    mask = self.label_volume[z0:z1, y, x0:x1] == paintover_value-1
                    self.label_volume[z0:z1, y, x0:x1][mask] = int(label_value)
                elif paintover_value == 0:
                    self.label_volume[z0:z1, y, x0:x1] = int(label_value)

            elif view_name == 'sagittal':  # YZ plane, spacing X ignored
                y0, y1 = max(0, y - half), min(ny - 1, y + half + (0 if self.size % 2 == 0 else 1))
                z0, z1 = max(0, z - half), min(nz - 1, z + half + (0 if self.size % 2 == 0 else 1))
                if paintover_value != 0:
                    mask = self.label_volume[z0:z1, y0:y1, x] == paintover_value-1
                    self.label_volume[z0:z1, y0:y1, x][mask] = int(label_value)
                elif paintover_value == 0:
                    self.label_volume[z0:z1, y0:y1, x] = int(label_value)
        elif self.brush_type == 'round':
            radius = int(self.size/2)
            points_vector = []
            points_vector.append([0,0])
            # apply mask
            slice_region = self.label_volume[z, :, :]

            if self.size%2==0:
                x_new = x+0.5
                y_new = y+0.5
                for xx in range(int(radius+1)):
                    for yy in range(int(radius+1)):
                        if np.sqrt((xx-0.5)**2+(yy-0.5)**2) < self.size/2*0.98:
                            points_vector.append([xx-0.5,yy-0.5])
            else:
                x_new = x
                y_new = y
                for xx in range(int(radius+1)):
                    for yy in range(int(radius+1)):
                        if np.sqrt(xx**2+yy**2) < self.size/2*0.93:
                            points_vector.append([xx,yy])

            for sign_x in +1,+1,-1,-1:
                for sign_y in +1,-1,+1,-1:
                    for dx,dy in points_vector:
                        xi = int(round(x_new + dx*sign_x))
                        yi = int(round(y_new + dy*sign_y))

                        # check bounds
                        if 0 <= xi < self.label_volume.shape[2] and 0 <= yi < self.label_volume.shape[1]:
                            if paintover_value != 0:
                                if slice_region[yi, xi] == paintover_value - 1:
                                    slice_region[yi, xi] = label_value
                            else:
                                slice_region[yi, xi] = label_value

            self.label_volume[z, :, :] = slice_region

        # Update the overlay
        self.update_overlay(z, y, x)
        self.histogram()


    def get_paint_settings(self,filled:bool,view_name:str,paintbrush_pos:tuple[int, int, int]):
        """
        Create or update a brush actor in a given view.
        """
        LM = self.LoadMRI
        z, y, x = map(int, paintbrush_pos)

        if self.brush_type == 'square':
            # Create cube
            self.source = vtk.vtkCubeSource()
            self.source.SetZLength(0.1)  # flat in slice plane
            ##Coronal
            if view_name == 'axial':
                self.source.SetXLength(self.size*LM.spacing[2])
                self.source.SetYLength(self.size*LM.spacing[1])
                if self.size % 2 == 0:
                    self.source.SetCenter((x - 0.5) * LM.spacing[2],(y - 0.5) * LM.spacing[1],1 )#self.mouse_pos[2]*LM.spacing[2], self.mouse_pos[1]*LM.spacing[1], 1) #xy
                else:
                    self.source.SetCenter(x * LM.spacing[2],y * LM.spacing[1],1 )
            elif view_name == 'coronal':
                self.source.SetXLength(self.size*LM.spacing[2]*2)
                self.source.SetYLength(self.size*LM.spacing[0]*2)
                if self.size % 2 == 0:
                    self.source.SetCenter((x - 0.5) * LM.spacing[2],(z - 0.5) * LM.spacing[0],1 )
                else:
                    self.source.SetCenter(x * LM.spacing[2],z * LM.spacing[0],1 )

                #self.source.SetCenter(self.mouse_pos[2]*LM.spacing[2], self.mouse_pos[0]*LM.spacing[0], 1) #xz
            elif view_name == 'sagittal':
                self.source.SetXLength(self.size*LM.spacing[0])
                self.source.SetYLength(self.size*LM.spacing[1])
                if self.size % 2 == 0:
                    self.source.SetCenter((self.LoadMRI.volume[0].shape[0]-z - 0.5) * LM.spacing[0],(y - 0.5) * LM.spacing[1],1 )
                else:
                    self.source.SetCenter((self.LoadMRI.volume[0].shape[0]-z) * LM.spacing[0],y * LM.spacing[1],1 )

                #self.source.SetCenter((self.LoadMRI.volume[0].shape[0]-self.mouse_pos[0])*LM.spacing[0], self.mouse_pos[1]*LM.spacing[1], 1) #zy
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(self.source.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            qcolor = QColor(self.brush_color)
            rgb = (qcolor.redF(), qcolor.greenF(), qcolor.blueF())
            actor.GetProperty().SetColor(rgb)
            actor.GetProperty().SetLineWidth(2.0)

            actor.GetProperty().SetRepresentationToWireframe()
            actor.GetProperty().SetOpacity(1.0)
            for i in range(self.LoadMRI.num_images):
                renderer = self.LoadMRI.renderers[i][view_name] ## FOR ALL IMAGES
                if self.paint_actors.get(view_name) is not None:
                    renderer.RemoveActor(self.paint_actors[view_name])
                renderer.AddActor(actor)
                self.LoadMRI.vtk_widgets[i][view_name].GetRenderWindow().Render() ## FOR ALL IMAGES
            self.paint_actors[view_name] = None
            self.paint_actors[view_name] = actor
            return actor

        elif self.brush_type == 'round':
            #z, y, x: slides
            radius = int(self.size/2)
            points_vector = []

            if self.size%2==0:
                x_new = x+0.5
                y_new = y+ 0.5
                for xx in range(int(radius)):
                    xx +=1
                    for yy in range(int(radius)):
                        yy +=1
                        if np.sqrt((xx-0.5)**2+(yy-0.5)**2) > self.size/2*0.98:
                            points_vector.append([xx-0.5,yy-0.5])
                            break
            else:
                x_new = x
                y_new = y
                for xx in range(int(radius)):
                    xx += 1
                    for yy in range(int(radius)):
                        yy += 1
                        if np.sqrt(xx**2+yy**2) > self.size/2*0.93:
                            points_vector.append([xx,yy])
                            break

            length = len(points_vector)
            points = vtkPoints()
            num = 0
            if length > 0:
                #rechts oben
                for ii in range(length):
                    points.InsertNextPoint((x_new + points_vector[ii][0] - 0.5)* LM.spacing[2], (y_new + points_vector[ii][1] + 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new + points_vector[ii][0] - 0.5)* LM.spacing[2], (y_new + points_vector[ii][1] - 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new + points_vector[ii][0] + 0.5)* LM.spacing[2], (y_new + points_vector[ii][1] - 0.5)* LM.spacing[1],1.1)
                    num += 3

                #rechts unten
                for ii in range(length):
                    ii = length-ii-1
                    points.InsertNextPoint((x_new + points_vector[ii][0] + 0.5)* LM.spacing[2], (y_new - points_vector[ii][1] + 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new + points_vector[ii][0] - 0.5)* LM.spacing[2], (y_new - points_vector[ii][1] + 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new + points_vector[ii][0] - 0.5)* LM.spacing[2], (y_new - points_vector[ii][1] - 0.5)* LM.spacing[1],1.1)
                    num += 3

                #links unten
                for ii in range(length):
                    points.InsertNextPoint((x_new - points_vector[ii][0] + 0.5)* LM.spacing[2], (y_new - points_vector[ii][1] - 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new - points_vector[ii][0] + 0.5)* LM.spacing[2], (y_new - points_vector[ii][1] + 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new - points_vector[ii][0] - 0.5)* LM.spacing[2], (y_new - points_vector[ii][1] + 0.5)* LM.spacing[1],1.1)
                    num += 3

                #links oben
                for ii in range(length):
                    ii = length-ii-1
                    points.InsertNextPoint((x_new - points_vector[ii][0] - 0.5)* LM.spacing[2], (y_new + points_vector[ii][1] - 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new - points_vector[ii][0] + 0.5)* LM.spacing[2], (y_new + points_vector[ii][1] - 0.5)* LM.spacing[1],1.1)
                    points.InsertNextPoint((x_new - points_vector[ii][0] + 0.5)* LM.spacing[2], (y_new + points_vector[ii][1] + 0.5)* LM.spacing[1],1.1)
                    num += 3

                #remove duplicated points
                #Extract all VTK points to a NumPy array
                n_points = points.GetNumberOfPoints()
                arr = np.array([points.GetPoint(i) for i in range(n_points)])

                # Convert to (x, y) only, since z is constant
                xy = arr[:, :2]

                # Find first and last occurrence of each unique (x, y)
                unique_xy, first_idx = np.unique(xy, axis=0, return_index=True)
                _, last_idx = np.unique(xy[::-1], axis=0, return_index=True)
                last_idx = len(xy) - 1 - last_idx  # flip back

                # Start with all True → keep all
                keep = np.ones(len(xy), dtype=bool)

                # Remove any points *between* first and last duplicates
                for f, l in zip(first_idx, last_idx):
                    if l > f + 1:  # means there are points between
                        keep[f + 1:l] = False

                # Apply mask
                arr_filtered = arr[keep]

                #close the loop
                if not np.allclose(arr_filtered[0], arr_filtered[-1]):
                    arr_filtered = np.vstack([arr_filtered, arr_filtered[0]])

                # Replace VTK points
                points.Reset()
                num = 0
                for p in arr_filtered:
                    points.InsertNextPoint(*p)
                    num += 1
            else: #radius 1 or 2_new
                points.InsertNextPoint((x_new + 0.5*self.size)* LM.spacing[2], (y_new + 0.5*self.size)* LM.spacing[1],1.1)
                points.InsertNextPoint((x_new + 0.5*self.size)* LM.spacing[2], (y_new - 0.5*self.size)* LM.spacing[1],1.1)
                points.InsertNextPoint((x_new - 0.5*self.size)* LM.spacing[2], (y_new - 0.5*self.size)* LM.spacing[1],1.1)
                points.InsertNextPoint((x_new - 0.5*self.size)* LM.spacing[2], (y_new + 0.5*self.size)* LM.spacing[1],1.1)
                num = 4

            self.source = vtk.vtkPolygon()
            self.source.GetPointIds().SetNumberOfIds(num)
            for i in range(num):
                self.source.GetPointIds().SetId(i,i)

            # Mapper and actor
            # Add the polygon to a list of polygons
            polygons = vtkCellArray()
            polygons.InsertNextCell(self.source)

            # Create a PolyData
            polygonPolyData = vtkPolyData()
            polygonPolyData.SetPoints(points)
            polygonPolyData.SetPolys(polygons)
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(polygonPolyData)

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            qcolor = QColor(self.brush_color)
            rgb = (qcolor.redF(), qcolor.greenF(), qcolor.blueF())
            actor.GetProperty().SetColor(rgb)
            actor.GetProperty().SetLineWidth(2.0)

            actor.GetProperty().SetRepresentationToWireframe()
            actor.GetProperty().SetOpacity(1.0)

            actor.GetProperty().SetRepresentationToWireframe()
            actor.GetProperty().SetOpacity(1.0)
            for i in range(self.LoadMRI.num_images):
                renderer = self.LoadMRI.renderers[i][view_name] ## FOR ALL IMAGES
                if self.paint_actors.get(view_name) is not None:
                    renderer.RemoveActor(self.paint_actors[view_name])
                renderer.AddActor(actor)
                self.LoadMRI.vtk_widgets[i][view_name].GetRenderWindow().Render() ## FOR ALL IMAGES
            self.paint_actors[view_name] = None
            self.paint_actors[view_name] = actor
            return actor


    def update_overlay(self,z:int, y:int, x:int):
        """Update the VTK overlay actors for all views based on the label volume."""

        for view_name, img_vtk in self.vtk_label_images.items():
            # Axial view (XY plane at z)
            if view_name == 'axial':
                slice_img = self.label_volume[z, :, :]
            elif view_name == 'coronal':
                slice_img = self.label_volume[:, y, :]
            elif view_name == 'sagittal':
                slice_img = np.fliplr(self.label_volume[:, :, x].T)

            # Always flatten in Fortran order for VTK
            vtk_array = numpy_support.numpy_to_vtk(slice_img.ravel(),
                                                   deep=True,
                                                   array_type=vtk.VTK_UNSIGNED_CHAR)

            # Set scalars and refresh
            img_vtk.GetPointData().SetScalars(vtk_array)
            img_vtk.Modified()
            self.color_mappers[view_name].Update()
            self.overlay_actors[view_name].GetMapper().Update()
            self.lookup.SetRange(0, len(self.LoadMRI.paintbrush.color_combobox)-1)
            actor = self.overlay_actors.get(view_name)
            self.overlay_actors[view_name] = actor
            for i in range(self.LoadMRI.num_images):
                self.LoadMRI.vtk_widgets[i][view_name].GetRenderWindow().Render()


    def setup_table(self,slice_img:np.ndarray, view_name:str):
        """ Create the VTK lookup table (LUT) and image actor for a slice in a view."""
        number_colors = len(self.RGB_table)
        self.lookup = vtk.vtkLookupTable()
        self.lookup.SetNumberOfTableValues(number_colors)
        self.lookup.SetRange(0, number_colors-1)
        self.lookup.Build()
        colors = self.RGB_table
        for i, (r, g, b, a) in enumerate(colors):
            self.lookup.SetTableValue(i, r, g, b, a)

        # Make slice a flat array of integers
        vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)

        img_vtk = vtk.vtkImageData()
        h, w = slice_img.shape
        img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth

        # Correct spacing per view
        if view_name == "axial":      #x,y
            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[1], 1)
        elif view_name == "coronal":  #
            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[0], 1)
        elif view_name == "sagittal": #y,z
            spacing = (self.LoadMRI.spacing[0], self.LoadMRI.spacing[1], 1)

        # Prepare your VTK image
        vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
        img_vtk = vtk.vtkImageData()
        h, w = slice_img.shape
        img_vtk.SetDimensions(w, h, 1)
        img_vtk.SetSpacing(spacing)
        img_vtk.GetPointData().SetScalars(vtk_data)

        # Map label values to colors using LUT
        color_mapper = vtk.vtkImageMapToColors()
        color_mapper.SetLookupTable(self.lookup)
        color_mapper.SetOutputFormatToRGBA()
        color_mapper.SetInputData(img_vtk)
        color_mapper.GetLookupTable().SetRange(0, len(self.LoadMRI.paintbrush.color_combobox) - 1)
        color_mapper.Update()

        # Create the actor
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(color_mapper.GetOutputPort())
        actor.GetProperty().SetColorWindow(len(self.LoadMRI.paintbrush.color_combobox) - 1)
        actor.GetProperty().SetColorLevel((len(self.LoadMRI.paintbrush.color_combobox) - 1)/2)
        actor.GetProperty().SetOpacity(self.label_occ)  #0.3

        # Add to renderer
        for i in range(self.LoadMRI.num_images):
            renderer = self.LoadMRI.renderers[i][view_name] ## FOR ALL IMAGES
            renderer.AddActor(actor)
            renderer.GetActiveCamera().SetParallelProjection(True)
            self.LoadMRI.vtk_widgets[i][view_name].GetRenderWindow().Render() ## FOR ALL IMAGES

        self.vtk_label_images[view_name] = img_vtk
        self.color_mappers[view_name] = color_mapper
        self.overlay_actors[view_name] = actor


    def histogram(self):
        """
        Update the histogram for the current label selection in the GUI.
        """
        # assume `image_data` is your MRI slice and `labels` is label array
        histog_label = self.LoadMRI.paintbrush.color_combobox.index(self.histogram_color)
        mask = self.label_volume == histog_label
        intensities = self.LoadMRI.volume[0][mask] ## FOR ALL IMAGES

        # Clear previous plot
        self.widget_histogram.clear()
        if intensities.size == 0:
            return

        # Compute histogram
        y, x = np.histogram(intensities, bins=50)

        # Plot directly in your GUI widget
        self.widget_histogram.plot(
            x, y, stepMode=True, fillLevel=0, brush=(0,0,255,150)
        )

    def set_label_occupancy(self,var:float):
        """Set the opacity of the label overlay and update GUI sliders."""
        if var > 1:
            var /= 100
        self.label_occ = var
        self.LoadMRI.brush['label_occ_slider'].setEnabled(False)
        self.LoadMRI.brush['label_occ'].setEnabled(False)
        self.LoadMRI.brush['label_occ'].setValue(self.label_occ)
        self.LoadMRI.brush['label_occ_slider'].setValue(self.label_occ*100)
        self.LoadMRI.brush['label_occ'].setEnabled(True)
        self.LoadMRI.brush['label_occ_slider'].setEnabled(True)

        for actor in self.overlay_actors.values():
            if actor is not None:
                actor.GetProperty().SetOpacity(self.label_occ)
        # optionally re-render
        for i in range(self.LoadMRI.num_images):
            for view_name in self.overlay_actors.keys():
                self.LoadMRI.vtk_widgets[i][view_name].GetRenderWindow().Render()

