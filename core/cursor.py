# This Python file uses the following encoding: utf-8

import vtk
import numpy as np
from core.interactor_style import CustomInteractorStyle
#from add_ons import Zoom,zoom_notifier
#from paintbrush.paintbrush import Paintbrush

class Cursor:
    """
    Manages a crosshair cursor within MRI slice views.

    Responsibilities:
    -----------------
    - Synchronize cursor position with scrollbars and spinboxes.
    - Display crosshair lines in each VTK renderer.
    - Handle mouse dragging to move the cursor across slices.
    - Update voxel intensity readout at the current position.
    """
    def __init__(self, Load_MRI, ui_elements):
        """
        Initialize the cursor handler.
        """
        self.Load_MRI = Load_MRI
        self.ui = ui_elements
        self.dragging = False
        self.cursor_lines: dict[str,dict] = {}

        self.init_widgets()


    def init_widgets(self):
        """
        Initialize scrollbars and spinboxes, and connect signals to handlers.
        """
        lm = self.Load_MRI
        # spinboxes
        self.ui['spin_x'].setRange(1, lm.volume.shape[2])
        self.ui['spin_y'].setRange(1, lm.volume.shape[1])
        self.ui['spin_z'].setRange(1, lm.volume.shape[0])
        self.ui['spin_x'].valueChanged.connect(lambda val: self.cursor_coord_changed('x', val))
        self.ui['spin_y'].valueChanged.connect(lambda val: self.cursor_coord_changed('y', val))
        self.ui['spin_z'].valueChanged.connect(lambda val: self.cursor_coord_changed('z', val))

        # scrollbars
        self.ui['scroll_x'].setRange(0, lm.volume.shape[2]-1)
        self.ui['scroll_y'].setRange(0, lm.volume.shape[1]-1)
        self.ui['scroll_z'].setRange(0, lm.volume.shape[0]-1)
        self.ui['scroll_x'].valueChanged.connect(lambda val: self.scroll_slice('x', val))
        self.ui['scroll_y'].valueChanged.connect(lambda val: self.scroll_slice('y', val))
        self.ui['scroll_z'].valueChanged.connect(lambda val: self.scroll_slice('z', val))

        # Setup scrollbars based on volume shape
        self.ui['scroll_x'].setValue(self.Load_MRI.slice_indices[2])
        self.ui['scroll_x'].valueChanged.connect(lambda val: self.scroll_slice('x', 0,val=val))

        self.ui['scroll_y'].setValue(self.Load_MRI.slice_indices[1])
        self.ui['scroll_y'].valueChanged.connect(lambda val: self.scroll_slice('y', 0,val=val))

        self.ui['scroll_z'].setValue(self.Load_MRI.slice_indices[0])
        self.ui['scroll_z'].valueChanged.connect(lambda val: self.scroll_slice('z', 0,val=val))


    def update_cursor_display(self):
        """
        Update spinboxes, scrollbar and intensity display based on current cursor position.
        """
        lm = self.Load_MRI
        if not hasattr(lm, 'slice_indices') or lm.volume is None:
            return

        x, y, z = lm.slice_indices[2] + 1, lm.slice_indices[1] + 1, lm.slice_indices[0]+ 1
        intensity = lm.volume[lm.slice_indices[0],lm.slice_indices[1],lm.slice_indices[2]]

        # Block spinBox signals to avoid recursion
        for key in ['spin_x','spin_y','spin_z','scroll_x','scroll_y','scroll_z']:
            self.ui[key].blockSignals(True)

        self.ui['spin_x'].setValue(x)
        self.ui['spin_y'].setValue(y)
        self.ui['spin_z'].setValue(z)
        self.ui['scroll_x'].setValue(lm.slice_indices[2])
        self.ui['scroll_y'].setValue(lm.slice_indices[1])
        self.ui['scroll_z'].setValue(lm.slice_indices[0])
        self.ui['intensity'].display(round(float(intensity), 3))

        # Unblock signals
        for key in ['spin_x','spin_y','spin_z','scroll_x','scroll_y','scroll_z']:
            self.ui[key].blockSignals(False)

    def start_cursor(self,cursor_on:bool):
        """
        Enable or disable interactive cursor mode.

        If cursor_on=True, crosshair is visible and draggable.
        Otherwise, cursor is static (uses default interactor).
        """
        if cursor_on: #Cursor is usable
            self.create_cursor_lines()
            self.update_cursor_display()
            self.add_cursor_interaction()
            for view_name, vtk_widget in self.Load_MRI.vtk_widgets.items():
                interactor = vtk_widget.GetRenderWindow().GetInteractor()
                interactor.SetInteractorStyle(CustomInteractorStyle(self, view_name,None))
        else:
            # cursor visible but not changeable
            for vtk_widget in self.Load_MRI.vtk_widgets.values():
                interactor = vtk_widget.GetRenderWindow().GetInteractor()
                interactor.SetInteractorStyle(vtk.vtkInteractorStyleImage())


    def create_cursor_lines(self):
        """
        Create VTK actors for the crosshair lines in each slice view.
        """
        lm = self.Load_MRI

        if self.cursor_lines:
            return

        for view_name, vtk_widget in lm.vtk_widgets.items():
            renderer = vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
            line_h = vtk.vtkLineSource()
            line_v = vtk.vtkLineSource()
            line_h,line_v = self.set_line_points(view_name, line_h, line_v)

            mapper_h = vtk.vtkPolyDataMapper()
            mapper_h.SetInputConnection(line_h.GetOutputPort())
            actor_h = vtk.vtkActor()
            actor_h.SetMapper(mapper_h)
            actor_h.GetProperty().SetColor(0, 0, 1)
            renderer.AddActor(actor_h)

            mapper_v = vtk.vtkPolyDataMapper()
            mapper_v.SetInputConnection(line_v.GetOutputPort())
            actor_v = vtk.vtkActor()
            actor_v.SetMapper(mapper_v)
            actor_v.GetProperty().SetColor(0, 0, 1)
            renderer.AddActor(actor_v)

            self.cursor_lines[view_name] = {
                'horizontal': {'actor': actor_h, 'source': line_h},
                'vertical': {'actor': actor_v, 'source': line_v}
            }

        for vtk_widget in self.Load_MRI.vtk_widgets.values():
            vtk_widget.GetRenderWindow().Render()

    def update_cursor_lines(self):
        """
        Update positions of the crosshair lines based on slice indices.
        """
        lm = self.Load_MRI
        for view_name, vtk_widget in lm.vtk_widgets.items():
            line_h = self.cursor_lines[view_name]['horizontal']['source']
            line_v = self.cursor_lines[view_name]['vertical']['source']
            line_h,line_v = self.set_line_points(view_name, line_h, line_v)

            line_h.Modified()
            line_v.Modified()

        for vtk_widget in self.Load_MRI.vtk_widgets.values():
            vtk_widget.GetRenderWindow().Render()

    def set_line_points(self, view_name:str, line_h: vtk.vtkLineSource, line_v: vtk.vtkLineSource)-> tuple[vtk.vtkLineSource, vtk.vtkLineSource]:
        """
        Update the endpoints of the horizontal and vertical crosshair lines
        for the given view based on the current slice indices.
        Returns updated line sources as tuple[vtk.vtkLineSource, vtk.vtkLineSource]
        """
        lm = self.Load_MRI
        z = lm.slice_indices[0]*lm.spacing[0]
        y = lm.slice_indices[1]*lm.spacing[1]
        x = lm.slice_indices[2]*lm.spacing[2]
        height = 1
        if view_name == "axial":
            line_h.SetPoint1(0, y, height)
            line_h.SetPoint2((lm.volume.shape[2]-1)*lm.spacing[2], y, height)
            line_v.SetPoint1(x, 0, height)
            line_v.SetPoint2(x, (lm.volume.shape[1]-1)*lm.spacing[1], height)
        elif view_name == "coronal":
            line_h.SetPoint1(0, z, height)
            line_h.SetPoint2((lm.volume.shape[2]-1)*lm.spacing[2], z, height)
            line_v.SetPoint1(x, 0, height)
            line_v.SetPoint2(x, (lm.volume.shape[0]-1)*lm.spacing[0], height)
        elif view_name == "sagittal":
            line_h.SetPoint1(0, y, height)
            line_h.SetPoint2((lm.volume.shape[0]-1)*lm.spacing[0], y, height)
            line_v.SetPoint1((lm.volume.shape[0]-1)*lm.spacing[0]-z, 0, height)
            line_v.SetPoint2((lm.volume.shape[0]-1)*lm.spacing[0]-z, (lm.volume.shape[1]-1)*lm.spacing[1], height)

        return line_h,line_v


    def add_cursor_interaction(self):
        """
        Attach the custom interactor style to each view for cursor dragging.
        """
        for view_name, vtk_widget in self.Load_MRI.vtk_widgets.items():
            interactor = vtk_widget.GetRenderWindow().GetInteractor()
            interactor.SetInteractorStyle(CustomInteractorStyle(self,view_name,None))


    def start_drag(self, interactor, view_name:str):
        """Begin dragging the cursor."""
        self.dragging = True
        self.last_view = view_name
        self.update_cursor_from_interactor(interactor, view_name)

    def end_drag(self, view_name:str):
        """Stop dragging the cursor."""
        self.dragging = False


    def on_drag(self, interactor, view_name:str):
        """Update cursor while dragging."""
        if not self.dragging:
            return
        self.update_cursor_from_interactor(interactor, view_name)

    def update_cursor_from_interactor(self, interactor, view_name:str):
        """
        Pick world coordinates from the interactor, convert to voxel indices,
        and update the cursor position accordingly.
        """
        lm = self.Load_MRI
        old_indices = lm.slice_indices.copy()

        x, y = interactor.GetEventPosition()

        picker = vtk.vtkPropPicker()
        renderer = lm.renderers[view_name]
        suc = picker.Pick(x, y, 0, renderer)
        if suc:
            pos = picker.GetPickPosition()
            if view_name == "axial":
                xi = pos[0]/lm.spacing[2]
                yi = pos[1]/lm.spacing[1]
                zi = old_indices[0]
            elif view_name == "sagittal":
                xi = old_indices[2]
                yi = pos[1]/lm.spacing[1]
                zi = lm.volume.shape[0]-1-pos[0]/lm.spacing[0]
            elif view_name == "coronal":
                xi = pos[0]/lm.spacing[2]
                yi = old_indices[1]
                zi = pos[1]/lm.spacing[0]
                zi = max(0, min(zi, lm.volume.shape[0]-1))
                yi = max(0, min(yi, lm.volume.shape[1]-1))
                xi = max(0, min(xi, lm.volume.shape[2]-1))

            lm.slice_indices = [int(round(zi)),int(round(yi)),int(round(xi))]
        else:
            actor = lm.actors[view_name]
            xmin, xmax, ymin, ymax, zmin, _ = actor.GetBounds()

            corners = [
                (xmin, ymin, zmin),
                (xmax, ymin, zmin),
                (xmin, ymax, zmin),
                (xmax, ymax, zmin),

            ]

            disp_x = []
            disp_y = []

            for xw, yw, zw in corners:
                renderer.SetWorldPoint(xw, yw, zw, 1.0)
                renderer.WorldToDisplay()
                dx, dy, _ = renderer.GetDisplayPoint()
                disp_x.append(dx)
                disp_y.append(dy)

            if x < min(disp_x):
                x = min(disp_x)
            elif x > max(disp_x):
                x = max(disp_x)
            if y < min(disp_y):
                y = min(disp_y)
            elif y > max(disp_y):
                y = max(disp_y)

            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.005)
            suc_2 = picker.Pick(x, y, 0, renderer)

            if suc_2:
                pos = picker.GetPickPosition()
                if view_name == "axial":
                    xi = pos[0]/lm.spacing[2]
                    yi = pos[1]/lm.spacing[1]
                    zi = old_indices[0]
                elif view_name == "sagittal":
                    xi = old_indices[2]
                    yi = pos[1]/lm.spacing[1]
                    zi = lm.volume.shape[0]-1-pos[0]/lm.spacing[0]
                elif view_name == "coronal":
                    xi = pos[0]/lm.spacing[2]
                    yi = old_indices[1]
                    zi = pos[1]/lm.spacing[0]
                zi = max(0, min(zi, lm.volume.shape[0]-1))
                yi = max(0, min(yi, lm.volume.shape[1]-1))
                xi = max(0, min(xi, lm.volume.shape[2]-1))

                lm.slice_indices = [int(round(zi)),int(round(yi)),int(round(xi))]
            else:
                lm.slice_indices = old_indices

        # Refresh all
        lm.update_slices()
        self.update_cursor_display()
        self.update_cursor_lines()

    def scroll_slice(self, view_name:str, delta:int,val:int=-1):
        """
        Update cursor position from scrollbar.
        """
        lm = self.Load_MRI
        if val != -1:
            if view_name == 'z':
                lm.slice_indices[0] = np.clip(val, 0, lm.volume.shape[0]-1)
            elif view_name == 'y':
                lm.slice_indices[1] = np.clip(val, 0, lm.volume.shape[1]-1)
            elif view_name == 'x':
                lm.slice_indices[2] = np.clip(val, 0, lm.volume.shape[2]-1)
        else:
            if view_name == 'axial':
                lm.slice_indices[0] = np.clip(lm.slice_indices[0] + delta, 0, lm.volume.shape[0]-1)
            elif view_name == 'coronal':
                lm.slice_indices[1] = np.clip(lm.slice_indices[1] + delta, 0, lm.volume.shape[1]-1)
            elif view_name == 'sagittal':
                lm.slice_indices[2] = np.clip(lm.slice_indices[2] + delta, 0, lm.volume.shape[2]-1)

        lm.update_slices()
        self.update_cursor_display()
        self.update_cursor_lines()

    def cursor_coord_changed(self,axis:str, value:int):
        """
        Update cursor position when a spinbox value changes.
        """
        if axis == 'x':
            self.Load_MRI.slice_indices[2] = value -1
        elif axis == 'y':
            self.Load_MRI.slice_indices[1] = value -1
        elif axis == 'z':
            self.Load_MRI.slice_indices[0] = value -1

        # Refresh all
        self.Load_MRI.update_slices()
        self.update_cursor_display()
        self.update_cursor_lines()

