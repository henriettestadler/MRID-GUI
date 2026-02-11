# This Python file uses the following encoding: utf-8
import numpy as np
import vtk
from vtk.util import numpy_support

class ThresholdSegmentation:
    def __init__(self,LoadMRI):
        super().__init__()
        # Load original image
        self.LoadMRI = LoadMRI
        self.LoadMRI.thres_idx = self.LoadMRI.num_data_max
        self.LoadMRI.volume[self.LoadMRI.thres_idx] = {}
        self.LoadMRI.volume[self.LoadMRI.thres_idx][0] = self.LoadMRI.volume[0][0].astype(np.float32)
        self.LoadMRI.file_name[self.LoadMRI.thres_idx] = 'Threshold Image'
        self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx] = {}
        self.LoadMRI.num_data_max += 1

        # Default thresholds
        self.lower = 10
        self.upper = 50

        #if tab in toolbar is clicked on -> bounded thresholding
        self.threshold_mode = 'bounded'
        self.LoadMRI.threshold_on = True
        self.LoadMRI.ThresholdClass = self


    def only_update_displayed_image(self):
        #only display slices to the new cursor coordinates (without re-doing the smoothness calculations)
        [z, y, x] = self.LoadMRI.slice_indices

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
                spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[1], 1)
            elif view_name == "coronal": # y fixed -> (z,x)
                spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[0], 1)
            elif view_name == "sagittal":# x fixed -> (z,y)
                spacing = (self.LoadMRI.spacing[0], self.LoadMRI.spacing[1], 1)

            mask_vtk.SetSpacing(spacing)
            mask_vtk.GetPointData().SetScalars(vtk_mask_data)


            #display intensity
            intensity = th_img_float[self.LoadMRI.slice_indices[0],self.LoadMRI.slice_indices[1],self.LoadMRI.slice_indices[2]]/ 32767.0
            self.LoadMRI.intensity[self.LoadMRI.thres_idx]= intensity
            if self.LoadMRI.thres_idx in self.LoadMRI.cursor.intensity:
                self.LoadMRI.cursor.intensity[self.LoadMRI.thres_idx].setText(f"{intensity:.3f}")


            map_colors = vtk.vtkImageMapToColors()
            map_colors.SetLookupTable(self.lut)
            map_colors.SetInputData(mask_vtk)
            map_colors.Update()

            #remove and readd everytime, otherwise contrast and brightness changes
            if view_name in self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx]:
                renderer = self.LoadMRI.renderers[0][view_name]
                renderer.RemoveActor(self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx][view_name])
                del self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx][view_name]

            mask_actor = vtk.vtkImageActor()
            mask_actor.GetMapper().SetInputConnection(map_colors.GetOutputPort())
            self.LoadMRI.renderers[0][view_name].AddActor(mask_actor)
            self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx][view_name] = mask_actor

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



