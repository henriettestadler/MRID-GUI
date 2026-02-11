# This Python file uses the following encoding: utf-8

import vtk
import numpy as np

class Measurement:
    """
    Handles distance measurements between two points in MRI volumes.

    Notes
    -----
    - Supports temporary (dynamic) and permanent measurements.
    - Converts voxel coordinates to physical space using voxel spacing.
    - Draws lines and distance labels in 3D VTK renderers.
    """
    def __init__(self, load_mri: object):
        """
        Initialize measurement handler.
        """
        self.load_mri = load_mri
        self.start_voxel = None #tuple[int, int, int]
        self.end_voxel = None #tuple[int, int, int]
        self.temp_line_actor = None # dynamic line vtk.vtkActor
        self.temp_text_actor = None # vtk.vtkBillboardTextActor3D


    def add_point(self, voxel: tuple[int, int, int], view_name:str):
        """
        Add a point in voxel coordinates.

        The first click sets the start point, the second click sets the end point and draws the measurement.
        """
        if self.start_voxel is None:
            self.start_voxel = voxel
        else:
            self.end_voxel = voxel
            self.draw_line(view_name)
            self.start_voxel = None

    def draw_line(self,view_name: str, temporary:bool=False):
        """
        Draw a line between start and end points.
        """
        if self.start_voxel is None:
            return

        # Convert voxel to physical coordinates
        if temporary:
            if not hasattr(self, 'end_voxel_temp'):
                return
            end_voxel = self.end_voxel_temp
        else:
            if self.end_voxel is None:
                return
            end_voxel = self.end_voxel

        # reuse line renderer if exists
        if view_name not in self.load_mri.measurement_renderer: # not in renderer_window:
            vtk_widget = self.load_mri.vtk_widgets[0][view_name]
            self.load_mri.measurement_renderer[view_name] = vtk.vtkRenderer()
            vtk_widget.GetRenderWindow().SetNumberOfLayers(3)
            vtk_widget.GetRenderWindow().AddRenderer(self.load_mri.measurement_renderer[view_name])
            self.load_mri.measurement_renderer[view_name].SetLayer(2)
            self.load_mri.measurement_renderer[view_name].SetActiveCamera(vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera())
            vtk_widget.GetRenderWindow().Render()

        measurement_renderer = self.load_mri.measurement_renderer[view_name]

        #Delete previous text and line if temporary
        measurement_renderer.RemoveActor(self.temp_line_actor)
        measurement_renderer.RemoveActor(self.temp_text_actor)

        # Convert voxel to physical coordinates
        start_point = np.array([
            self.start_voxel[2] * self.load_mri.spacing[0][2],
            self.start_voxel[1] * self.load_mri.spacing[0][1],
            self.start_voxel[0] * self.load_mri.spacing[0][0]
        ])
        end_point = np.array([
            end_voxel[2] * self.load_mri.spacing[0][2],
            end_voxel[1] * self.load_mri.spacing[0][1],
            end_voxel[0] * self.load_mri.spacing[0][0]
        ])

        #Create Line
        line = vtk.vtkLineSource()
        line.SetPoint1(start_point)
        line.SetPoint2(end_point)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, 0, 0)
        measurement_renderer.AddActor(actor)

        # Compute distance and midpoint
        midpoint = (start_point + end_point) / 2
        distance = round(np.linalg.norm(end_point-start_point),3)

        #Create Text
        text_actor = self.create_text_actor(midpoint, distance)

        if temporary:
            self.temp_line_actor = actor
            self.temp_text_actor = text_actor
            measurement_renderer.AddActor(text_actor)
        else:
            measurement_renderer.AddActor(text_actor)
            line_slice_index = [self.load_mri.slice_indices[0][0], self.load_mri.slice_indices[0][1], self.load_mri.slice_indices[0][2]]
            self.load_mri.measurement_lines.append((view_name, actor, line_slice_index, text_actor))
            self.temp_line_actor = None
            self.temp_text_actor = None
            self.start_voxel = None
            self.end_voxel = None

        # Store references for later
        self.load_mri.vtk_widgets[0][view_name].GetRenderWindow().Render()


    def create_text_actor(self, midpoint: np.ndarray, distance: float, color: tuple[float, float, float] =(1,0,0)) -> vtk.vtkBillboardTextActor3D:
        """
        Helper to create a text actor at a midpoint displaying the distance.

        Returns vtk.vtkBillboardTextActor3D
        """
        text_actor = vtk.vtkBillboardTextActor3D()
        text_actor.SetInput(f"{distance:.3f} mm")
        text_actor.SetPosition(midpoint)
        text_actor.GetTextProperty().SetColor(*color)
        text_actor.GetTextProperty().SetFontSize(10)
        text_actor.GetTextProperty().BoldOn()
        return text_actor


    def get_length_physical(self) -> float:
        """
        Return the physical distance (in mm) between the start and end measurement points.
        """
        if self.start_voxel is None or self.end_voxel is None:
            return 0.0
        start = np.array(self.start_voxel)
        end = np.array(self.end_voxel)
        spacing = np.array(self.load_mri.spacing[0][0])
        return np.linalg.norm((end - start) * spacing)
