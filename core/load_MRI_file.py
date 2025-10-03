# This Python file uses the following encoding: utf-8

from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QObject, Signal
import SimpleITK as sITK
import vtk
from vtk.util import numpy_support
import numpy as np
from utils.contrast import Contrast
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
        self.volume = None
        self.timestamp4D = 0
        self.slice_indices = [0, 0, 0]  # z y x (for cursor +1)

        # GUI-related
        self.contrast_ui_elements = {}
        self.zoom_tf ={}
        self.img_vtks = {}
        self.scale_bar = {}
        self.measurement_lines = []
        self.threshold_on = False
        self.measurement_renderer = {}

        # Rendering
        self.actors = {}  # store vtkImageActor for each view
        self.renderers = {}  # store vtkRenderer for each view
        self.is_first_slice = True


    def load_file(self,vol_dim:int):
        """
        Open a file dialog, load a NIfTI file, and initialize data structures.
        Emits `fileLoaded` signal once data is loaded.
        """
        self.vol_dim = vol_dim #3D or 4D volume
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            "",
            "NIfTI files (*.nii.gz)"
        )

        #user cancelled
        if not file_name:
            return

        # Load volume
        self.image = sITK.ReadImage(file_name)
        self.volume = sITK.GetArrayFromImage(self.image)
        self.spacing = self.image.GetSpacing()[::-1]

        # handle 4D volume
        if self.volume.ndim == 4:
            self.volume4D = self.volume.copy()
            self.volume = self.volume[self.timestamp4D, :, :, :] #echo 0
            self.spacing = [self.spacing[1],self.spacing[2],self.spacing[3]]

        # emit signal for MainWindow to update UI
        self.fileLoaded.emit(file_name, vol_dim)

        # initialize Contrast class
        self.contrastClass = Contrast(self)

        # Set-up first slide
        z, y, x = self.slice_indices
        if self.vol_dim == 4:
            self.setup_vtkdata(self.volume[z, ::-1, ::-1], self.vtk_widgets["axial"], "axial")
        else:
            self.setup_vtkdata(self.volume[z, :, :], self.vtk_widgets["axial"], "axial")
        self.setup_vtkdata(self.volume[:, y, :], self.vtk_widgets["coronal"], "coronal")
        self.setup_vtkdata(np.fliplr(self.volume[:, :, x].T), self.vtk_widgets["sagittal"], "sagittal")

        # initiate Cursor class
        self.cursor = Cursor(self, self.cursor_ui)
        self.cursor.start_cursor(True) #index = 0 at start


    def setup_vtkdata(self,slice_img:np.array,vtk_widget, view_name:str):
        """
        Create or update the VTK pipeline for a given view (axial, coronal, sagittal).
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
        if view_name in self.actors:
            renderer = self.renderers[view_name]
            renderer.RemoveActor(self.actors[view_name])
        else:
            renderer = vtk.vtkRenderer()
            vtk_widget.GetRenderWindow().AddRenderer(renderer)
            # higher quality
            vtk_widget.GetRenderWindow().SetMultiSamples(16)
            renderer.SetUseDepthPeeling(1)
            renderer.SetMaximumNumberOfPeels(200)
            renderer.SetOcclusionRatio(0.05)
            self.renderers[view_name] = renderer

        # High-quality smoothing for better visual clarity
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(img_vtk)
        reslice.SetInterpolationModeToCubic()  # Options: Nearest, Linear, Cubic
        reslice.Update()

        # Add image to actor to then be added to renderer
        actor = vtk.vtkImageActor()
        actor.SetInputData(reslice.GetOutput())
        actor.GetProperty().SetInterpolationTypeToLinear()

        # Attach LUT for contrast and brightness
        prop = actor.GetProperty()
        prop.SetLookupTable(self.lut_vtk)
        prop.UseLookupTableScalarRangeOn()  # force LUT range

        renderer.AddActor(actor)

        #reset camera only at beginning
        if self.is_first_slice :
            renderer.ResetCamera()
            self.zoom_tf[view_name]=False
            if view_name == 'sagittal':
                self.is_first_slice = False

        #Update renderer
        vtk_widget.GetRenderWindow().Render()

        # Save actor, renderer, img_vtks to later be used again
        self.actors[view_name] = actor
        self.renderers[view_name] = renderer
        self.img_vtks[view_name] = img_vtk

        #Add axes to each widget
        self.add_axes(renderer, img_vtk, view_name)

        # Add scale_bar and minimap
        if view_name not in self.scale_bar:
            self.scale_bar[view_name] = Scale()
            self.scale_bar[view_name].create_bar(renderer, length_cm=1.0)
        self.minimap.add_minimap(view_name,img_vtk)


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
            prop.SetFontSize(16)
            prop.SetColor(1, 1, 0)  # red text
            prop.BoldOn()
            actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
            actor.SetPosition(x, y)

            renderer.AddActor2D(actor)


    def only_display_slide(self, slice_img:np.array, view_name:str):
        """
        Update an existing vtkImageData with new scalar data for a given slice.
        """
        img_vtk = self.img_vtks[view_name]
        vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        img_vtk.GetPointData().SetScalars(vtk_data)
        img_vtk.Modified()
        self.actors[view_name].GetMapper().SetInputData(img_vtk)


    def update_slices(self):
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
                self.only_display_slide(self.volume[z, ::-1, ::-1], "axial")
            else:
                self.only_display_slide(self.volume[z, :, :], "axial")
            self.only_display_slide(self.volume[:, y, :], "coronal")
            self.only_display_slide(np.fliplr(self.volume[:, :, x].T), "sagittal")
        self.update_measurement_visibility()

        for widget in self.vtk_widgets.values():
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


    def on_threshold_changed(self, checked:bool):
        """Toggle threshold segmentation display."""
        if checked:
            self.threshold_on = True
        else:
            self.threshold_on = False
            self.update_slices()


    def timestamp4D_changed(self,index: int):
        """
        Update the current timestamp (4D volume selection).
        Called from MainWindow when combobox index changes.
        """
        self.timestamp4D = int(index)
        self.volume = None
        self.volume = self.volume4D[self.timestamp4D, :, :, :]
        self.contrastClass = Contrast(self)
        #Refresh views
        z, y, x = self.slice_indices
        self.setup_vtkdata(self.volume[z, ::-1, ::-1], self.vtk_widgets["axial"], "axial")
        self.setup_vtkdata(self.volume[:, y, :], self.vtk_widgets["coronal"], "coronal")
        self.setup_vtkdata(np.fliplr(self.volume[:, :, x].T), self.vtk_widgets["sagittal"], "sagittal")

        self.update_slices()
