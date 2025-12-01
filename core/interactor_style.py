# This Python file uses the following encoding: utf-8
import vtk
from utils.zoom import Zoom
from utils.zoom import zoom_notifier

class CustomInteractorStyle(vtk.vtkInteractorStyleImage):
    """
    Custom VTK interactor style for MRI views
    """
    def __init__(self, self_cursor, view_name, image_index,measurement,data_index):
        """
        Initialize the interactor style with cursor, view, and measurement objects.
        """
        super().__init__()

        self.LoadMRI = self_cursor.LoadMRI
        self.cursor = self_cursor
        self.interactor_view_name = view_name
        self.interactor_data_index = data_index
        self.image_index = image_index
        self.measurement = measurement

        # Interactor state flags
        self.dragging = False
        self.panning = False
        self.dragging_minimap = False
        self.zooming = False
        self.pos_last = []
        self.LoadMRI.brush_on = False

        # Add Observers
        self.AddObserver("LeftButtonPressEvent", self.on_left_button_down)
        self.AddObserver("LeftButtonReleaseEvent", self.on_left_button_up)
        self.AddObserver("RightButtonPressEvent", self.on_right_button_down)
        self.AddObserver("RightButtonReleaseEvent", self.on_right_button_up)
        self.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.AddObserver("MouseWheelForwardEvent", self.on_wheel_forward)
        self.AddObserver("MouseWheelBackwardEvent", self.on_wheel_backward)
        self.AddObserver("MiddleButtonPressEvent", self.on_middle_button_down)
        self.AddObserver("MiddleButtonReleaseEvent", self.on_middle_button_up)

    def on_left_button_down(self, obj, event):
        """
        Handle left mouse button press for measurements or cursor updates.
        """
        interactor = self.GetInteractor()
        x, y = interactor.GetEventPosition()
        picker = vtk.vtkPropPicker()
        renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()

        picker.Pick(x, y, 0, renderer)
        if self.is_in_minimap_rect(x, y):
            # Start dragging rectangle to pan
            self.dragging_minimap = True
        elif self.LoadMRI.brush_on:
            self.dragging = True
            self.LoadMRI.paintbrush.mouse_moves(self.paintbrush_pos,self.dragging,self.interactor_view_name,self.interactor_data_index)
        else:
            self.dragging = True
            # add measurement point if Measurement instance exists
            if self.measurement is not None:
                if picker.Pick(x, y, 0, renderer):
                    pos = picker.GetPickPosition()
                    voxel = [
                        int(round(pos[2] / self.LoadMRI.spacing[self.interactor_data_index][0])),
                        int(round(pos[1] / self.LoadMRI.spacing[self.interactor_data_index][1])),
                        int(round(pos[0] / self.LoadMRI.spacing[self.interactor_data_index][2]))
                    ]
                    self.measurement.add_point(voxel, self.interactor_view_name)
                else:
                    return
            else:
                # update cursor
                self.cursor.update_cursor_from_interactor(interactor, self.interactor_view_name,self.interactor_data_index)

    def on_left_button_up(self, obj, event):
        """
        Handle left mouse button release, stop dragging minimap or cursor updates.
        """

        interactor = self.GetInteractor()
        x, y = interactor.GetEventPosition()

        if self.is_in_minimap_rect(x, y):
            self.dragging_minimap = False
        else:
            if self.measurement is None:
                self.dragging = False

    def on_mouse_move(self, obj, event):
        """
        Handle mouse movement for minimap dragging, zooming, or measurement preview.
        """
        interactor = self.GetInteractor()
        x, y = interactor.GetEventPosition()

        # Minimap dragging
        if self.is_in_minimap_rect(x, y) and self.dragging_minimap:
            rw, rh = self.LoadMRI.renderers[self.image_index][self.interactor_view_name].GetSize()
            if not hasattr(self, "last_pos"):
                self.last_pos = [rw/2,rh/2]
            (w_norm,h_norm) = self.LoadMRI.minimap.size_rectangle[self.image_index][self.interactor_view_name]
            new_x = max(0,min(1,(x/rw) / w_norm))
            new_y = max(0,min(1,(y/rh) / h_norm))
            self.LoadMRI.minimap.create_small_rectangle(zoom_factor=Zoom.global_zoom_factor,vn=self.interactor_view_name,new_x=new_x,new_y=new_y)
            self.last_pos = [x,y]
            interactor.GetRenderWindow().Render()
        elif self.panning:
            #make sure all images are zoomed in the same
            renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
            camera = renderer.GetActiveCamera()
            fp = camera.GetFocalPoint()
            pos = camera.GetPosition()

            for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for vn, widget in vtk_widget_image.items():
                    renderer = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                    camera = renderer.GetActiveCamera()
                    if vn == self.interactor_view_name and not image_index == self.image_index:
                        camera.SetFocalPoint(fp[0],fp[1],fp[2])
                        camera.SetPosition(pos[0],pos[1],pos[2])
                        widget.GetRenderWindow().Render()
            if len(self.LoadMRI.cursor.cursor_lines)==4:
                renderer = self.LoadMRI.renderers[3][self.interactor_view_name]
                camera = renderer.GetActiveCamera()
                camera.SetFocalPoint(fp[0],fp[1],fp[2])
                camera.SetPosition(pos[0],pos[1],pos[2])
                self.LoadMRI.vtk_widgets_heatmap[self.interactor_view_name].GetRenderWindow().Render()

            if self.LoadMRI.vol_dim==3:
                camera = self.LoadMRI.renderers[0]['axial'].GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera()
                Zoom.update_bounds('axial', camera, self.LoadMRI.renderers[self.image_index][self.interactor_view_name])
                camera = self.LoadMRI.renderers[0]['coronal'].GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera()
                Zoom.update_bounds('coronal', camera, self.LoadMRI.renderers[self.image_index][self.interactor_view_name])
                camera = self.LoadMRI.renderers[0]['sagittal'].GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera()
                Zoom.update_bounds('sagittal', camera, self.LoadMRI.renderers[self.image_index][self.interactor_view_name])
            zoom_notifier.factorChanged.emit(Zoom.global_zoom_factor)

        elif self.LoadMRI.brush_on:
            picker = vtk.vtkPropPicker()
            renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
            self.paintbrush_pos = None
            if picker.Pick(x, y, 0, renderer):
                view_name = self.interactor_view_name
                old_indices = self.LoadMRI.slice_indices[self.interactor_data_index].copy()
                pos = picker.GetPickPosition()  # VTK world coordinates
                # Update slice_indices depending on view
                if view_name == "axial" or (self.LoadMRI.vol_dim==4 and view_name=='coronal')or (self.LoadMRI.vol_dim==4 and view_name=='sagittal'):
                    xi = pos[0]/self.LoadMRI.spacing[self.interactor_data_index][2]
                    yi = pos[1]/self.LoadMRI.spacing[self.interactor_data_index][1]
                    zi = old_indices[0]
                elif view_name == "sagittal":
                    xi = old_indices[2]
                    yi = pos[1]/self.LoadMRI.spacing[self.interactor_data_index][1]
                    zi = self.LoadMRI.volume[0][0].shape[0]-1-pos[0]/self.LoadMRI.spacing[self.interactor_data_index][0]
                elif view_name == "coronal":
                    xi = pos[0]/self.LoadMRI.spacing[self.interactor_data_index][2]
                    yi = old_indices[1]
                    zi = pos[1]/self.LoadMRI.spacing[self.interactor_data_index][0]
                zi = max(0, min(zi, self.LoadMRI.volume[self.interactor_data_index][0].shape[0]-1))
                yi = max(0, min(yi, self.LoadMRI.volume[self.interactor_data_index][0].shape[1]-1))
                xi = max(0, min(xi, self.LoadMRI.volume[self.interactor_data_index][0].shape[2]-1))

                self.paintbrush_pos = [int(round(zi)),int(round(yi)),int(round(xi))]
                self.LoadMRI.paintbrush.mouse_moves(self.paintbrush_pos,self.dragging,self.interactor_view_name,self.interactor_data_index)
            else:
                return
        # Zooming with right mouse drag
        elif self.zooming:
            renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()

            camera = renderer.GetActiveCamera()
            scale = camera.GetParallelScale()
            pos = camera.GetPosition()
            fp = camera.GetFocalPoint()

            for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for vn, widget in vtk_widget_image.items():
                    renderer = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                    camera = renderer.GetActiveCamera()

                    if not (vn == self.interactor_view_name and image_index == self.image_index):
                        camera.ParallelProjectionOn()
                        pos_xy = camera.GetPosition()
                        fp_xy = camera.GetFocalPoint()
                        camera.SetParallelScale(scale)
                        camera.SetPosition(pos_xy[0],pos_xy[1],pos[2])
                        camera.SetFocalPoint(fp_xy[0],fp_xy[1],fp[2])
                        widget.GetRenderWindow().Render()
                        renderer.ResetCameraClippingRange()

            if len(self.LoadMRI.cursor.cursor_lines)==4:
                renderer = self.LoadMRI.renderers[3][view_name]
                camera = renderer.GetActiveCamera()
                camera.ParallelProjectionOn()
                pos_xy = camera.GetPosition()
                fp_xy = camera.GetFocalPoint()
                camera.SetParallelScale(scale)
                camera.SetPosition(pos_xy[0],pos_xy[1],pos[2])
                camera.SetFocalPoint(fp_xy[0],fp_xy[1],fp[2])
                self.LoadMRI.vtk_widgets_heatmap[view_name].GetRenderWindow().Render()

            if self.LoadMRI.vol_dim==3:
                camera = self.LoadMRI.renderers[0]['axial'].GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera()
                Zoom.update_bounds('axial', camera, self.LoadMRI.renderers[self.image_index][self.interactor_view_name])
                camera = self.LoadMRI.renderers[0]['coronal'].GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera()
                Zoom.update_bounds('coronal', camera, self.LoadMRI.renderers[self.image_index][self.interactor_view_name])
                camera = self.LoadMRI.renderers[0]['sagittal'].GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera()
                Zoom.update_bounds('sagittal', camera, self.LoadMRI.renderers[self.image_index][self.interactor_view_name])

            Zoom.global_zoom_factor = scale
            Zoom.factorChanged = scale
            zoom_notifier.factorChanged.emit(scale)

        #Measuring
        else:
            if self.dragging and self.measurement is None:
                self.cursor.update_cursor_from_interactor(self.GetInteractor(), self.interactor_view_name,self.interactor_data_index)
            elif self.measurement and self.measurement.start_voxel is not None and self.measurement.end_voxel is None:
                picker = vtk.vtkPropPicker()
                renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
                if picker.Pick(x, y, 0, renderer):
                    pos = picker.GetPickPosition()
                    lm = self.LoadMRI

                    voxel = [
                        int(round(pos[2]/lm.spacing[self.interactor_data_index][0])),
                        int(round(pos[1]/lm.spacing[self.interactor_data_index][1])),
                        int(round(pos[0]/lm.spacing[self.interactor_data_index][2]))
                    ]
                    self.measurement.end_voxel_temp = voxel
                    self.measurement.draw_line(self.interactor_view_name, temporary=True)
                else:
                    return

        super().OnMouseMove()

    def on_wheel_forward(self, obj, event):
        """Scroll the slice forward when mouse wheel moves up."""
        if self.LoadMRI.vol_dim==4:
            self.cursor.scroll_slice(self.interactor_view_name, +1,self.interactor_data_index)
        else:
            self.cursor.scroll_slice(self.interactor_view_name, +3,self.interactor_data_index)
        obj.InvokeEvent("AbortEvent")
        return

    def on_wheel_backward(self, obj, event):
        """Scroll the slice backward when mouse wheel moves down."""
        if self.LoadMRI.vol_dim==4:
            self.cursor.scroll_slice(self.interactor_view_name, -1,self.interactor_data_index)
        else:
            self.cursor.scroll_slice(self.interactor_view_name, -3,self.interactor_data_index)
        obj.InvokeEvent("AbortEvent")
        return

    def on_right_button_up(self, obj, event):
        """Stop zooming when right mouse button is released."""
        self.zooming = False
        #make sure all images are zoomed in the same
        renderer = self.LoadMRI.renderers[self.image_index][self.interactor_view_name].GetRenderWindow().GetRenderers().GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        scale = camera.GetParallelScale()
        fp = camera.GetFocalPoint()
        pos = camera.GetPosition()

        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for vn, widget in vtk_widget_image.items():
                renderer = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                camera = renderer.GetActiveCamera()
                if not (vn == self.interactor_view_name and image_index == self.image_index):
                    pos_xy = camera.GetPosition()
                    fp_xy = camera.GetFocalPoint()
                    camera.SetParallelScale(scale)
                    camera.SetFocalPoint(fp_xy[0],fp_xy[1],fp[2])
                    camera.SetPosition(pos_xy[0],pos_xy[1],pos[2])
                    widget.GetRenderWindow().Render()
                    renderer.ResetCameraClippingRange()

        if len(self.LoadMRI.cursor.cursor_lines)==4:
            renderer = self.LoadMRI.renderers[3][self.interactor_view_name]
            camera = renderer.GetActiveCamera()
            camera.ParallelProjectionOn()
            pos_xy = camera.GetPosition()
            fp_xy = camera.GetFocalPoint()
            camera.SetParallelScale(scale)
            camera.SetPosition(pos_xy[0],pos_xy[1],pos[2])
            camera.SetFocalPoint(fp_xy[0],fp_xy[1],fp[2])
            self.LoadMRI.vtk_widgets_heatmap[self.interactor_view_name].GetRenderWindow().Render()

        super().OnRightButtonUp()

    def on_right_button_down(self, obj, event):
        """Start zooming when right mouse button is pressed."""
        interactor = self.GetInteractor()
        x, y = interactor.GetEventPosition()
        renderer = self.LoadMRI.renderers[self.image_index][self.interactor_view_name].GetRenderWindow().GetRenderers().GetFirstRenderer()
        interactor.GetInteractorStyle().SetDefaultRenderer(renderer)
        camera = renderer.GetActiveCamera()
        self.scale_pre = camera.GetParallelScale()

        if not self.is_in_minimap_rect(x, y): # and self.dragging_minimap:
            self.zooming = True
            self.pos_last = [x,y]

        super().OnRightButtonDown()


    def is_in_minimap_rect(self, x, y) -> bool:
        """
        Check if the display coordinates (x, y) are inside any of the mini-map rectangles.
        Returns true if inside, else false.
        """
        if self.image_index==3:
            return
        window_width, window_height = self.LoadMRI.renderers[self.image_index][self.interactor_view_name].GetSize()
        (w_norm,h_norm) = self.LoadMRI.minimap.size_rectangle[self.image_index][self.interactor_view_name]

        return 0 <= x/window_width <= w_norm and 0 <= y/window_height <= h_norm


    def on_middle_button_down(self, obj, event):
        self.panning = True
        self.dragging = True

        super().OnMiddleButtonDown()


    def on_middle_button_up(self, obj, event):
        self.panning = False
        self.dragging = False

        #make sure all images are zoomed in the same
        renderer = self.LoadMRI.renderers[self.image_index][self.interactor_view_name].GetRenderWindow().GetRenderers().GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        fp = camera.GetFocalPoint()
        pos = camera.GetPosition()

        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for vn, widget in vtk_widget_image.items():
                renderer = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                camera = renderer.GetActiveCamera()
                if vn == self.interactor_view_name and not image_index == self.image_index:
                    camera.SetFocalPoint(fp[0],fp[1],fp[2])
                    camera.SetPosition(pos[0],pos[1],pos[2])
                    widget.GetRenderWindow().Render()
                    renderer.ResetCameraClippingRange()


        super().OnMiddleButtonUp()
