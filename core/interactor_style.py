# This Python file uses the following encoding: utf-8
import vtk
from utils.zoom import Zoom
from utils.zoom import zoom_notifier
from utils.scale_bar import Scale

class CustomInteractorStyle(vtk.vtkInteractorStyleImage):
    """
    Custom VTK interactor style for MRI views
    """
    def __init__(self, self_cursor, view_name, measurement):
        """
        Initialize the interactor style with cursor, view, and measurement objects.
        """
        super().__init__()

        self.Load_MRI = self_cursor.Load_MRI
        self.cursor = self_cursor
        self.view_name = view_name
        self.measurement = measurement

        # Interactor state flags
        self.dragging = False ##DELETEbar?
        self.dragging_minimap = False
        self.zooming = False
        self.pos_last = []

        # Add Observers
        self.AddObserver("LeftButtonPressEvent", self.on_left_button_down)
        self.AddObserver("LeftButtonReleaseEvent", self.on_left_button_up)
        self.AddObserver("RightButtonPressEvent", self.on_right_button_down)
        self.AddObserver("RightButtonReleaseEvent", self.on_right_button_up)
        self.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.AddObserver("MouseWheelForwardEvent", self.on_wheel_forward)
        self.AddObserver("MouseWheelBackwardEvent", self.on_wheel_backward)

    def on_left_button_down(self, obj, event):
        """
        Handle left mouse button press for measurements or cursor updates.
        """
        interactor = self.GetInteractor()
        x, y = interactor.GetEventPosition()
        picker = vtk.vtkPropPicker()
        renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()

        #Check if inside minimap rectangle
        if self.is_in_minimap_rect(x, y):
            self.dragging_minimap = True
        else:
            self.dragging = True
            # add measurement point if Measurement instance exists
            if self.measurement is not None:
                if picker.Pick(x, y, 0, renderer):
                    pos = picker.GetPickPosition()
                    voxel = [
                        int(round(pos[2] / self.Load_MRI.spacing[0])),
                        int(round(pos[1] / self.Load_MRI.spacing[1])),
                        int(round(pos[0] / self.Load_MRI.spacing[2]))
                    ]
                    self.measurement.add_point(voxel, self.view_name)
            else:
                # update cursor
                self.cursor.update_cursor_from_interactor(interactor, self.view_name)
        super().OnLeftButtonDown()

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
        super().OnLeftButtonUp()

    def on_mouse_move(self, obj, event):
        """
        Handle mouse movement for minimap dragging, zooming, or measurement preview.
        """
        interactor = self.GetInteractor()
        x, y = interactor.GetEventPosition()

        # Minimap dragging
        if self.is_in_minimap_rect(x, y) and self.dragging_minimap:
            rw, rh = self.Load_MRI.renderers[self.view_name].GetSize()
            if not hasattr(self, "last_pos"):
                self.last_pos = [rw/2,rh/2]
            (w_norm,h_norm) = self.Load_MRI.minimap.size_rectangle[self.view_name]
            new_x = max(0,min(1,(x/rw) / w_norm))
            new_y = max(0,min(1,(y/rh) / h_norm))
            self.Load_MRI.minimap.create_small_rectangle(None,vn=self.view_name,new_x=new_x,new_y=new_y)
            self.last_pos = [x,y]
            interactor.GetRenderWindow().Render()
        # Zooming with right mouse drag
        elif self.zooming:
            dy = y - self.pos_last[1]
            if dy == 0:
                return
            factor = 1.01**dy #realtive zooming
            self.pos_last = [x,y]

            for vn,widget in self.Load_MRI.vtk_widgets.items(): #zoom in/out in the other 2 images
                renderer = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                camera = renderer.GetActiveCamera()
                camera.ParallelProjectionOn()
                if vn != self.view_name:
                    camera.SetParallelScale(camera.GetParallelScale() / factor)
                    widget.GetRenderWindow().Render()

                self.Load_MRI.scale_bar[vn].update_bar(renderer, length_cm=1.0)

                cx, cy, cz = camera.GetFocalPoint()
                pos = camera.GetPosition()
                camera.SetPosition(cx, cy, pos[2])

                half_height = camera.GetParallelScale()
                width_px, height_px = renderer.GetSize()
                half_width = half_height * width_px / height_px
                Zoom.bounds[vn] = [cx - half_width, cx + half_width, cy - half_height, cy + half_height]
            Zoom.global_zoom_factor *= factor
            Zoom.factorChanged = factor
            zoom_notifier.factorChanged.emit(factor)
        #Measuring
        else:
            if self.dragging and self.measurement is None:
                self.cursor.update_cursor_from_interactor(self.GetInteractor(), self.view_name)
            elif self.measurement and self.measurement.start_voxel is not None and self.measurement.end_voxel is None:
                picker = vtk.vtkPropPicker()
                renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()
                if picker.Pick(x, y, 0, renderer):
                    pos = picker.GetPickPosition()
                    lm = self.Load_MRI

                    voxel = [
                        int(round(pos[2]/lm.spacing[0])),
                        int(round(pos[1]/lm.spacing[1])),
                        int(round(pos[0]/lm.spacing[2]))
                    ]
                    self.measurement.end_voxel_temp = voxel
                    self.measurement.draw_line(self.view_name, temporary=True)


        super().OnMouseMove()

    def on_wheel_forward(self, obj, event):
        """Scroll the slice forward when mouse wheel moves up."""
        self.cursor.scroll_slice(self.view_name, +3)
        obj.InvokeEvent("AbortEvent")
        return

    def on_wheel_backward(self, obj, event):
        """Scroll the slice backward when mouse wheel moves down."""
        self.cursor.scroll_slice(self.view_name, -3)
        obj.InvokeEvent("AbortEvent")
        return

    def on_right_button_up(self, obj, event):
        """Stop zooming when right mouse button is released."""
        self.zooming = False

        super().OnRightButtonUp()

    def on_right_button_down(self, obj, event):
        """Start zooming when right mouse button is pressed."""
        interactor = self.GetInteractor()
        x, y = interactor.GetEventPosition()

        if not self.is_in_minimap_rect(x, y):
            self.zooming = True
            self.pos_last = [x,y]
        super().OnRightButtonDown()


    def is_in_minimap_rect(self, x, y) -> bool:
        """
        Check if the display coordinates (x, y) are inside any of the mini-map rectangles.
        Returns true if inside, else false.
        """
        window_width, window_height = self.Load_MRI.renderers[self.view_name].GetSize()
        (w_norm,h_norm) = self.Load_MRI.minimap.size_rectangle[self.view_name]

        return 0 <= x/window_width <= w_norm*1.2 and 0 <= y/window_height <= h_norm*1.2



