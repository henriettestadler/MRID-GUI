# This Python file uses the following encoding: utf-8
import numpy as np
import vtk
from vtk.util import numpy_support
from vtkmodules.vtkFiltersSources import vtkRegularPolygonSource
from vtkmodules.vtkRenderingCore import vtkActor,vtkPolyDataMapper
from PySide6.QtGui import QStandardItemModel,QFont,QStandardItem

import math
#import SimpleITK as sitk
import itk
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
        self.vol_threshold= self.LoadMRI.volume[0][0].astype(np.float32)

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
                spacing = (self.LoadMRI.spacing[0][2], self.LoadMRI.spacing[0][1], 1)
            elif view_name == "coronal": # y fixed -> (z,x)
                spacing = (self.LoadMRI.spacing[0][2], self.LoadMRI.spacing[0][0], 1)
            elif view_name == "sagittal":# x fixed -> (z,y)
                spacing = (self.LoadMRI.spacing[0][0], self.LoadMRI.spacing[0][1], 1)

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
                self.LoadMRI.slice_indices[0][2]*self.LoadMRI.spacing[0][2],
                self.LoadMRI.slice_indices[0][1]*self.LoadMRI.spacing[0][1],
                1.1 #otherwise not visible
            ]
        elif view_name == "coronal": # y fixed -> (z,x)
            self.center = [
                self.LoadMRI.slice_indices[0][2]*self.LoadMRI.spacing[0][2],
                self.LoadMRI.slice_indices[0][0]*self.LoadMRI.spacing[0][0],
                1.1 #otherwise not visible
            ]
        elif view_name == "sagittal":# x fixed -> (y,z)
            self.center = [
                (self.LoadMRI.volume[0][0].shape[0]-self.LoadMRI.slice_indices[0][0])*self.LoadMRI.spacing[0][0],
                self.LoadMRI.slice_indices[0][1]*self.LoadMRI.spacing[0][1],
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
                distance = (self.LoadMRI.slice_indices[0][0] - c_px[0])*self.LoadMRI.spacing[0][0]
            elif view_name == "sagittal":# x fixed -> (z,y)
                distance = (self.LoadMRI.slice_indices[0][2] - c_px[2])*self.LoadMRI.spacing[0][2]
            elif view_name == "coronal": # y fixed -> (x,z)
                distance = (self.LoadMRI.slice_indices[0][1] - c_px[1])*self.LoadMRI.spacing[0][1]

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



class SegmentationEvolution:
    def __init__(self,LoadMRI,SegInitialization,Threshold,button):
        super().__init__()

        self.LoadMRI = LoadMRI
        self.SegInit = SegInitialization
        self.Thres = Threshold

        self.inside_value = -4
        self.outside_value = +4
        self.evolution_actors = {}
        self.evolved_actors = {}
        #    'coronal': [],
        #    'axial': [],
        #    'sagittal': []
        #}

        ## create_initialwrapper
        #self.ls_array = self.initialize_level_set()
        #for vn in 'axial','coronal','sagittal':
        #    self.visualize_level_set(vn,self.ls_array,255)

        ##make selected circle lines invisible
        for i in 0,1,2:
            actor_cirlce = self.SegInit.actor_selected[i]
            actor_cirlce[2].SetVisibility(0)

        ## make circles invisible
        for i,[_, actor,center,radius,c_px,_] in enumerate(self.SegInit.actor_bubble):
            actor.SetVisibility(0)
            actor.SetVisibility(0)
            actor_cirlce = self.SegInit.actor_selected[i]
            actor_cirlce[2].SetVisibility(0)

        # Store the original icon (whatever it currently is)
        original_icon = button.icon()

        # Create a second "running" icon using a standard Qt internal icon
        running_icon = button.style().standardIcon(QStyle.SP_MediaPause)
        # #CHANGE TODO
        # path: /Icons/ITKsnap/media-playback-pause-4.png

        # Track state
        is_running = False

        # Slot to toggle the icon
        def toggle_icon():
            nonlocal is_running
            if is_running:
                button.setIcon(original_icon)
                is_running = False
            else:
                button.setIcon(running_icon)
                is_running = True

        # Connect the button
        button.clicked.connect(toggle_icon)


        #OLD: self.LoadMRI.main_window.ui.toolButton_runEvo.clicked.connect(self.run_evolution)
        #print('is itk successfully downloaded',itk.Version())

    def initialize_segmentation_itk(self, inside_value=4.0, outside_value=-4.0):
        """
        Initialize a level set image using ITK Python bindings with actor_bubble data.

        Is run by pressing PLAY
        """
        actor_bubbles = self.SegInit.actor_bubble
        mri_array = self.LoadMRI.volume[0][0]
        mri_image = itk.image_from_array(mri_array)
        mri_image.CopyInformation(mri_image)

        # Initialize level set
        level_array = np.full(mri_array.shape, outside_value, dtype=np.float32)
        th_array = np.full(mri_array.shape, outside_value, dtype=np.float32)

        # Fill inside based on threshold mask (positive values = allowed)
        inside_voxels = self.LoadMRI.th_img > 0
        th_array[inside_voxels] = inside_value

        # Fill bubbles
        for (_, _, _, radius_mm, center_vox, _) in actor_bubbles:
            center = np.array(center_vox, dtype=float)
            spacing = np.array(self.LoadMRI.spacing[0])
            zyx = np.indices(mri_array.shape).transpose(1, 2, 3, 0)
            dist2 = np.sum(((zyx - center) * spacing) ** 2, axis=-1)
            bubble_voxels = dist2 <= radius_mm ** 2
            level_array[bubble_voxels] = inside_value
            print(f"Bubble center: {center_vox}, radius: {radius_mm} mm, voxels: {np.sum(bubble_voxels)}")

        # Threshold mask for allowed growth (inside voxels)
        allowed_mask = th_array > 0 #level_array > 0
        self.threshold_mask = itk.image_from_array(allowed_mask.astype(np.uint8))
        self.threshold_mask.CopyInformation(mri_image)

        # Convert back to ITK image
        self.level_set_image = itk.image_from_array(level_array)
        self.level_set_image.CopyInformation(mri_image)

        print("Before")
        print("Min/Max:", np.min(level_array), np.max(level_array))
        print("Number of inside pixels:", np.sum(level_array > 0))
        print("DONEE")


    def segmentation_itk(self, inside_value=4.0,iterations=20):
        # Evolve bubbles
        evolved = self.evolve_bubbles(self.level_set_image, self.threshold_mask, iterations, inside_value=inside_value)
        evolved_array = itk.array_view_from_image(evolved)
        print("Evolution finished")
        print("Min/Max:", np.min(evolved_array), np.max(evolved_array))
        print("Number of inside pixels:", np.sum(evolved_array > 0))

        # Visualize
        # Convert NumPy → SimpleITK
        evolved_sitk = sITK.GetImageFromArray(evolved_array)

        # Copy metadata
        org_image = sITK.ReadImage(self.LoadMRI.file_name[0])

        evolved_sitk.SetSpacing(org_image.GetSpacing())
        evolved_sitk.SetOrigin(org_image.GetOrigin())
        evolved_sitk.SetDirection(
            np.array(org_image.GetDirection()).reshape(3, 3).flatten()
        )

        # Save
        default_name = "test4d.nii.gz" #"label_volume.nii.gz"
        save_path = os.path.join(self.LoadMRI.session_path, default_name)
        sITK.WriteImage(evolved_sitk, save_path)

        print("okay 4")

        z, y, x = self.LoadMRI.slice_indices[0].copy()
        print("okay 5")
        self.visualize(evolved[z, :, :], self.LoadMRI.vtk_widgets[0]["axial"], "axial")
        print("okay 6")
        self.visualize(evolved[:, y, :], self.LoadMRI.vtk_widgets[0]["coronal"], "coronal")
        print("okay 7")
        self.visualize(np.fliplr(evolved[:, :, x].T), self.LoadMRI.vtk_widgets[0]["sagittal"], "sagittal")
        print("okay 8")
        self.evolved = evolved
        print("okay 9")
        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()
        print("okay 10")
        ## is this correct?
        self.level_set_image = evolved



    ##NEW
    def evolve_bubbles(self, level_set_image, threshold_mask, iterations, inside_value=4.0):
        # Copy level set
        current = itk.image_from_array(itk.array_from_image(level_set_image))
        current.CopyInformation(level_set_image)

        # Binary mask of current inside voxels
        binary_level = (itk.array_from_image(current) > 0).astype(np.uint8)
        binary_level_image = itk.image_from_array(binary_level)
        binary_level_image.CopyInformation(level_set_image)

        StructuringElementType = itk.FlatStructuringElement[3] #3-dimansional
        radius = 1 #3 #5 is too much
        structuring_element = StructuringElementType.Ball(radius) #Ball

        dilate = itk.BinaryDilateImageFilter.New(
            Input=binary_level_image,
            Kernel=structuring_element,
            ForegroundValue=1
        )

        for i in range(iterations):
            dilate.Update()
            grown = dilate.GetOutput()
            grown_array = itk.array_from_image(grown)
            mask_array = itk.array_from_image(threshold_mask)

            # Keep only inside allowed region
            grown_array = np.where(mask_array > 0, grown_array, 0)

            # Update current level set
            current_array = itk.array_from_image(current)
            current_array[grown_array > 0] = inside_value
            current = itk.image_from_array(current_array.astype(np.float32))
            current.CopyInformation(level_set_image)

        return current


    def visualize(self, evolved_slice, vtk_widget, view_name):
        """
        Visualize only the evolved bubbles as red overlay in VTK.

        Parameters:
        - evolved_slice: 2D numpy array of the slice (negative = inside bubble)
        - vtk_widget: the corresponding VTK widget
        - view_name: string name for the view ("axial", "coronal", "sagittal")
        """
        h, w = evolved_slice.shape

        # Create empty RGB image (black background)
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        # Bubble mask: negative values are inside
        bubble_mask = evolved_slice > 0

        # Color bubbles red
        rgb[bubble_mask, 0] = 255  # R
        rgb[bubble_mask, 1] = 0    # G
        rgb[bubble_mask, 2] = 0    # B

        # Convert to VTK image
        vtk_data = numpy_support.numpy_to_vtk(rgb.reshape(-1, 3), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR) #ravel()
        img_vtk = vtk.vtkImageData()
        img_vtk.SetDimensions(w, h, 1)
        img_vtk.GetPointData().SetScalars(vtk_data)
        #img_vtk.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)  # RGB

        # Correct spacing per view
        if view_name == "axial":      # z fixed -> (y,x)
            spacing = (self.LoadMRI.spacing[0][2], self.LoadMRI.spacing[0][1], 2)
        elif view_name == "coronal": # y fixed -> (z,x)
            spacing = (self.LoadMRI.spacing[0][2], self.LoadMRI.spacing[0][0], 2)
        elif view_name == "sagittal":# x fixed -> (z,y)
            spacing = (self.LoadMRI.spacing[0][0], self.LoadMRI.spacing[0][1], 2)
        img_vtk.SetSpacing(spacing)

        # Create actor
        renderer = self.LoadMRI.renderers[0][view_name]
        if view_name in self.evolved_actors:
            actor = self.evolved_actors[view_name]
            renderer.RemoveActor(actor)
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputData(img_vtk)
        #actor.SetOpacity(0.6)

        # Add actor to renderer
        #renderer = vtk.vtkRenderer()
        #vtk_widget.GetRenderWindow().AddRenderer(renderer)


        renderer.AddActor(actor)

        #vtk_widget.GetRenderWindow().SetNumberOfLayers(2)
        #actor.SetLayerNumber(1)
        actor.SetOpacity(0.6)

        renderer.AddActor(actor)
        vtk_widget.GetRenderWindow().Render()

        # Keep reference
        self.evolved_actors[view_name] = actor




    def update_evolution_initializtion(self,opqaue_level):
        for vn in 'axial','coronal','sagittal':
            if vn in self.evolved_actors:
                actor = self.evolved_actors[vn]
                #self.LoadMRI.bubble_renderer[vn].RemoveActor(actor)
                self.LoadMRI.renderers[0][vn].RemoveActor(actor)
                z, y, x = self.LoadMRI.slice_indices[0].copy()
                self.visualize(self.evolved[z, :, :], self.LoadMRI.vtk_widgets[0]["axial"], "axial")
                self.visualize(self.evolved[:, y, :], self.LoadMRI.vtk_widgets[0]["coronal"], "coronal")
                self.visualize(np.fliplr(self.evolved[:, :, x].T), self.LoadMRI.vtk_widgets[0]["sagittal"], "sagittal")
        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()

#
#    ##OLD
#    ##OLD
#    ##OLD
#    ##OLD
#
#    def initialize_level_set(self):
#        level_set_array = np.full_like(self.LoadMRI.th_img, self.outside_value, dtype=np.float32)
#        # Fill spherical bubbles
#        for _, [_, _, center, radius, c_px, _] in enumerate(self.SegInit.actor_bubble):
#
#            # Compute voxel radius in index units
#            r_vox = [math.ceil(radius / sp) for sp in self.LoadMRI.spacing]
#
#            # Bounding box (clamped to volume shape)
#            zmin, zmax = max(0, c_px[0] - r_vox[0]), min(level_set_array.shape[0], c_px[0] + r_vox[0] + 1)
#            ymin, ymax = max(0, c_px[1] - r_vox[1]), min(level_set_array.shape[1], c_px[1] + r_vox[1] + 1)
#            xmin, xmax = max(0, c_px[2] - r_vox[2]), min(level_set_array.shape[2], c_px[2] + r_vox[2] + 1)
#
#            # Create local coordinate grid (physical spacing aware)
#            zz, yy, xx = np.meshgrid(
#                np.arange(zmin, zmax) - c_px[0],
#                np.arange(ymin, ymax) - c_px[1],
#                np.arange(xmin, xmax) - c_px[2],
#                indexing='ij'
#            )
#            self.dist = np.sqrt((zz * self.LoadMRI.spacing[0])**2 +
#                           (yy * self.LoadMRI.spacing[1])**2 +
#                           (xx * self.LoadMRI.spacing[2])**2)
#
#            # Mask inside bubble
#            inside_mask = self.dist <= radius
#            level_set_array[zmin:zmax, ymin:ymax, xmin:xmax][inside_mask] = self.inside_value
#
#        return level_set_array
#
#
#    def visualize_level_set(self, view_name,level_set_array,opaque_level):
#        # Extract 2D slice
#        if view_name == "axial":      # z fixed -> (y,x)
#            th_slice = self.LoadMRI.th_img[self.LoadMRI.slice_indices[0], :, :].astype(np.float32)
#            ls_slice = level_set_array[self.LoadMRI.slice_indices[0], :, :]
#            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[1], 1)
#        elif view_name == "coronal": # y fixed -> (z,x)
#            th_slice = self.LoadMRI.th_img[:, self.LoadMRI.slice_indices[1], :].astype(np.float32)
#            ls_slice = level_set_array[:, self.LoadMRI.slice_indices[1], :]
#            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[0], 1)
#        elif view_name == "sagittal":# x fixed -> (z,y)
#            th_slice = self.LoadMRI.th_img[:, :, self.LoadMRI.slice_indices[2]].astype(np.float32)
#            ls_slice = level_set_array[:, :, self.LoadMRI.slice_indices[2]]
#            spacing = (self.LoadMRI.spacing[0], self.LoadMRI.spacing[1], 1)
#            th_slice = np.rot90(th_slice, k=-1)  # Optional: rotate to orient as (z, y)
#            ls_slice = np.rot90(ls_slice, k=-1)  # Same rotation
#
#
#        # Prepare RGBA output array
#        shape = th_slice.shape
#
#        # Inside pixels → red
#        rgb_overlay = np.zeros(shape + (4,), dtype=np.uint8)
#        inside_mask = ls_slice == self.inside_value
#        rgb_overlay[inside_mask] = [255, 0, 0, opaque_level]
#
#
#        # Create vtkImageData
#        flat_rgba = rgb_overlay.reshape(-1, 4)
#        vtk_array = numpy_support.numpy_to_vtk(flat_rgba, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
#        image_data = vtk.vtkImageData()
#        image_data.SetDimensions(shape[1], shape[0], 1)  # x, y, z dims
#        image_data.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 4)
#        image_data.GetPointData().SetScalars(vtk_array)
#        image_data.SetSpacing(spacing)
#
#
#        # Create new renderer once
#        if not hasattr(self.LoadMRI, "bubble_renderer"):
#            self.LoadMRI.bubble_renderer = {}
#            for vn in 'axial','coronal','sagittal':
#                vtk_widget = self.LoadMRI.vtk_widgets[vn]
#                self.LoadMRI.bubble_renderer[vn] = vtk.vtkRenderer()
#                vtk_widget.GetRenderWindow().SetNumberOfLayers(4)
#                vtk_widget.GetRenderWindow().AddRenderer(self.LoadMRI.bubble_renderer[vn])
#                vtk_widget.GetRenderWindow().Render()
#                self.LoadMRI.bubble_renderer[vn].SetLayer(3)
#                self.LoadMRI.bubble_renderer[vn].SetActiveCamera(vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera())
#
#        #add actor
#        actor_ax = vtk.vtkImageActor()
#        actor_ax.GetMapper().SetInputData(image_data)
#        actor_ax.SetOpacity(1)
#        if opaque_level == 255:
#            self.LoadMRI.bubble_renderer[view_name].AddActor(actor_ax)
#        else:
#            self.LoadMRI.renderers[view_name].AddActor(actor_ax)
#
#        self.evolution_actors[view_name] = actor_ax
#
#
#    def update_evolution(self):
#        print(self.evolution_actors)
#        for vn in 'axial','coronal','sagittal':
#            actor = self.evolution_actors[vn]
#            self.LoadMRI.bubble_renderer[vn].RemoveActor(actor)
#            self.LoadMRI.renderers[vn].RemoveActor(actor)
#            self.visualize_level_set(vn,self.ls_array,255)
#
#        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
#            for view_name, widget in vtk_widget_image.items():
#                widget.GetRenderWindow().Render()
#
#
#    def new_evolution(self):
#        self.ls_array = self.initialize_level_set()
#        print(self.evolution_actors)
#        for vn in 'axial','coronal','sagittal':
#            actor = self.evolution_actors[vn]
#            self.LoadMRI.bubble_renderer[vn].RemoveActor(actor)
#            self.LoadMRI.renderers[vn].RemoveActor(actor)
#            self.visualize_level_set(vn,self.ls_array,255)
#        # make circles invisible
#        for i,[_, actor,center,radius,c_px,_] in enumerate(self.SegInit.actor_bubble):
#            actor.SetVisibility(0)
#            actor.SetVisibility(0)
#            actor_cirlce = self.SegInit.actor_selected[i]
#            actor_cirlce[2].SetVisibility(0)
#        #make selected circle lines invisible
#        for i in 0,1,2:
#            actor_cirlce = self.SegInit.actor_selected[i]
#            actor_cirlce[2].SetVisibility(0)
#        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
#            for view_name, widget in vtk_widget_image.items():
#                widget.GetRenderWindow().Render()
#
#
#
#    def run_evolution(self):
#        print('start evolution')
#        # Set number of iterations
#        n_iterations = 1000
#
#        X_dim, Y_dim, Z_dim = self.LoadMRI.volume.shape
#
#        # Create empty bubble mask
#        bubble_mask = np.zeros_like(self.LoadMRI.volume, dtype=np.uint8)
#
#
#        # Fill bubbles
#        for i, (view_name, actor, center, radius, c_px, _) in enumerate(self.SegInit.actor_bubble):
#            cx, cy, cz = c_px  # in voxel coordinates
#            r = radius            # in voxels
#            X, Y, Z = np.ogrid[:X_dim, :Y_dim, :Z_dim]
#            mask = (X - cx)**2 + (Y - cy)**2 + (Z - cz)**2 <= r**2
#            bubble_mask[mask] = 1
#
#
#        mask_itk = sitk.GetImageFromArray(bubble_mask.astype(np.uint8))
#
#        ##NEW
#        print("start evolution")
#        # -------------------------------
#        # PARAMETERS
#        n_iterations = 1000           # <- change this to control evolution length
#        propagation_scaling = 0.7
#        curvature_scaling = 0.5
#        advection_scaling = 1.0
#        dilation_radius = [2, 2, 2]   # voxels to optionally grow bubble
#        intensity_threshold = 0.2     # optional threshold to limit growth
#        sigma_gradient = 2.0          # gradient smoothing
#        # -------------------------------
#
#        X_dim, Y_dim, Z_dim = self.LoadMRI.volume.shape
#
#        # -------------------------------
#        # Create initial bubble mask (uint8)
#        bubble_mask = np.zeros_like(self.LoadMRI.volume, dtype=np.uint8)
#        for _, _, _, radius, c_px, _ in self.SegInit.actor_bubble:
#            cx, cy, cz = c_px
#            X, Y, Z = np.ogrid[:X_dim, :Y_dim, :Z_dim]
#            mask = (X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2 <= radius ** 2
#            bubble_mask[mask] = 1
#
#        mask_itk = sitk.GetImageFromArray(bubble_mask)
#        # -------------------------------
#        # Optional: dilate bubble
#        mask_itk = sitk.BinaryDilate(mask_itk, dilation_radius, sitk.sitkBall)
#
#        # -------------------------------
#        # Convert MRI to SimpleITK, rescale 0-1
#        mri_itk = sitk.GetImageFromArray(self.LoadMRI.volume.astype(np.float32))
#        mri_itk = sitk.RescaleIntensity(mri_itk, 0.0, 1.0)
#
#
#
#
#        # Optional smoothing
#        smoothing = sitk.CurvatureAnisotropicDiffusion(mri_itk, timeStep=0.0625, numberOfIterations=5)
#
#        # -------------------------------
#        # Feature image for geodesic level set
#        gradient = sitk.GradientMagnitudeRecursiveGaussian(smoothing, sigma=sigma_gradient)
#        gradient = sitk.RescaleIntensity(gradient, 0.0, 1.0)
#        # Create intensity mask (stop bubble in low-intensity areas)
#        feature_img = sitk.Cast(1.0 / (1.0 + gradient * 5.0), sitk.sitkFloat32)
#        #intensity_mask = mri_itk > 0.2  # adjust threshold
#        intensity_mask = sitk.Cast(mri_itk > 0.2, sitk.sitkFloat32)
#        feature_img = sitk.Cast(feature_img * sitk.Cast(intensity_mask, sitk.sitkFloat32), sitk.sitkFloat32)
#
#
#        # -------------------------------
#        # Create initial level set
#        # Inside bubble = negative, background = positive
#
#        # Create signed distance map from mask
#        mask_ls_np = np.where(sitk.GetArrayFromImage(mask_itk) > 0, -1.0, 1.0).astype(np.float32)
#        mask_ls_itk = sitk.GetImageFromArray(mask_ls_np)
#
#        initial_ls = sitk.SignedMaurerDistanceMap(
#            mask_itk,
#            insideIsPositive=True,  # True because bubble is negative (<0)
#            useImageSpacing=True
#        )
#        initial_ls = sitk.Clamp(initial_ls, lowerBound=-5.0, upperBound=5.0)
#        initial_ls = sitk.Cast(initial_ls, sitk.sitkFloat32)
#
#        print("Initial LS min/max:", sitk.GetArrayFromImage(initial_ls).min(), sitk.GetArrayFromImage(initial_ls).max())
#
#        # -------------------------------
#        # Geodesic Active Contour Level Set
#        geodesic_ls = sitk.GeodesicActiveContourLevelSetImageFilter()
#        geodesic_ls.SetNumberOfIterations(n_iterations)
#        geodesic_ls.SetPropagationScaling(propagation_scaling)
#        geodesic_ls.SetCurvatureScaling(curvature_scaling)
#        geodesic_ls.SetAdvectionScaling(advection_scaling)
#
#        # Run evolution
#        segmentation_itk = geodesic_ls.Execute(initial_ls, feature_img)
#
#        # -------------------------------
#        # Convert back to numpy (inside = 1, outside = 0)
#        segmentation_np = (sitk.GetArrayFromImage(segmentation_itk) < 0).astype(np.uint8)
#        print("Segmented voxels:", segmentation_np.sum())
#
#        ##Small debug
#
#        # Convert back to numpy
#        #segmentation_np = (sitk.GetArrayFromImage(segmentation_itk) < 0).astype(np.uint8)
#        print("Mask unique values before dilate:", np.unique(sitk.GetArrayFromImage(mask_itk)))
#        print("Mask sum before dilate:", np.sum(sitk.GetArrayFromImage(mask_itk)))
#        #arr_dilate = sitk.GetArrayFromImage(dilate)
#        #print("Mask unique values after dilate:", np.unique(arr_dilate))
#        #print("Mask sum after dilate:", np.sum(arr_dilate))
#
#
#        ##OLD
#
#        #threshold_mask_combined = np.maximum(self.LoadMRI.th_img, bubble_mask)
#        #threshold_mask_combined = (threshold_mask_combined > 0).astype(np.float32)
#
#        # Convert numpy arrays to SimpleITK images
#        # Convert to float32
#        #mri_float = self.LoadMRI.volume.astype(np.float32)
#
#        ## Rescale to 0–1
#        #mri_float = (mri_float - mri_float.min()) / (mri_float.max() - mri_float.min())
#
#        ## Optional: slightly enhance contrast with power-law (gamma) correction
#        #gamma = 1.5  # >1 increases contrast in midtones
#        #mri_float = np.power(mri_float, gamma)
#
#        ## Convert back to SimpleITK
#        #mri_itk = sitk.GetImageFromArray(mri_float)
#        #mri_itk = sitk.RescaleIntensity(mri_itk, outputMinimum=0.0, outputMaximum=1.0)
#
#
#        ## Edge potential map: 1 / (1 + gradient)
#        #smoothing = sitk.CurvatureAnisotropicDiffusion(mri_itk, timeStep=0.0625, numberOfIterations=5)
#        #gradient = sitk.GradientMagnitudeRecursiveGaussian(smoothing, sigma=2.0)
#        #gradient = sitk.Clamp(gradient, lowerBound=1e-5)
#        #gradient = sitk.RescaleIntensity(gradient, 0.1, 1.0)
#        ##feature_img = sitk.Cast(1.0 / (1.0 + gradient*10), sitk.sitkFloat32)
#        #feature_img = sitk.Cast(1.0 / gradient, sitk.sitkFloat32)
#
#
#        ## Create initial level set from the mask (distance map)
#        #initial_ls = sitk.SignedMaurerDistanceMap(
#        #    mask_itk,
#        #    insideIsPositive=False, useImageSpacing=True
#        #)
#        #initial_ls = sitk.Clamp(initial_ls, lowerBound=-5.0, upperBound=5.0)
#        #initial_ls = sitk.Cast(initial_ls, sitk.sitkFloat32)
#
#        ## Geodesic Active Contour Level Set
#
#        #geodesic_ls = sitk.GeodesicActiveContourLevelSetImageFilter()
#        #geodesic_ls.SetNumberOfIterations(n_iterations)
#        #geodesic_ls.SetPropagationScaling(1.0)
#        #geodesic_ls.SetCurvatureScaling(0.5)
#        #geodesic_ls.SetAdvectionScaling(1.0)
#
#        ## Run level set
#        ##segmentation_itk = geodesic_ls.Execute(initial_ls, smoothing)
#        #segmentation_itk = geodesic_ls.Execute(initial_ls, feature_img)
#
#
#
#
#
#
#
#
#        ## AXIAL
#        slice_np = segmentation_np[1, :, :]
#        vtk_slice_array = numpy_support.numpy_to_vtk(num_array=slice_np.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
#        vtk_slice_image = vtk.vtkImageData()
#        vtk_slice_image.SetDimensions(slice_np.shape[1], slice_np.shape[0], 1)  # X, Y, 1 slice
#        vtk_slice_image.GetPointData().SetScalars(vtk_slice_array)
#        spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[1], 1)
#        vtk_slice_image.SetSpacing(spacing)
#        color_map = vtk.vtkImageMapToColors()
#        color_map.SetInputData(vtk_slice_image)
#        # Make all non-zero pixels red
#        lookup_table = vtk.vtkLookupTable()
#        lookup_table.SetNumberOfTableValues(2)
#        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # background transparent
#        lookup_table.SetTableValue(1, 1, 0, 0, 1)  # red, opaque
#        lookup_table.Build()
#        color_map.SetLookupTable(lookup_table)
#        color_map.Update()
#        actor_ax = vtk.vtkImageActor()
#        actor_ax.GetMapper().SetInputData(vtk_slice_image)
#        actor_ax.SetOpacity(1)
#        actor_ax.GetMapper().SetInputData(color_map.GetOutput())
#        renderer = self.LoadMRI.renderers['axial']
#        #renderer.RemoveActor(self.Thres.vol_actors['axial'])
#        renderer.AddActor(actor_ax)
#        self.LoadMRI.vtk_widgets['axial'].GetRenderWindow().Render()
#
#        ## CORONAL
#        slice_np = segmentation_np[:, 32, :]
#        vtk_slice_array = numpy_support.numpy_to_vtk(num_array=slice_np.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
#        vtk_slice_image = vtk.vtkImageData()
#        vtk_slice_image.SetDimensions(slice_np.shape[1], slice_np.shape[0], 1)  # X, Y, 1 slice
#        vtk_slice_image.GetPointData().SetScalars(vtk_slice_array)
#        spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[0], 1)
#        vtk_slice_image.SetSpacing(spacing)
#        color_map = vtk.vtkImageMapToColors()
#        color_map.SetInputData(vtk_slice_image)
#        # Make all non-zero pixels red
#        lookup_table = vtk.vtkLookupTable()
#        lookup_table.SetNumberOfTableValues(2)
#        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # background transparent
#        lookup_table.SetTableValue(1, 1, 0, 0, 1)  # red, opaque
#        lookup_table.Build()
#        color_map.SetLookupTable(lookup_table)
#        color_map.Update()
#        actor_ax = vtk.vtkImageActor()
#        actor_ax.GetMapper().SetInputData(vtk_slice_image)
#        actor_ax.SetOpacity(1)
#        actor_ax.GetMapper().SetInputData(color_map.GetOutput())
#        renderer = self.LoadMRI.renderers['coronal']
#        renderer.AddActor(actor_ax)
#        self.LoadMRI.vtk_widgets['coronal'].GetRenderWindow().Render()
#
#        ##SAGITTAL
#        slice_np = np.fliplr(segmentation_np[:, :, 91].T)
#        vtk_slice_array = numpy_support.numpy_to_vtk(num_array=slice_np.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
#        vtk_slice_image = vtk.vtkImageData()
#        vtk_slice_image.SetDimensions(slice_np.shape[1], slice_np.shape[0], 1)  # X, Y, 1 slice
#        vtk_slice_image.GetPointData().SetScalars(vtk_slice_array)
#        spacing = (self.LoadMRI.spacing[0], self.LoadMRI.spacing[1], 1)
#        vtk_slice_image.SetSpacing(spacing)
#        color_map = vtk.vtkImageMapToColors()
#        color_map.SetInputData(vtk_slice_image)
#        # Make all non-zero pixels red
#        lookup_table = vtk.vtkLookupTable()
#        lookup_table.SetNumberOfTableValues(2)
#        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # background transparent
#        lookup_table.SetTableValue(1, 1, 0, 0, 1)  # red, opaque
#        lookup_table.Build()
#        color_map.SetLookupTable(lookup_table)
#        color_map.Update()
#        actor_ax = vtk.vtkImageActor()
#        actor_ax.GetMapper().SetInputData(vtk_slice_image)
#        actor_ax.SetOpacity(1)
#        actor_ax.GetMapper().SetInputData(color_map.GetOutput())
#        renderer = self.LoadMRI.renderers['sagittal']
#        #renderer.RemoveActor(self.Thres.vol_actors['axial'])
#        renderer.AddActor(actor_ax)
#        self.LoadMRI.vtk_widgets['sagittal'].GetRenderWindow().Render()
#
#        print('finished')








