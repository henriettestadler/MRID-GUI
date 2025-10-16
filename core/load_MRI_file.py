# This Python file uses the following encoding: utf-8

from PySide6.QtCore import QObject, Signal
import SimpleITK as sITK
import vtk
from vtk.util import numpy_support
import numpy as np
from utils.zoom import Zoom
from core.cursor import Cursor
from utils.scale_bar import Scale


class LoadMRI(QObject):
    """
    Handles loading, managing, and displaying MRI volumes (3D and 4D).
    """
    # Signals to ui
    fileLoaded = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Core volume data
        self.volume = {}
        self.timestamp4D = {}
        self.timestamp4D[0] = 0
        self.timestamp4D[1] = 4
        self.timestamp4D[2] = 8
        self.slice_indices = [0, 0, 0]  # z y x (for cursor +1)

        # GUI-related
        self.contrast_ui_elements = {}
        self.zoom_tf ={}
        self.img_vtks = {}
        self.img_vtks[0] = {}
        self.scale_bar = {}
        self.measurement_lines = []
        self.threshold_on = False
        self.measurement_renderer = {}

        # Rendering
        self.actors = {}
        self.renderers = {}
        self.actors[0] = {}
        self.renderers[0] = {}

        self.is_first_slice = True




    def load_file(self,vol_dim:int):
        """
        Initialize data structures after data is loaded.
        Emits `fileLoaded` signal once data is loaded.
        """

        self.num_images = 1
        # handle 4D volume and load it
        if self.volume[0].ndim == 4:
            self.num_images = 3
            self.volume4D = self.volume[0].copy()
            self.volume = {}
            for i in 1,2: #,3:
                self.volume[i] = sITK.GetArrayFromImage(self.image)
                self.renderers[i] = {}  # store vtkRenderer for each view
                self.actors[i] = {}
                self.img_vtks[i] = {}
            self.volume[0] = self.volume4D[self.timestamp4D[0], :, :, :] #echo 0
            self.volume[1] = self.volume4D[self.timestamp4D[1], :, :, :] #echo 4
            self.volume[2] = self.volume4D[self.timestamp4D[2], :, :, :] #echo 8
            self.spacing = [self.spacing[1],self.spacing[2],self.spacing[3]]


        # emit signal for MainWindow to update UI
        self.fileLoaded.emit(self.file_name, vol_dim)

        # Set-up first slide
        z, y, x = self.slice_indices
        for image_index,vtk_widget_image in self.vtk_widgets.items():
            if vol_dim ==3:
                self.setup_vtkdata(self.volume[0][z, :, :], vtk_widget_image["axial"], "axial",image_index)
            else:
                self.setup_vtkdata(self.volume[image_index][z, ::-1, ::-1], self.vtk_widgets[image_index]["axial"], "axial",image_index)
            self.setup_vtkdata(self.volume[0][:, y, :], vtk_widget_image["coronal"], "coronal",image_index)
            self.setup_vtkdata(np.fliplr(self.volume[0][:, :, x].T), vtk_widget_image["sagittal"], "sagittal",image_index)


        # Add scale_bar and minimap
        for view_name in 'axial','coronal','sagittal':
            renderer = self.renderers[0][view_name]
            if view_name not in self.scale_bar:
                self.scale_bar[view_name] = Scale(self,self.vol_dim)
            self.scale_bar[view_name].create_bar(renderer,view_name,length_cm=1.0)

        # initiate Cursor class
        self.cursor = Cursor(self, self.cursor_ui)
        self.cursor.start_cursor(True) #index = 0 at start


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
            spacing = (self.spacing[2], self.spacing[1], 1)
        elif view_name == "coronal": # y fixed -> (z,x)
            spacing = (self.spacing[2], self.spacing[0], 1)
        elif view_name == "sagittal":# x fixed -> (z,y)
            spacing = (self.spacing[0], self.spacing[1], 1)

        img_vtk.SetSpacing(spacing)
        img_vtk.GetPointData().SetScalars(vtk_data)

        # reuse renderer if exists, otherwise create one
        if view_name in self.actors[image_index]:
            renderer = self.renderers[image_index][view_name]
            renderer.RemoveActor(self.actors[image_index][view_name])
        else:
            renderer = vtk.vtkRenderer()
            vtk_widget.GetRenderWindow().AddRenderer(renderer)
            # higher quality
            vtk_widget.GetRenderWindow().SetMultiSamples(16)
            renderer.SetUseDepthPeeling(1)
            renderer.SetMaximumNumberOfPeels(200)
            renderer.SetOcclusionRatio(0.05)
            self.renderers[image_index][view_name] = renderer

            camera = renderer.GetActiveCamera()
            cx, cy, cz = camera.GetFocalPoint()
            pos = camera.GetPosition()
            camera.SetPosition(cx, cy, pos[2])
            half_height = camera.GetParallelScale()
            width_px, height_px = renderer.GetSize()
            half_width = half_height * width_px / height_px
            Zoom.bounds[view_name] = [cx - half_width, cx + half_width, cy - half_height, cy + half_height]

        # High-quality smoothing for better visual clarity
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(img_vtk)
        reslice.SetInterpolationModeToNearestNeighbor() #Cubic()  # Options: Nearest, Linear, Cubic
        reslice.Update()

        # Add image to actor to then be added to renderer
        actor = vtk.vtkImageActor()
        actor.SetInputData(reslice.GetOutput())
        actor.GetProperty().SetInterpolationTypeToNearest() #Linear()

        # Attach LUT for contrast and brightness
        prop = actor.GetProperty()
        prop.SetLookupTable(self.lut_vtk[image_index])
        prop.UseLookupTableScalarRangeOn()  # force LUT range

        renderer.AddActor(actor)

        #reset camera only at beginning
        if self.is_first_slice :
            renderer.ResetCamera()
            self.zoom_tf[view_name]=False
            if self.vol_dim ==3 and view_name == 'sagittal':
                self.is_first_slice = False
            elif self.vol_dim ==4 and view_name == 'sagittal' and image_index==3:
                self.is_first_slice = False

        #Update renderer
        vtk_widget.GetRenderWindow().Render()

        # Save actor, renderer, img_vtks to later be used again
        self.actors[image_index][view_name] = actor
        self.renderers[image_index][view_name] = renderer
        self.img_vtks[image_index][view_name] = img_vtk

        #Add axes to each widget
        self.add_axes(renderer, img_vtk, view_name)


        if image_index not in self.minimap.minimap_renderers:
            self.minimap.minimap_renderers[image_index] = {}
            self.minimap.minimap_actors[image_index] = {}
            self.minimap.minimap_borders[image_index] = {}
            self.minimap.zoom_rects[image_index] = {}

        self.minimap.add_minimap(view_name,img_vtk,image_index,vtk_widget)

    def only_display_slide(self, slice_img:np.array, view_name:str,image_index:int):
        """
        Update an existing vtkImageData with new scalar data for a given slice.
        """
        img_vtk = self.img_vtks[image_index][view_name]
        vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        img_vtk.GetPointData().SetScalars(vtk_data)
        img_vtk.Modified()
        self.actors[image_index][view_name].GetMapper().SetInputData(img_vtk)


    def update_slices(self,image_index:int):
        """
        Refresh all slice views (axial, coronal, sagittal) based on current slice indices.
        Handles threshold overlays and distance measurement visibility.
        """
        z, y, x = self.slice_indices.copy() if hasattr(self, 'slice_indices') else [0, 0, 0]

        #threshold ON or OFF
        if self.threshold_on == True:
            ThresholdSegmentation.only_update_displayed_image(self.ThresholdClass)
        else:
            if hasattr(self, "volume4D"):
                self.only_display_slide(self.volume[image_index][z, ::-1, ::-1], "axial",image_index) #image_index
            else:
                self.only_display_slide(self.volume[0][z, :, :], "axial",image_index)
            self.only_display_slide(self.volume[0][:, y, :], "coronal",image_index)
            self.only_display_slide(np.fliplr(self.volume[0][:, :, x].T), "sagittal",image_index)
        self.update_measurement_visibility()

        for _,vtk_widget_image in self.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()


    def update_measurement_visibility(self):
        """
        Show or hide measurement lines and text depending on whether they
        belong to the currently visible slice.
        """
        for view_name, line_actor,line_slice_index,text_actor in self.measurement_lines:
            renderer = self.measurement_renderer[view_name]
            if view_name == 'axial' and line_slice_index[0]==self.slice_indices[0]:
                renderer.AddActor(line_actor)
                text_actor.SetVisibility(1)
            elif view_name == 'coronal' and line_slice_index[1]==self.slice_indices[1]:
                renderer.AddActor(line_actor)
                text_actor.SetVisibility(1)
            elif view_name == 'sagittal' and line_slice_index[2]==self.slice_indices[2]:
                renderer.AddActor(line_actor)
                text_actor.SetVisibility(1)
            else:
                renderer.RemoveActor(line_actor)
                text_actor.SetVisibility(0)


    def on_threshold_changed(self, checked:bool,image_index:int):
        """Toggle threshold segmentation display."""
        if checked:
            self.threshold_on = True
        else:
            self.threshold_on = False
            self.update_slices(image_index)


    def timestamp4D_changed(self,index: int,image_index):
        """
        Update the current timestamp (4D volume selection).
        Called from MainWindow when combobox index changes.
        """
        self.timestamp4D[image_index] = int(index)
        self.volume[image_index] = None
        self.volume[image_index] = self.volume4D[self.timestamp4D[image_index], :, :, :]
        #self.contrastClass = Contrast(self)

        self.contrastClass.recompute_luttable(self.volume[image_index],image_index)

        #Refresh views
        z, y, x = self.slice_indices
        self.setup_vtkdata(self.volume[image_index][z, ::-1, ::-1], self.vtk_widgets[image_index]["axial"], "axial",image_index)
        self.setup_vtkdata(self.volume[image_index][:, y, :], self.vtk_widgets[image_index]["coronal"], "coronal",image_index)
        self.setup_vtkdata(np.fliplr(self.volume[image_index][:, :, x].T), self.vtk_widgets[image_index]["sagittal"], "sagittal",image_index)

        self.update_slices(image_index)


    def add_axes(self, renderer: vtk.vtkRenderer, img_vtk: vtk.vtkImageData, view_name:str):
        """
        Add L/R/A/P/S/I axes to the given view for orientation.
        """
        center = 0.5
        up = 0.9
        if view_name == "axial":      # slice in XY plane
            texts = [("L", 0.95, center),
                     ("R", 0.05, center),
                     ("S", center, up),
                     ("I", center, 0.05)]

        elif view_name == "coronal":  # slice in XZ plane
            texts = [("L", 0.95, center),
                     ("R", 0.05, center),
                     ("A", center, up),
                     ("P", center, 0.05)]

        elif view_name == "sagittal": # slice in YZ plane
            texts = [("P", 0.95, center),
                     ("A", 0.05, center),
                     ("S", center, up),
                     ("I", center, 0.05)]

        for text, x, y in texts:
            actor = vtk.vtkTextActor()
            actor.SetInput(text)
            prop = actor.GetTextProperty()
            if self.vol_dim == 4 and view_name != 'axial':
                prop.SetFontSize(10)
            else:
                prop.SetFontSize(16)
            prop.SetColor(1, 1, 0)  # red text
            prop.BoldOn()
            actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
            actor.SetPosition(x, y)

            renderer.AddActor2D(actor)
