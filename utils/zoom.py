# This Python file uses the following encoding: utf-8

from PySide6.QtCore import QObject, Signal
import vtk


class ZoomNotifier(QObject):
    """
    Emits a signal whenever the zoom factor changes.
    """
    factorChanged = Signal(float)

zoom_notifier = ZoomNotifier()


class Zoom:
    """
    Handles zooming and fit-to-window logic across multiple VTK views.

    Notes
    -----
    - Synchronizes zoom level across axial, sagittal, and coronal views.
    - Maintains scale bar consistency during zoom operations.
    - Uses Qt signals (`ZoomNotifier`) for UI updates.
    """
    global_zoom_factor: float = 1
    bounds: dict[int, dict[str, list[float]]] = {
        idx: {view: [] for view in ("axial", "sagittal", "coronal")}
        for idx in range(3)
    }

    @staticmethod
    def fit_to_window(vtk_widget, vtk_widgets:list, scale_bar:dict, vtk_widgets_dict:dict):
        """
        Reset and centers all views so the selected image fits the window (uniform zoom).
        Emits a signal with the updated zoom factor.
        """
        renderer = vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        camera.ParallelProjectionOn()

        # Save previous scale
        prev_scale = camera.GetParallelScale()

        # Compute bounds and center
        xmin, xmax, ymin, ymax, zmin, zmax = renderer.ComputeVisiblePropBounds()
        Zoom.cx, Zoom.cy, Zoom.cz = ((xmin + xmax)/2, (ymin + ymax)/2, (zmin + zmax)/2)

        width = xmax - xmin
        height = ymax - ymin
        aspect_window = vtk_widget.width() / vtk_widget.height()
        aspect_image = width / height

        # Compute factor to fit window
        if aspect_image > aspect_window:
            factor = width / (2 * aspect_window)
        else:
            factor = height / 2.0

        # Apply fit-to-window to selected widget and re-center it
        camera.SetFocalPoint(Zoom.cx, Zoom.cy, Zoom.cz)
        camera.SetParallelScale(factor)
        pos = camera.GetPosition()
        camera.SetPosition(Zoom.cx, Zoom.cy, pos[2])
        renderer.ResetCameraClippingRange()

        # Apply relative factor to the other views
        for image_index,vtk_widget_image in vtk_widgets_dict.items():
            for vn, widget in vtk_widget_image.items():
                if widget == vtk_widget:
                    if image_index==0:
                        view_name_other = Zoom.get_view_name(widget, vtk_widgets_dict)
                        scale_bar[view_name_other].update_bar(renderer,view_name_other,length_cm=1.0)
                        #Update zoom bounds
                        Zoom.update_bounds(view_name_other, camera, renderer)
                    # Update bounds
                    #Zoom.update_bounds(view_name, camera, renderer)
                    #scale_bar[view_name].update_bar(renderer,view_name, length_cm=1.0)
                    continue
                renderer_other = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                camera_other = renderer_other.GetActiveCamera()
                camera_other.ParallelProjectionOn()

                # Maintain relative zoom
                rel_factor = camera_other.GetParallelScale() / prev_scale
                camera_other.SetParallelScale(factor * rel_factor)

                # Center view on image
                xmin, xmax, ymin, ymax, zmin, zmax = renderer_other.ComputeVisiblePropBounds()
                target_center = ((xmin + xmax)/2.0, (ymin + ymax)/2.0, (zmin + zmax)/2.0)
                Zoom.recenter_camera_to_world_point(camera_other, target_center)

                renderer_other.ResetCameraClippingRange()

                if image_index==0:
                    view_name_other = Zoom.get_view_name(widget, vtk_widgets_dict)
                    scale_bar[view_name_other].update_bar(renderer_other,view_name_other,length_cm=1.0)
                    #Update zoom bounds
                    Zoom.update_bounds(view_name_other, camera_other, renderer_other)

        # Update Zoom.global_zoom_factor
        Zoom.global_zoom_factor = factor

        # Emit factor for UI updates
        zoom_notifier.factorChanged.emit(factor)

        for _,vtk_widget_image in vtk_widgets_dict.items():
            for _, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()


    @staticmethod
    def zoom(factor: float,scale_bar: dict,vtk_widgets_dict: dict):
        """
        Apply relative zoom while maintaining sync between views.
        """
        Zoom.global_zoom_factor *= factor

        for image_index,vtk_widget_image in vtk_widgets_dict.items():
            for vn, widget in vtk_widget_image.items():
                widget = vtk_widgets_dict[image_index][vn]
                renderer = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                camera = renderer.GetActiveCamera()
                camera.ParallelProjectionOn()

                camera.SetParallelScale(camera.GetParallelScale() / factor)
                cx, cy, cz = camera.GetFocalPoint()
                pos = camera.GetPosition()
                camera.SetPosition(cx, cy, pos[2])

                if image_index==0:
                    view_name = Zoom.get_view_name(widget,vtk_widgets_dict)
                    scale_bar[view_name].update_bar(renderer,view_name,length_cm=1.0)
                    half_height = camera.GetParallelScale()
                    width_px, height_px = renderer.GetSize()
                    half_width = half_height * width_px / height_px
                    Zoom.bounds[view_name] = [
                        cx - half_width, cx + half_width, cy - half_height, cy + half_height
                    ]


        for _,vtk_widget_image in vtk_widgets_dict.items():
            for _, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()

        zoom_notifier.factorChanged.emit(factor)

    @staticmethod
    def get_view_name(widget, vtk_widgets_dict: dict) -> str | None:
        """
        Return view name ('axial', 'sagittal', 'coronal') for a given widget.
        """
        for _,vtk_widget_image in vtk_widgets_dict.items():
           for name, w in vtk_widget_image.items():
                if w == widget:
                    return name
        return None

    @staticmethod
    def update_bounds(view_name:str, camera, renderer):
        """
        Update bounds dictionary for a given view.
        """
        half_height = camera.GetParallelScale()
        aspect = renderer.GetSize()[0] / renderer.GetSize()[1]
        half_width = half_height * aspect
        cx, cy, cz = camera.GetFocalPoint()
        xmin = cx - half_width
        xmax = cx + half_width
        ymin = cy - half_height
        ymax = cy + half_height
        Zoom.bounds[view_name] = [xmin, xmax, ymin, ymax]

    @staticmethod
    def recenter_camera_to_world_point(camera: vtk.vtkCamera, world_center: tuple[float,float,float]) -> None:
        """
        Set camera to look at world_center but preserve the camera's offset (position-focal).
        This keeps the camera direction/distance intact while centering on the new point.
        """
        old_fp = camera.GetFocalPoint()
        old_pos = camera.GetPosition()
        offset = (old_pos[0] - old_fp[0], old_pos[1] - old_fp[1], old_pos[2] - old_fp[2])

        cx, cy, cz = world_center
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetPosition(cx + offset[0], cy + offset[1], cz + offset[2])

