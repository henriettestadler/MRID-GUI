# This Python file uses the following encoding: utf-8

from PySide6.QtCore import QObject
import vtk
from vtk.util import numpy_support
import numpy as np
from utils.zoom import Zoom
from utils.scale_bar import Scale
from core.mri_volume import MRIVolume
from gui_utils.intensity_table import IntensityTable
from utils.contrast import Contrast

class LoadMRI(QObject):
    """
    Handles loading, managing, and displaying MRI volumes (3D and 4D).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Core volume data
        self.volumes: dict[int, MRIVolume] = {}
        self.actors_non_mainimage = {}
        self.actors_non_mainimage[0] = {}
        self.slice_indices = {}
        self.slice_indices[0] = [0, 0, 0]  # z y x (for cursor +1)

        # GUI-related
        self.contrast_ui_elements = {}
        self.zoom_tf ={}
        self.zoom_tf['axial']=False
        self.zoom_tf['coronal']=False
        self.zoom_tf['sagittal']=False
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

        self.intensity_table: dict[int, IntensityTable] = {}
        self.contrast: dict[int, Contrast] = {}



    def load_file(self,data_view,data_index,first_time=True):
        """
        Initialize data structures after data is loaded.
        Emits `fileLoaded` signal once data is loaded.
        """
        # Set-up first slide
        z, y, x = self.slice_indices[data_index]
        if not self.volumes[0].is_4d:
            self.setup_vtkdata(self.volumes[data_index].slices[2][z, :, :], self.vtk_widgets[0]["axial"], "axial",0,data_index)
            self.setup_vtkdata(self.volumes[data_index].slices[0][:, y, :], self.vtk_widgets[0]["coronal"], "coronal",0,data_index)
            self.setup_vtkdata(np.fliplr(self.volumes[data_index].slices[1][:, :, x].T), self.vtk_widgets[0]["sagittal"], "sagittal",0,data_index)
        else:
            for image_index,vtk_widget_image in self.vtk_widgets.items():
                if data_view=='axial':
                    self.setup_vtkdata(self.volumes[data_index].slices[image_index][z, :, :], vtk_widget_image["axial"], "axial",image_index,data_index)
                elif data_view=='coronal':
                    self.setup_vtkdata(self.volumes[data_index].slices[image_index][z, :, :], vtk_widget_image["coronal"], "coronal",image_index,data_index)
                elif data_view=='sagittal':
                    self.setup_vtkdata(self.volumes[data_index].slices[image_index][z, :, :].T, vtk_widget_image["sagittal"], "sagittal",image_index,data_index)

        # Add scale_bar and minimap
        for view_name in 'axial','coronal','sagittal':
            if self.volumes[0].is_4d and data_view!=view_name:
                continue
            elif view_name in self.renderers[data_index]:
                renderer = self.renderers[data_index][view_name]
                if view_name not in self.scale_bar:
                    self.scale_bar[view_name] = Scale(self)
                self.scale_bar[view_name].create_bar(renderer,view_name,length_cm=1.0)

        if first_time:
            #fit to window to make it look nice
            if self.volumes[0].is_4d:
                Zoom.fit_to_window(self.vtk_widgets[0][data_view], self.vtk_widgets.values(), self.scale_bar, self.vtk_widgets, data_index)
            else: #3d
                Zoom.fit_to_window(self.vtk_widgets[0]["coronal"], self.vtk_widgets.values(), self.scale_bar, self.vtk_widgets, data_index)


    def setup_vtkdata(self,slice_img:np.array,vtk_widget, view_name:str,image_index:int,data_index:int,cam_reset:bool=True):
        """
        Create or update the VTK pipeline for a given view (axial, coronal  , sagittal).
        Handles reslice, actor creation, and LUT setup.
        """
        vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        img_vtk = vtk.vtkImageData()
        h, w = slice_img.shape
        img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth

        # Correct spacing per view
        if not self.volumes[0].is_4d:
            if view_name == "axial":      # z fixed -> (y,x)
                spacing = (self.volumes[data_index].spacing[2], self.volumes[data_index].spacing[1], 1)
            elif view_name == "coronal": # y fixed -> (z,x)
                spacing = (self.volumes[data_index].spacing[2], self.volumes[data_index].spacing[0], 1)
            elif view_name == "sagittal":# x fixed -> (z,y)
                spacing = (self.volumes[data_index].spacing[0], self.volumes[data_index].spacing[1], 1)
        else:
            spacing = (self.volumes[data_index].spacing[2], self.volumes[data_index].spacing[1], 1)

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
            if cam_reset:
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
        contrast_class = self.contrast[data_index]
        prop.SetLookupTable(contrast_class.lut_vtk[image_index])
        prop.UseLookupTableScalarRangeOn()  # force LUT range

        renderer.AddActor(actor)
        prop = actor.GetProperty()
        renderer.SetUseDepthPeeling(0)
        #reset camera only at beginning
        if self.is_first_slice:
            renderer.ResetCamera()
            self.zoom_tf[view_name]=False
            if not self.volumes[0].is_4d and view_name == 'sagittal':
                self.is_first_slice = False
            elif self.volumes[0].is_4d and view_name == 'sagittal' and image_index==3:
                self.is_first_slice = False

        # Save actor, renderer, img_vtks to later be used again
        self.actors[image_index][view_name] = actor
        self.renderers[image_index][view_name] = renderer
        self.img_vtks[image_index][view_name] = img_vtk

        #Add axes to each widget
        if self.volumes[0].is_4d:
            if view_name=='coronal':
                 self.add_axes(renderer, img_vtk, 'axial')
            else:
                self.add_axes(renderer, img_vtk, view_name)
        else:
            self.add_axes(renderer, img_vtk, view_name)

        self.minimap.add_minimap(view_name,img_vtk,image_index,vtk_widget,data_index)

        #Update renderer
        if cam_reset:
            vtk_widget.GetRenderWindow().Render()


    def only_display_slide(self, slice_img:np.array, view_name:str,image_index:int):
        """
        Update an existing vtkImageData with new scalar data for a given slice.
        """
        img_vtk = self.img_vtks[image_index][view_name]
        vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        img_vtk.GetPointData().SetScalars(vtk_data)
        img_vtk.Modified()
        self.actors[image_index][view_name].GetMapper().SetInputData(img_vtk)


    def update_slices(self,image_index:int,data_index,data_view):
        """
        Refresh all slice views (axial, coronal, sagittal) based on current slice indices.
        Handles threshold overlays and distance measurement visibility.
        """
        z, y, x = self.slice_indices[data_index].copy() if hasattr(self, 'slice_indices') else [0, 0, 0]
        #threshold ON or OFF

        if self.threshold_on == True:
            self.Segmentation.only_update_displayed_image()
        else:
            if not self.volumes[0].is_4d:
                self.only_display_slide(self.volumes[data_index].slices[image_index][:, y, :], "coronal",0)
                self.only_display_slide(np.fliplr(self.volumes[data_index].slices[image_index][:, :, x].T), "sagittal",0)
                self.only_display_slide(self.volumes[data_index].slices[image_index][z, :, :], "axial",0)
            else:
                if data_view=='sagittal':
                    self.only_display_slide(self.volumes[data_index].slices[image_index][z, :, :].T, data_view,image_index)
                else:
                    self.only_display_slide(self.volumes[data_index].slices[image_index][z, :, :], data_view,image_index)
        #3d volumes added
        if hasattr(self,"non_mainindex"):
            for i in range(self.non_mainindex+1):
                self.LoadImage3D.only_display_slide(self.LoadImage3D.vol[i][z, :, :], "axial",i)
                self.LoadImage3D.only_display_slide(self.LoadImage3D.vol[i][:, y, :], "coronal",i)
                self.LoadImage3D.only_display_slide(np.fliplr(self.LoadImage3D.vol[i][:, :, x].T), "sagittal",i)


        if hasattr(self, "SegEvolution"):
            self.SegEvolution.update_evolution_initializtion()
        elif hasattr(self,'SegInitialization'):
            self.SegInitialization.update_bubbles_visible()

        if hasattr(self,'paintbrush'): #label_volume
            img_vtk = self.paintbrush.vtk_label_images[data_view]
            #for view_name, img_vtk in self.paintbrush.vtk_label_images.items():
            # Axial view (XY plane at z)
            if data_view == 'axial' or (self.volumes[0].is_4d and data_view=="coronal") or self.volumes[0].is_4d and data_view=="sagittal":
                slice_img = self.paintbrush.label_volume[data_index][z, :, :]
            elif data_view == 'coronal':
                slice_img = self.paintbrush.label_volume[data_index][:, y, :]
            elif data_view == 'sagittal':
                slice_img = np.fliplr(self.paintbrush.label_volume[data_index][:, :, x].T)
            # Always flatten in Fortran order for VTK
            vtk_array = numpy_support.numpy_to_vtk(slice_img.ravel(),
                                                   deep=True,
                                                   array_type=vtk.VTK_UNSIGNED_CHAR)

            # Set scalars and refresh
            img_vtk.GetPointData().SetScalars(vtk_array)
            img_vtk.Modified()
            self.paintbrush.color_mappers[data_view].Update()
            for idx in range(len(self.renderers)):
                if idx==3:
                    return
                self.paintbrush.overlay_actors[data_view][idx].GetMapper().Update()
                self.paintbrush.lookup.SetRange(0, len(self.paintbrush.color_combobox)-1)
                actor = self.paintbrush.overlay_actors[data_view][idx]
                self.paintbrush.overlay_actors[data_view][idx] = actor

        if hasattr(self,'mrid_tags') and hasattr(self.mrid_tags,'actor_heatmap'):
            if data_view=='sagittal':
                slice_img = np.flip(self.mrid_tags.heatmap_slice[data_index][:, :, z],axis=0)
            else:
                slice_img = np.flip(self.mrid_tags.heatmap_slice[data_index][:, :, z].T)
            # Always flatten in Fortran order for VTK
            vtk_data = numpy_support.numpy_to_vtk(slice_img.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
            h, w = slice_img.shape
            spacing = (self.volumes[data_index].spacing[2], self.volumes[data_index].spacing[1], 1)
            img_vtk = vtk.vtkImageData()
            img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth
            img_vtk.SetSpacing(spacing)
            img_vtk.GetPointData().SetScalars(vtk_data)

            self.mrid_tags.actor_heatmap[data_index].SetInputData(img_vtk)
            self.mrid_tags.actor_heatmap[data_index].Modified()
            #self.vtk_widgets_heatmap['axial'].GetRenderWindow().Render()
            self.mrid_tags.add_legend(slice_img,False,data_index)

        self.update_measurement_visibility(data_index)

        for _,vtk_widget_image in self.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()


    def update_measurement_visibility(self,data_index):
        """
        Show or hide measurement lines and text depending on whether they
        belong to the currently visible slice.
        """
        for view_name, line_actor,line_slice_index,text_actor,_,dashed_lines,points in self.measurement_lines:
            renderer = self.measurement_renderer[view_name]
            if view_name == 'axial' and line_slice_index[0]==self.slice_indices[data_index][0]:
                renderer.AddActor(line_actor)
                renderer.AddActor(dashed_lines[1])
                renderer.AddActor(dashed_lines[3])
                text_actor.SetVisibility(1)
                renderer.AddActor(points[2])
            elif view_name == 'coronal' and line_slice_index[1]==self.slice_indices[data_index][1]:
                renderer.AddActor(line_actor)
                renderer.AddActor(dashed_lines[1])
                renderer.AddActor(dashed_lines[3])
                text_actor.SetVisibility(1)
                renderer.AddActor(points[2])
            elif view_name == 'sagittal' and line_slice_index[2]==self.slice_indices[data_index][2]:
                renderer.AddActor(line_actor)
                renderer.AddActor(dashed_lines[1])
                renderer.AddActor(dashed_lines[3])
                text_actor.SetVisibility(1)
                renderer.AddActor(points[2])
            else:
                renderer.RemoveActor(line_actor)
                renderer.RemoveActor(dashed_lines[1])
                renderer.RemoveActor(dashed_lines[3])
                text_actor.SetVisibility(0)
                renderer.RemoveActor(points[2])


    def on_threshold_changed(self, checked:bool,image_index:int,data_index:int,data_view:str):
        """Toggle threshold segmentation display."""
        if checked:
            self.threshold_on = True
        else:
            self.threshold_on = False
            self.update_slices(image_index,data_index,data_view)


    def timestamp4D_changed(self,index: int,image_index,data_index,data_view):
        """
        Update the current timestamp (4D volume selection).
        Called from MainWindow when combobox index changes.
        """
        scale = {}
        fp = {}
        pos = {}
        vol = self.volumes[data_index]

        renderer = self.renderers[image_index][data_view].GetRenderWindow().GetRenderers().GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        scale[data_view] = camera.GetParallelScale()
        fp[data_view] = camera.GetFocalPoint()
        pos[data_view] = camera.GetPosition()
        vol.timestamp4D[image_index] = int(index)
        vol.slices[image_index] = vol.array_4d[vol.timestamp4D[image_index], :, :, :].copy() #echo 8

        self.contrast[data_index].recompute_luttable(image_index,data_index)

        camera.SetParallelScale(scale[data_view])
        camera.SetFocalPoint(fp[data_view])
        camera.SetPosition(pos[data_view])

        self.update_slices(image_index,data_index,data_view)


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
            if self.volumes[0].is_4d and view_name != 'axial':
                prop.SetFontSize(10)
            else:
                prop.SetFontSize(16)
            prop.SetColor(1, 1, 0)  # red text
            prop.BoldOn()
            actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
            actor.SetPosition(x, y)

            renderer.AddActor2D(actor)
