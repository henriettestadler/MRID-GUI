# This Python file uses the following encoding: utf-8
import vtk
from vtk.util import numpy_support
import numpy as np
import SimpleITK as sITK


### This class is not yet finished and perfected.
### TODO: visualize 2 images resampled and resized simultaneously

class LoadOtherFile:
    def __init__(self,LoadMRI,data_idx,vol_dim):
        self.LoadMRI = LoadMRI
        self.data_idx = data_idx
        self.vol_dim = vol_dim
        self.LoadMRI.actors_non_mainimage[self.data_idx] = {}

        # Set-up first slide
        z, y, x = self.LoadMRI.slice_indices
        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            self.update_size(image_index)
            self.setup_vtkdata(self.LoadMRI.volume[self.data_idx][image_index][z, :, :], vtk_widget_image["axial"], "axial",image_index)
            self.setup_vtkdata(self.LoadMRI.volume[self.data_idx][image_index][:, y, :], vtk_widget_image["coronal"], "coronal",image_index)
            self.setup_vtkdata(np.fliplr(self.LoadMRI.volume[self.data_idx][image_index][:, :, x].T), vtk_widget_image["sagittal"], "sagittal",image_index)

        #render
        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()


    def setup_vtkdata(self,slice_img:np.array,vtk_widget, view_name:str,image_index:int):
        """
        Create or update the VTK pipeline for a given view (axial, coronal  , sagittal).
        Handles reslice, actor creation, and LUT setup.
        """
        vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        img_vtk = vtk.vtkImageData()
        h, w = slice_img.shape
        img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth

        # Correct spacing per view
        if view_name == "axial":      # z fixed -> (y,x)
            spacing = (self.LoadMRI.spacing[self.data_idx][2], self.LoadMRI.spacing[self.data_idx][1], 1)
        elif view_name == "coronal": # y fixed -> (z,x)
            spacing = (self.LoadMRI.spacing[self.data_idx][2], self.LoadMRI.spacing[self.data_idx][0], 1)
        elif view_name == "sagittal":# x fixed -> (z,y)
            spacing = (self.LoadMRI.spacing[self.data_idx][0], self.LoadMRI.spacing[self.data_idx][1], 1)

        img_vtk.SetSpacing(spacing)
        img_vtk.GetPointData().SetScalars(vtk_data)

        # reuse renderer if exists, otherwise create one
        renderer = self.LoadMRI.renderers[image_index][view_name]

        # High-quality smoothing for better visual clarity
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(img_vtk)
        reslice.SetInterpolationModeToNearestNeighbor() #Cubic()  # Options: Nearest, Linear, Cubic
        reslice.Update()

        # Add image to actor to then be added to renderer
        actor = vtk.vtkImageActor()
        actor.SetInputData(reslice.GetOutput())
        actor.Modified()
        actor.GetProperty().SetInterpolationTypeToNearest() #Linear()
        actor.GetProperty().SetOpacity(1)
        #actor.SetInputData(new_vtk_image)  # replace with sliced 4D → 3D
                         # ensure pipeline updates
        #actor.GetProperty().SetOpacity(0.5)
        #vtk_widget.GetRenderWindow().Render()

        #mapper = vtk.vtkImageResliceMapper()
        #mapper.SetInputData(img_vtk)

        #actor = vtk.vtkImageSlice()
        #actor.SetMapper(mapper)
        #actor.GetProperty().SetOpacity(0.5)  # affects entire slice
        #renderer.AddViewProp(actor)

        # Attach LUT for contrast and brightness
        vminmax_perc = [0, 1] #reset
        vmin, vmax = np.percentile(self.LoadMRI.volume[self.data_idx][image_index], [vminmax_perc[0]*100, vminmax_perc[1]*100])
        lut_vtk = vtk.vtkLookupTable()
        lut_vtk.SetTableRange(vmin, vmax)
        lut_vtk.SetValueRange(0.0, 1.0)
        lut_vtk.SetSaturationRange(0.0, 0.0)
        lut_vtk.Build()
        prop = actor.GetProperty()
        prop.SetLookupTable(lut_vtk)
        prop.UseLookupTableScalarRangeOn()  # force LUT range

        img_vtk = vtk.vtkImageData()
        print("VTK scalar range:", img_vtk.GetScalarRange())

        actor = vtk.vtkImageActor()
        actor.SetInputData(img_vtk)
        print("Actor opacity before:", actor.GetProperty().GetOpacity())

        # Save actor, renderer, img_vtks to later be used again
        self.LoadMRI.actors_non_mainimage[self.data_idx][view_name] = actor

        renderer.AddActor(actor)

        #Update renderer
        #vtk_widget.GetRenderWindow().Render()


    def change_opacity(self,row,value):
        for view_name in 'axial','coronal','sagittal':
            actor = self.LoadMRI.actors_non_mainimage[self.data_idx][view_name]
            actor.GetProperty().SetOpacity(value/100)

        for _,vtk_widget in self.LoadMRI.vtk_widgets.items():
            vtk_widget['axial'].GetRenderWindow().Render()
            vtk_widget['coronal'].GetRenderWindow().Render()
            vtk_widget['sagittal'].GetRenderWindow().Render()


    def update_size(self,image_index):
        self.LoadMRI.origional_volume_nonmain[self.data_idx] = {}
        self.LoadMRI.origional_volume_nonmain[self.data_idx][image_index] = self.LoadMRI.volume[self.data_idx][image_index].copy()
        ref_img = self.LoadMRI.ref_image

        if self.vol_dim ==4:
            img = self.LoadMRI.image[self.data_idx][:,:,:,0]
            #img = sitk.Cast(img, sitk.sitkFloat32)
            img.SetOrigin(ref_img.GetOrigin())
        else:
            img = self.LoadMRI.image[self.data_idx]
            img.SetOrigin(ref_img.GetOrigin())

        # Build resample filter
        resample = sITK.ResampleImageFilter()
        resample.SetReferenceImage(ref_img)
        resample.SetInterpolator(sITK.sitkLinear)
        resample.SetDefaultPixelValue(0)

        # Perform resampling
        resampled = resample.Execute(img)
        resampled_array = sITK.GetArrayFromImage(resampled)

        #resampled.CopyInformation(ref_img)

        # Update data structures
        self.LoadMRI.volume[self.data_idx][image_index] = sITK.GetArrayFromImage(resampled).astype(np.float32)
