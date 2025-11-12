# This Python file uses the following encoding: utf-8

import numpy as np
import vtk
from vtk.util import numpy_support
import math
#import SimpleITK as sitk
import itk
from PySide6.QtWidgets import QStyle


class SegmentationEvolution:
    def __init__(self,LoadMRI,SegInitialization,Threshold,button):
        super().__init__()

        self.LoadMRI = LoadMRI
        self.SegInit = SegInitialization
        self.Thres = Threshold

        self.inside_value = -4
        self.outside_value = +4
        self.evolution_actors = {}
        self.evolved_actors = {
            'coronal': [],
            'axial': [],
            'sagittal': []
        }

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




    ##NEW
    def evolve_bubbles(self, level_set_image, threshold_mask, inside_value=4.0, iterations=5):
        # Copy level set
        current = itk.image_from_array(itk.array_from_image(level_set_image))
        current.CopyInformation(level_set_image)

        # Binary mask of current inside voxels
        binary_level = (itk.array_from_image(current) > 0).astype(np.uint8)
        binary_level_image = itk.image_from_array(binary_level)
        binary_level_image.CopyInformation(level_set_image)

        StructuringElementType = itk.FlatStructuringElement[3]
        radius = 1
        structuring_element = StructuringElementType.Ball(radius)

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

    def initialize_segmentation_itk(self, inside_value=4.0, outside_value=-4.0):
        """
        Initialize a level set image using ITK Python bindings with actor_bubble data.
        """
        actor_bubbles = self.SegInit.actor_bubble
        mri_array = self.LoadMRI.volume[0][0]
        mri_image = itk.image_from_array(mri_array)
        mri_image.CopyInformation(mri_image)

        # Initialize level set
        level_array = np.full(mri_array.shape, outside_value, dtype=np.float32)

        # Fill inside based on threshold mask (positive values = allowed)
        inside_voxels = self.LoadMRI.th_img > 0
        level_array[inside_voxels] = inside_value

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
        allowed_mask = level_array > 0
        threshold_mask = itk.image_from_array(allowed_mask.astype(np.uint8))
        threshold_mask.CopyInformation(mri_image)

        # Convert back to ITK image
        level_set_image = itk.image_from_array(level_array)
        level_set_image.CopyInformation(mri_image)

        # Evolve bubbles
        evolved = self.evolve_bubbles(level_set_image, threshold_mask, inside_value=inside_value, iterations=10)
        evolved_array = itk.array_view_from_image(evolved)
        print("Evolution finished")
        print("Min/Max:", np.min(evolved_array), np.max(evolved_array))
        print("Number of inside pixels:", np.sum(evolved_array > 0))

        # Visualize
        z, y, x = self.LoadMRI.slice_indices.copy()
        self.visualize(evolved[z, :, :], self.LoadMRI.vtk_widgets[0]["axial"], "axial")
        self.visualize(evolved[:, y, :], self.LoadMRI.vtk_widgets[0]["coronal"], "coronal")
        self.visualize(np.fliplr(evolved[:, :, x].T), self.LoadMRI.vtk_widgets[0]["sagittal"], "sagittal")
        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()

        return level_set_image

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
        bubble_mask = evolved_slice < 0

        # Color bubbles red
        rgb[bubble_mask, 0] = 255  # R
        rgb[bubble_mask, 1] = 0    # G
        rgb[bubble_mask, 2] = 0    # B

        # Convert to VTK image
        vtk_data = numpy_support.numpy_to_vtk(rgb.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
        img_vtk = vtk.vtkImageData()
        img_vtk.SetDimensions(w, h, 1)
        img_vtk.GetPointData().SetScalars(vtk_data)
        img_vtk.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)  # RGB

        # Correct spacing per view
        if view_name == "axial":      # z fixed -> (y,x)
            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[1], 1.1)
        elif view_name == "coronal": # y fixed -> (z,x)
            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[0], 1.1)
        elif view_name == "sagittal":# x fixed -> (z,y)
            spacing = (self.LoadMRI.spacing[0], self.LoadMRI.spacing[1], 1.1)
        img_vtk.SetSpacing(spacing)

        # Create actor
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputData(img_vtk)

        # Add actor to renderer
        renderer = self.LoadMRI.renderers[view_name]
        renderer.AddActor(actor)
        renderer.ResetCamera()

        vtk_widget.GetRenderWindow().Render()


        # Keep reference
        self.evolved_actors[view_name] = actor


        ## reuse renderer
        #renderer = self.LoadMRI.renderers[view_name]
        #lookup_table = vtk.vtkLookupTable()
        #lookup_table.SetRange(0, 1)  # your normalized data
        #lookup_table.SetValueRange(0.0, 1.0)  # brightness
        #lookup_table.SetSaturationRange(0.0, 0.0)  # grayscale
        #lookup_table.Build()

        #mapper = vtk.vtkImageMapToColors()
        #mapper.SetInputData(img_vtk)
        #mapper.SetLookupTable(lookup_table)
        #mapper.Update()

        #actor = vtk.vtkImageActor()
        #actor.GetMapper().SetInputConnection(mapper.GetOutputPort())

        ##actor = vtk.vtkImageActor()
        ##actor.GetMapper().SetInputData(img_vtk)
        ### ADDED

        #renderer.AddActor(actor)
        #mask_actor = self.Thres.vol_actors[view_name]
        #renderer.RemoveActor(mask_actor)
        #main_actor = self.LoadMRI.actors[view_name]
        #renderer.RemoveActor(main_actor)
        #renderer.ResetCamera()



        #vtk_widget.GetRenderWindow().Render()



        #self.evolved_actors[view_name] = actor

        # Debug info:
        print("VTK Image Dimensions:", img_vtk.GetDimensions())
        print("VTK Image Scalars Min/Max:", img_vtk.GetPointData().GetScalars().GetRange())


    ##OLD

    def initialize_level_set(self):
        level_set_array = np.full_like(self.LoadMRI.th_img, self.outside_value, dtype=np.float32)
        # Fill spherical bubbles
        for _, [_, _, center, radius, c_px, _] in enumerate(self.SegInit.actor_bubble):

            # Compute voxel radius in index units
            r_vox = [math.ceil(radius / sp) for sp in self.LoadMRI.spacing]

            # Bounding box (clamped to volume shape)
            zmin, zmax = max(0, c_px[0] - r_vox[0]), min(level_set_array.shape[0], c_px[0] + r_vox[0] + 1)
            ymin, ymax = max(0, c_px[1] - r_vox[1]), min(level_set_array.shape[1], c_px[1] + r_vox[1] + 1)
            xmin, xmax = max(0, c_px[2] - r_vox[2]), min(level_set_array.shape[2], c_px[2] + r_vox[2] + 1)

            # Create local coordinate grid (physical spacing aware)
            zz, yy, xx = np.meshgrid(
                np.arange(zmin, zmax) - c_px[0],
                np.arange(ymin, ymax) - c_px[1],
                np.arange(xmin, xmax) - c_px[2],
                indexing='ij'
            )
            self.dist = np.sqrt((zz * self.LoadMRI.spacing[0])**2 +
                           (yy * self.LoadMRI.spacing[1])**2 +
                           (xx * self.LoadMRI.spacing[2])**2)

            # Mask inside bubble
            inside_mask = self.dist <= radius
            level_set_array[zmin:zmax, ymin:ymax, xmin:xmax][inside_mask] = self.inside_value

        return level_set_array


    def visualize_level_set(self, view_name,level_set_array,opaque_level):
        # Extract 2D slice
        if view_name == "axial":      # z fixed -> (y,x)
            th_slice = self.LoadMRI.th_img[self.LoadMRI.slice_indices[0], :, :].astype(np.float32)
            ls_slice = level_set_array[self.LoadMRI.slice_indices[0], :, :]
            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[1], 1)
        elif view_name == "coronal": # y fixed -> (z,x)
            th_slice = self.LoadMRI.th_img[:, self.LoadMRI.slice_indices[1], :].astype(np.float32)
            ls_slice = level_set_array[:, self.LoadMRI.slice_indices[1], :]
            spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[0], 1)
        elif view_name == "sagittal":# x fixed -> (z,y)
            th_slice = self.LoadMRI.th_img[:, :, self.LoadMRI.slice_indices[2]].astype(np.float32)
            ls_slice = level_set_array[:, :, self.LoadMRI.slice_indices[2]]
            spacing = (self.LoadMRI.spacing[0], self.LoadMRI.spacing[1], 1)
            th_slice = np.rot90(th_slice, k=-1)  # Optional: rotate to orient as (z, y)
            ls_slice = np.rot90(ls_slice, k=-1)  # Same rotation


        # Prepare RGBA output array
        shape = th_slice.shape

        # Inside pixels → red
        rgb_overlay = np.zeros(shape + (4,), dtype=np.uint8)
        inside_mask = ls_slice == self.inside_value
        rgb_overlay[inside_mask] = [255, 0, 0, opaque_level]


        # Create vtkImageData
        flat_rgba = rgb_overlay.reshape(-1, 4)
        vtk_array = numpy_support.numpy_to_vtk(flat_rgba, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
        image_data = vtk.vtkImageData()
        image_data.SetDimensions(shape[1], shape[0], 1)  # x, y, z dims
        image_data.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 4)
        image_data.GetPointData().SetScalars(vtk_array)
        image_data.SetSpacing(spacing)


        # Create new renderer once
        if not hasattr(self.LoadMRI, "bubble_renderer"):
            self.LoadMRI.bubble_renderer = {}
            for vn in 'axial','coronal','sagittal':
                vtk_widget = self.LoadMRI.vtk_widgets[vn]
                self.LoadMRI.bubble_renderer[vn] = vtk.vtkRenderer()
                vtk_widget.GetRenderWindow().SetNumberOfLayers(4)
                vtk_widget.GetRenderWindow().AddRenderer(self.LoadMRI.bubble_renderer[vn])
                vtk_widget.GetRenderWindow().Render()
                self.LoadMRI.bubble_renderer[vn].SetLayer(3)
                self.LoadMRI.bubble_renderer[vn].SetActiveCamera(vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera())

        #add actor
        actor_ax = vtk.vtkImageActor()
        actor_ax.GetMapper().SetInputData(image_data)
        actor_ax.SetOpacity(1)
        if opaque_level == 255:
            self.LoadMRI.bubble_renderer[view_name].AddActor(actor_ax)
        else:
            self.LoadMRI.renderers[view_name].AddActor(actor_ax)

        self.evolution_actors[view_name] = actor_ax


    def update_evolution(self):
        for vn in 'axial','coronal','sagittal':
            actor = self.evolution_actors[vn]
            self.LoadMRI.bubble_renderer[vn].RemoveActor(actor)
            self.LoadMRI.renderers[vn].RemoveActor(actor)
            self.visualize_level_set(vn,self.ls_array,255)

        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()


    def new_evolution(self):
        self.ls_array = self.initialize_level_set()
        for vn in 'axial','coronal','sagittal':
            actor = self.evolution_actors[vn]
            self.LoadMRI.bubble_renderer[vn].RemoveActor(actor)
            self.LoadMRI.renderers[vn].RemoveActor(actor)
            self.visualize_level_set(vn,self.ls_array,255)
        # make circles invisible
        for i,[_, actor,center,radius,c_px,_] in enumerate(self.SegInit.actor_bubble):
            actor.SetVisibility(0)
            actor.SetVisibility(0)
            actor_cirlce = self.SegInit.actor_selected[i]
            actor_cirlce[2].SetVisibility(0)
        #make selected circle lines invisible
        for i in 0,1,2:
            actor_cirlce = self.SegInit.actor_selected[i]
            actor_cirlce[2].SetVisibility(0)
        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()

    def update_evolution_initializtion(self,opqaue_level):
        for vn in 'axial','coronal','sagittal':
            actor = self.evolution_actors[vn]
            self.LoadMRI.bubble_renderer[vn].RemoveActor(actor)
            self.LoadMRI.renderers[vn].RemoveActor(actor)
            self.visualize_level_set(vn,self.ls_array,opqaue_level)
        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()

    def run_evolution(self):
        print('start evolution')
        # Set number of iterations
        n_iterations = 1000

        X_dim, Y_dim, Z_dim = self.LoadMRI.volume.shape

        # Create empty bubble mask
        bubble_mask = np.zeros_like(self.LoadMRI.volume, dtype=np.uint8)


        # Fill bubbles
        for i, (view_name, actor, center, radius, c_px, _) in enumerate(self.SegInit.actor_bubble):
            cx, cy, cz = c_px  # in voxel coordinates
            r = radius            # in voxels
            X, Y, Z = np.ogrid[:X_dim, :Y_dim, :Z_dim]
            mask = (X - cx)**2 + (Y - cy)**2 + (Z - cz)**2 <= r**2
            bubble_mask[mask] = 1


        mask_itk = sitk.GetImageFromArray(bubble_mask.astype(np.uint8))

        ##NEW
        print("start evolution")
        # -------------------------------
        # PARAMETERS
        n_iterations = 1000           # <- change this to control evolution length
        propagation_scaling = 0.7
        curvature_scaling = 0.5
        advection_scaling = 1.0
        dilation_radius = [2, 2, 2]   # voxels to optionally grow bubble
        intensity_threshold = 0.2     # optional threshold to limit growth
        sigma_gradient = 2.0          # gradient smoothing
        # -------------------------------

        X_dim, Y_dim, Z_dim = self.LoadMRI.volume.shape

        # -------------------------------
        # Create initial bubble mask (uint8)
        bubble_mask = np.zeros_like(self.LoadMRI.volume, dtype=np.uint8)
        for _, _, _, radius, c_px, _ in self.SegInit.actor_bubble:
            cx, cy, cz = c_px
            X, Y, Z = np.ogrid[:X_dim, :Y_dim, :Z_dim]
            mask = (X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2 <= radius ** 2
            bubble_mask[mask] = 1

        mask_itk = sitk.GetImageFromArray(bubble_mask)
        # -------------------------------
        # Optional: dilate bubble
        mask_itk = sitk.BinaryDilate(mask_itk, dilation_radius, sitk.sitkBall)

        # -------------------------------
        # Convert MRI to SimpleITK, rescale 0-1
        mri_itk = sitk.GetImageFromArray(self.LoadMRI.volume.astype(np.float32))
        mri_itk = sitk.RescaleIntensity(mri_itk, 0.0, 1.0)




        # Optional smoothing
        smoothing = sitk.CurvatureAnisotropicDiffusion(mri_itk, timeStep=0.0625, numberOfIterations=5)

        # -------------------------------
        # Feature image for geodesic level set
        gradient = sitk.GradientMagnitudeRecursiveGaussian(smoothing, sigma=sigma_gradient)
        gradient = sitk.RescaleIntensity(gradient, 0.0, 1.0)
        # Create intensity mask (stop bubble in low-intensity areas)
        feature_img = sitk.Cast(1.0 / (1.0 + gradient * 5.0), sitk.sitkFloat32)
        #intensity_mask = mri_itk > 0.2  # adjust threshold
        intensity_mask = sitk.Cast(mri_itk > 0.2, sitk.sitkFloat32)
        feature_img = sitk.Cast(feature_img * sitk.Cast(intensity_mask, sitk.sitkFloat32), sitk.sitkFloat32)


        # -------------------------------
        # Create initial level set
        # Inside bubble = negative, background = positive

        # Create signed distance map from mask
        mask_ls_np = np.where(sitk.GetArrayFromImage(mask_itk) > 0, -1.0, 1.0).astype(np.float32)
        mask_ls_itk = sitk.GetImageFromArray(mask_ls_np)

        initial_ls = sitk.SignedMaurerDistanceMap(
            mask_itk,
            insideIsPositive=True,  # True because bubble is negative (<0)
            useImageSpacing=True
        )
        initial_ls = sitk.Clamp(initial_ls, lowerBound=-5.0, upperBound=5.0)
        initial_ls = sitk.Cast(initial_ls, sitk.sitkFloat32)

        print("Initial LS min/max:", sitk.GetArrayFromImage(initial_ls).min(), sitk.GetArrayFromImage(initial_ls).max())

        # -------------------------------
        # Geodesic Active Contour Level Set
        geodesic_ls = sitk.GeodesicActiveContourLevelSetImageFilter()
        geodesic_ls.SetNumberOfIterations(n_iterations)
        geodesic_ls.SetPropagationScaling(propagation_scaling)
        geodesic_ls.SetCurvatureScaling(curvature_scaling)
        geodesic_ls.SetAdvectionScaling(advection_scaling)

        # Run evolution
        segmentation_itk = geodesic_ls.Execute(initial_ls, feature_img)

        # -------------------------------
        # Convert back to numpy (inside = 1, outside = 0)
        segmentation_np = (sitk.GetArrayFromImage(segmentation_itk) < 0).astype(np.uint8)
        print("Segmented voxels:", segmentation_np.sum())

        ##Small debug

        # Convert back to numpy
        #segmentation_np = (sitk.GetArrayFromImage(segmentation_itk) < 0).astype(np.uint8)
        print("Mask unique values before dilate:", np.unique(sitk.GetArrayFromImage(mask_itk)))
        print("Mask sum before dilate:", np.sum(sitk.GetArrayFromImage(mask_itk)))
        #arr_dilate = sitk.GetArrayFromImage(dilate)
        #print("Mask unique values after dilate:", np.unique(arr_dilate))
        #print("Mask sum after dilate:", np.sum(arr_dilate))


        ##OLD

        #threshold_mask_combined = np.maximum(self.LoadMRI.th_img, bubble_mask)
        #threshold_mask_combined = (threshold_mask_combined > 0).astype(np.float32)

        # Convert numpy arrays to SimpleITK images
        # Convert to float32
        #mri_float = self.LoadMRI.volume.astype(np.float32)

        ## Rescale to 0–1
        #mri_float = (mri_float - mri_float.min()) / (mri_float.max() - mri_float.min())

        ## Optional: slightly enhance contrast with power-law (gamma) correction
        #gamma = 1.5  # >1 increases contrast in midtones
        #mri_float = np.power(mri_float, gamma)

        ## Convert back to SimpleITK
        #mri_itk = sitk.GetImageFromArray(mri_float)
        #mri_itk = sitk.RescaleIntensity(mri_itk, outputMinimum=0.0, outputMaximum=1.0)


        ## Edge potential map: 1 / (1 + gradient)
        #smoothing = sitk.CurvatureAnisotropicDiffusion(mri_itk, timeStep=0.0625, numberOfIterations=5)
        #gradient = sitk.GradientMagnitudeRecursiveGaussian(smoothing, sigma=2.0)
        #gradient = sitk.Clamp(gradient, lowerBound=1e-5)
        #gradient = sitk.RescaleIntensity(gradient, 0.1, 1.0)
        ##feature_img = sitk.Cast(1.0 / (1.0 + gradient*10), sitk.sitkFloat32)
        #feature_img = sitk.Cast(1.0 / gradient, sitk.sitkFloat32)


        ## Create initial level set from the mask (distance map)
        #initial_ls = sitk.SignedMaurerDistanceMap(
        #    mask_itk,
        #    insideIsPositive=False, useImageSpacing=True
        #)
        #initial_ls = sitk.Clamp(initial_ls, lowerBound=-5.0, upperBound=5.0)
        #initial_ls = sitk.Cast(initial_ls, sitk.sitkFloat32)

        ## Geodesic Active Contour Level Set

        #geodesic_ls = sitk.GeodesicActiveContourLevelSetImageFilter()
        #geodesic_ls.SetNumberOfIterations(n_iterations)
        #geodesic_ls.SetPropagationScaling(1.0)
        #geodesic_ls.SetCurvatureScaling(0.5)
        #geodesic_ls.SetAdvectionScaling(1.0)

        ## Run level set
        ##segmentation_itk = geodesic_ls.Execute(initial_ls, smoothing)
        #segmentation_itk = geodesic_ls.Execute(initial_ls, feature_img)








        ## AXIAL
        slice_np = segmentation_np[1, :, :]
        vtk_slice_array = numpy_support.numpy_to_vtk(num_array=slice_np.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        vtk_slice_image = vtk.vtkImageData()
        vtk_slice_image.SetDimensions(slice_np.shape[1], slice_np.shape[0], 1)  # X, Y, 1 slice
        vtk_slice_image.GetPointData().SetScalars(vtk_slice_array)
        spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[1], 1)
        vtk_slice_image.SetSpacing(spacing)
        color_map = vtk.vtkImageMapToColors()
        color_map.SetInputData(vtk_slice_image)
        # Make all non-zero pixels red
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(2)
        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # background transparent
        lookup_table.SetTableValue(1, 1, 0, 0, 1)  # red, opaque
        lookup_table.Build()
        color_map.SetLookupTable(lookup_table)
        color_map.Update()
        actor_ax = vtk.vtkImageActor()
        actor_ax.GetMapper().SetInputData(vtk_slice_image)
        actor_ax.SetOpacity(1)
        actor_ax.GetMapper().SetInputData(color_map.GetOutput())
        renderer = self.LoadMRI.renderers['axial']
        #renderer.RemoveActor(self.Thres.vol_actors['axial'])
        renderer.AddActor(actor_ax)
        self.LoadMRI.vtk_widgets['axial'].GetRenderWindow().Render()

        ## CORONAL
        slice_np = segmentation_np[:, 32, :]
        vtk_slice_array = numpy_support.numpy_to_vtk(num_array=slice_np.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        vtk_slice_image = vtk.vtkImageData()
        vtk_slice_image.SetDimensions(slice_np.shape[1], slice_np.shape[0], 1)  # X, Y, 1 slice
        vtk_slice_image.GetPointData().SetScalars(vtk_slice_array)
        spacing = (self.LoadMRI.spacing[2], self.LoadMRI.spacing[0], 1)
        vtk_slice_image.SetSpacing(spacing)
        color_map = vtk.vtkImageMapToColors()
        color_map.SetInputData(vtk_slice_image)
        # Make all non-zero pixels red
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(2)
        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # background transparent
        lookup_table.SetTableValue(1, 1, 0, 0, 1)  # red, opaque
        lookup_table.Build()
        color_map.SetLookupTable(lookup_table)
        color_map.Update()
        actor_ax = vtk.vtkImageActor()
        actor_ax.GetMapper().SetInputData(vtk_slice_image)
        actor_ax.SetOpacity(1)
        actor_ax.GetMapper().SetInputData(color_map.GetOutput())
        renderer = self.LoadMRI.renderers['coronal']
        renderer.AddActor(actor_ax)
        self.LoadMRI.vtk_widgets['coronal'].GetRenderWindow().Render()

        ##SAGITTAL
        slice_np = np.fliplr(segmentation_np[:, :, 91].T)
        vtk_slice_array = numpy_support.numpy_to_vtk(num_array=slice_np.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        vtk_slice_image = vtk.vtkImageData()
        vtk_slice_image.SetDimensions(slice_np.shape[1], slice_np.shape[0], 1)  # X, Y, 1 slice
        vtk_slice_image.GetPointData().SetScalars(vtk_slice_array)
        spacing = (self.LoadMRI.spacing[0], self.LoadMRI.spacing[1], 1)
        vtk_slice_image.SetSpacing(spacing)
        color_map = vtk.vtkImageMapToColors()
        color_map.SetInputData(vtk_slice_image)
        # Make all non-zero pixels red
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(2)
        lookup_table.SetTableValue(0, 0, 0, 0, 0)  # background transparent
        lookup_table.SetTableValue(1, 1, 0, 0, 1)  # red, opaque
        lookup_table.Build()
        color_map.SetLookupTable(lookup_table)
        color_map.Update()
        actor_ax = vtk.vtkImageActor()
        actor_ax.GetMapper().SetInputData(vtk_slice_image)
        actor_ax.SetOpacity(1)
        actor_ax.GetMapper().SetInputData(color_map.GetOutput())
        renderer = self.LoadMRI.renderers['sagittal']
        #renderer.RemoveActor(self.Thres.vol_actors['axial'])
        renderer.AddActor(actor_ax)
        self.LoadMRI.vtk_widgets['sagittal'].GetRenderWindow().Render()

        print('finished')



