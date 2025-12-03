# This Python file uses the following encoding: utf-8
from mrid_utils import handlers, gauss_aux, warper, chmap
import numpy as np
import nibabel as nib
import os
import pickle
from PySide6.QtWidgets import QFileDialog
import vtk
import SimpleITK as sitk
from vtk.util import numpy_support

class ElectrodeLoc:
    """
    Class for Electrode Localisation and visualizing the found points on MRI image in 4th image.
    """
    def __init__(self,LoadMRI):
        """
        Initialize the ElectrodeLoc object with a reference to LoadMRI.
        """
        self.LoadMRI = LoadMRI
        self.savepath = LoadMRI.session_path
        self.sessionpath = LoadMRI.session_path
        self.labelsdf = handlers.read_labels(os.path.join(self.sessionpath, "anat", "labels.txt"))
        self.LoadMRI.renderers[3] = {}


    def get_gaussian_centers(self,transformation_files):
        """
        1. Warping heatmaps, segmentation and 4D volume at first-timestamp
        2. Getting Gaussian Centers or Electrodes
        """
        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
            self.filename = self.LoadMRI.file_name[idx][:-7]
            roi_names = self.get_roinames(os.path.join(self.sessionpath, "anat", "labels.txt"))
            self.orientation = data_view

            for roi_name in roi_names:
                #warps and resamples heatmaps
                fixed_path = warper.heatmap_warp(self.filename, roi_name, self.savepath, self.sessionpath, transformation_files[idx])
                #save gaussian centers
                volume3d_resampled = np.asanyarray(nib.load(fixed_path).dataobj)
                savepath = os.path.join(self.LoadMRI.session_path, 'analysed',roi_name,self.orientation)
                gauss_aux.run_gaussian_analysis(self.filename, savepath, roi_name, self.orientation, volume3d_resampled, self.labelsdf)

    def getCoordinates(self):
        """
        Loads a pickle file with MRID design parameters and the Gaussian centers found in self.get_gaussian_centers

        Finds best-fit to compute final  Gaussian centers and isualizes them in the warped MRI slice.

        """
        # Pickle file that contains all the design parameters of each MRID tag
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Please select pkl file",
            "",
            "PKL files (*.pkl)"
        )
        if not file_path:
            return  # user cancelled

        with open(file_path, 'rb') as f:
            mrid_dict = pickle.load(f)


        roi_names = self.get_roinames(os.path.join(self.sessionpath, "anat", "labels.txt"))
        for mrid in roi_names:
            mrid = mrid.lower() #make sure it is all lower case
            gaussian_centers_coronal, contrast_intensities_coronal, \
            gaussian_centers_sagittal, contrast_intensities_sagittal, \
            gaussian_centers_axial, contrast_intensities_axial, \
            gaussian_sigmas_coronal, gaussian_sigmas_sagittal = handlers.get_gaussian_centers(self.sessionpath, mrid)


            gaussian_centers_3d = gauss_aux.combine_gauss_centers_3D(gaussian_centers_coronal,
                                                            contrast_intensities_coronal,
                                                            gaussian_centers_sagittal,
                                                            contrast_intensities_sagittal,
                                                            gaussian_centers_axial,
                                                            contrast_intensities_axial,
                                                            self.savepath)


        fitted_points = chmap.register_bundle(gaussian_centers_3d, mrid_dict[mrid], bundle_start=0, weighted_loss_f="density",
                                               visualization=False)

        for data_index in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[data_index]
            filename = self.LoadMRI.file_name[data_index][0:self.LoadMRI.file_name[data_index].find('.')] #[os.path.splitext(f)[0] for f in self.LoadMRI.file_name]
            filename_4d_warped = ".".join((filename + "-resampled-warped", "nii", "gz"))
            filename_4d_warped_path = os.path.join(self.savepath, filename_4d_warped)
            img_4d= sitk.ReadImage(filename_4d_warped_path)
            vol = sitk.GetArrayFromImage(img_4d)
            if data_view=='sagittal':
                img_slice = np.fliplr(vol[:,:,round(fitted_points[0][0])].T)
                #spacing = []
            else:
                img_slice = vol[int(fitted_points[0][2]),:,:]
            spacing = img_4d.GetSpacing() #xyz # #

            self.visualize_4Dwarpedslice(img_slice,spacing,data_index,data_view)
            renderer = self.LoadMRI.renderers[3][data_view]
            for idx in range(len(fitted_points)):
                if data_view=='sagittal':
                    x = vol.shape[0]-1-fitted_points[idx][2]
                    y = fitted_points[idx][1]
                    spacing = np.array(spacing)
                    spacing[2] = spacing[0]
                else:
                    x = fitted_points[idx][0]
                    y = fitted_points[idx][1]
                self.add_point(renderer, x,y,spacing,vol)

        #after minimaps are created, rectanlges are still needed
        #self.LoadMRI.minimap.create_small_rectangle(zoom_factor=1)



    def get_roinames(self,filename):
        """
        Read ROI names from a label file.
        """
        labels = []
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Split by tab or spaces
                parts = line.split()
                # The last column is the quoted label name
                if len(parts) >= 8:
                    label = parts[-1].strip('"')
                    labels.append(label)
        labels.pop(0)

        roi_names = []
        pure_labels = [l.rstrip("0123456789") for l in labels]

        for i, label in enumerate(labels):
            if label.endswith("1"):
                roi_names.append((pure_labels[i]))

        return roi_names



    def add_point(self,renderer, x, y,spacing,vol):
        """
        Add point of found electrode Gaussian center to 4D MRI slice.
        """
        x=(x)*spacing[2]
        y=(y)*spacing[1]

        radius = 0.2

        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(x,y,0.2)
        sphere.SetRadius(radius)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, 0, 0)  # red

        renderer.AddActor(actor)
        renderer.GetRenderWindow().Render()

        return actor


    def visualize_4Dwarpedslice(self, img_slice,spacing,data_index,data_view):
        """
            Visualize a single slice of the first timestamp to then add the found electrode locations.

            Parameters
            ----------
            img_slice : ndarray
                2D numpy array representing the heatmap slice to display.
            reset_camera : bool
                Whether to reset the camera to focus on the heatmap area.
        """
        # add to vtkwidgets for rendering and zooming
        vtk_widget = self.LoadMRI.vtk_widgets[3][data_view]
        vtk_data = numpy_support.numpy_to_vtk(img_slice.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        h, w = img_slice.shape
        spacing = (spacing[2], spacing[1], 1)

        #renderer,img_vtk = self.open_mainimage(vtk_widget,vtk_data, spacing,w,h)
        img_vtk = vtk.vtkImageData()
        img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth
        img_vtk.SetSpacing(spacing)
        img_vtk.GetPointData().SetScalars(vtk_data)

        #create new renderer
        renderer = vtk.vtkRenderer()
        vtk_widget.GetRenderWindow().AddRenderer(renderer)
        vtk_widget.GetRenderWindow().SetMultiSamples(16)
        renderer.SetUseDepthPeeling(1)
        renderer.SetMaximumNumberOfPeels(200)
        renderer.SetOcclusionRatio(0.05)

        self.LoadMRI.renderers[3][data_view]=renderer

        nonzero_y, nonzero_x = np.nonzero(img_slice)
        spacing_x, spacing_y = spacing[1], spacing[0]  # careful: VTK x=cols, y=rows
        if len(nonzero_x) == 0 or len(nonzero_y) == 0:
            ny, nx = np.nonzero(self.LoadMRI.paintbrush.label_volume[self.LoadMRI.slice_indices[0],:,:])
            # Get pixel bounds
            x_min, x_max = nx.min(), nx.max()
            y_min, y_max = ny.min(), ny.max()

            # Convert pixel coordinates to world coordinates
            self.center_x = (x_min + x_max) / 2 * spacing_x
            self.center_y = (y_min + y_max) / 2 * spacing_y
            self.width = (x_max - x_min) * spacing_x
            self.height = (y_max - y_min) * spacing_y

        else:
            # Get pixel bounds
            x_min, x_max = nonzero_x.min()-1, nonzero_x.max()+1
            y_min, y_max = nonzero_y.min()-1, nonzero_y.max()+1

            # Convert pixel coordinates to world coordinates
            self.center_x = (x_min + x_max) / 2 * spacing_x
            self.center_y = (y_min + y_max) / 2 * spacing_y
            self.width = (x_max - x_min) * spacing_x
            self.height = (y_max - y_min) * spacing_y

        camera_base = self.LoadMRI.renderers[0][data_view].GetActiveCamera()
        fp = camera_base.GetFocalPoint()
        pos = camera_base.GetPosition()

        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(self.center_x, self.center_y, fp[2])
        camera.SetPosition(self.center_x, self.center_y, pos[2])  # small offset in z
        camera.ParallelProjectionOn()
        camera.SetParallelScale(max(self.width, self.height)/2)

        # Add image to actor to then be added to renderer
        actor = vtk.vtkImageActor()
        scalar = img_vtk.GetScalarRange()
        actor.GetProperty().SetColorWindow(scalar[1])
        actor.GetProperty().SetColorLevel(scalar[1]/2)

        actor.SetInputData(img_vtk)
        actor.Modified()
        actor.GetProperty().SetInterpolationTypeToNearest() #Linear()
        actor.GetProperty().SetOpacity(1)

        vmin, vmax = np.percentile(vtk_data, [0,100])
        lut = vtk.vtkLookupTable()
        lut.SetTableRange(vmin, vmax)
        lut.SetValueRange(0.0, 1.0)
        lut.SetSaturationRange(0.0, 0.0)
        lut.Build()
        contrast_class = getattr(self.LoadMRI, f"contrastClass_{data_index}")
        contrast_class.lut_vtk[3]=lut

        # make low values (blue end) transparent
        # now build alpha: all zero voxels → alpha = 0
        prop = actor.GetProperty()
        prop.SetLookupTable(lut)
        prop.UseLookupTableScalarRangeOn()

        renderer.AddActor(actor)

        self.LoadMRI.heatmap = True
        self.actor_heatmap = actor


        vtk_widget.GetRenderWindow().Render()
        #add minirender, interactor and other stuff
        #scale = camera.GetParallelScale()

        #if 3 not in self.LoadMRI.minimap.minimap_renderers:
        #    self.LoadMRI.minimap.minimap_renderers[3] = {}
        #    self.LoadMRI.minimap.size_rectangle[3] = {}
        #    self.LoadMRI.minimap.zoom_rects[3] = {}
        #    self.LoadMRI.minimap.minimap_actors[3] = {}

        #spacing = self.LoadMRI.spacing[data_index]
        #self.LoadMRI.cursor.add_cursor4image(data_view,data_index,scale,img_vtk) #,spacing)
        #allow interaction
        #interactor = vtk_widget.GetRenderWindow().GetInteractor()
        #interactor.SetInteractorStyle(CustomInteractorStyle(self.LoadMRI.cursor, data_view,3,None,data_index))






