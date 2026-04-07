# This Python file uses the following encoding: utf-8

import vtk
import numpy as np
from PySide6.QtGui import QStandardItemModel,QFont,QStandardItem
from PySide6.QtWidgets import QTableWidgetItem
import vtk
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QColor

class Measurement:
    """
    Handles distance measurements between two points in MRI volumes.

    Notes
    -----
    - Supports temporary (dynamic) and permanent measurements.
    - Converts voxel coordinates to physical space using voxel spacing.
    - Draws lines and distance labels in 3D VTK renderers.
    """
    def __init__(self, LoadMRI: object):
        """
        Initialize measurement handler.
        """
        self.LoadMRI = LoadMRI
        self.start_voxel = None #tuple[int, int, int]
        self.end_voxel = None #tuple[int, int, int]
        self.temp_line_actor = None # dynamic line vtk.vtkActor
        self.temp_text_actor = None # vtk.vtkBillboardTextActor3D
        self.color_index=0
        self.colors=[(1,0,0),(0,1,0),(0,1,1),(1,1,0),(1,0,1)]
        self.current_view_name = None


    def add_point(self, voxel: tuple[int, int, int], view_name:str):
        """
        Add a point in voxel coordinates.

        The first click sets the start point, the second click sets the end point and draws the measurement.
        """
        if self.start_voxel is None:
            self.start_voxel = voxel
            self.current_view_name = view_name
        else:
            self.end_voxel = voxel
            self.draw_line(view_name)
            self.start_voxel = None

    def draw_line(self,view_name: str, temporary:bool=False):
        """
        Draw a line between start and end points.
        """
        if self.current_view_name != view_name:
            return

        color = self.colors[self.color_index]
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
        if view_name not in self.LoadMRI.measurement_renderer: # not in renderer_window:
            vtk_widget = self.LoadMRI.vtk_widgets[0][view_name]
            self.LoadMRI.measurement_renderer[view_name] = vtk.vtkRenderer()
            vtk_widget.GetRenderWindow().SetNumberOfLayers(3)
            vtk_widget.GetRenderWindow().AddRenderer(self.LoadMRI.measurement_renderer[view_name])
            self.LoadMRI.measurement_renderer[view_name].SetLayer(1)
            self.LoadMRI.measurement_renderer[view_name].SetActiveCamera(vtk_widget.GetRenderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera())
            vtk_widget.GetRenderWindow().Render()

        measurement_renderer = self.LoadMRI.measurement_renderer[view_name]

        #Delete previous text and line if temporary
        measurement_renderer.RemoveActor(self.temp_line_actor)
        measurement_renderer.RemoveActor(self.temp_text_actor)

        # Convert voxel to physical coordinates
        start_point = np.array([
            self.start_voxel[2] * self.LoadMRI.spacing[0][2],
            self.start_voxel[1] * self.LoadMRI.spacing[0][1],
            self.start_voxel[0] * self.LoadMRI.spacing[0][0]
        ])
        end_point = np.array([
            end_voxel[2] * self.LoadMRI.spacing[0][2],
            end_voxel[1] * self.LoadMRI.spacing[0][1],
            end_voxel[0] * self.LoadMRI.spacing[0][0]
        ])

        #Create Line
        line = vtk.vtkLineSource()
        line.SetPoint1(start_point)
        line.SetPoint2(end_point)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
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
            line_slice_index = [self.LoadMRI.slice_indices[0][0], self.LoadMRI.slice_indices[0][1], self.LoadMRI.slice_indices[0][2]]
            #Create Line (start to start)
            line_ss = vtk.vtkLineSource()
            line_ss.SetPoint1(start_point)
            line_ss.SetPoint2(start_point)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(line_ss.GetOutputPort())
            actor_ss = vtk.vtkActor()
            actor_ss.SetMapper(mapper)
            actor_ss.GetProperty().SetColor(*color)
            actor_ss.GetProperty().SetLineStipplePattern(0xF0F0)  # pattern: 0xF0F0 = dashed
            actor_ss.GetProperty().SetLineStippleRepeatFactor(10)
            measurement_renderer.AddActor(actor_ss)

            #Create Line (end to end)
            line_ee = vtk.vtkLineSource()
            line_ee.SetPoint1(end_point)
            line_ee.SetPoint2(end_point)
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(line_ee.GetOutputPort())
            actor_ee = vtk.vtkActor()
            actor_ee.SetMapper(mapper)
            actor_ee.GetProperty().SetColor(1, 0, 0)
            #actor_ee.GetProperty().SetLineStipplePattern(0xF0F0)  # pattern: 0xF0F0 = dashed
            #actor_ee.GetProperty().SetLineStippleRepeatFactor(10)
            measurement_renderer.AddActor(actor_ee)
            dashed_lines = [line_ss,actor_ss,line_ee,actor_ee]
            points = vtk.vtkPoints()
            points.InsertNextPoint(start_point)
            points.InsertNextPoint(end_point)
            polydata = vtk.vtkPolyData()
            polydata.SetPoints(points)
            glyph = vtk.vtkVertexGlyphFilter()
            glyph.SetInputData(polydata)
            glyph.Update()
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(glyph.GetOutputPort())
            actor_p = vtk.vtkActor()
            actor_p.SetMapper(mapper)
            actor_p.GetProperty().SetColor(*color)  # red points
            actor_p.GetProperty().SetPointSize(8)
            measurement_renderer.AddActor(actor_p)
            points_array = [points, polydata,actor_p]
            self.LoadMRI.measurement_lines.append((view_name, actor, line_slice_index, text_actor,line,dashed_lines,points_array))
            self.add_to_table(view_name,distance)
            self.temp_line_actor = None
            self.temp_text_actor = None
            self.start_voxel = None
            self.end_voxel = None

        # Store references for later
        self.LoadMRI.vtk_widgets[0][view_name].GetRenderWindow().Render()



    def create_text_actor(self, midpoint: np.ndarray, distance: float) -> vtk.vtkBillboardTextActor3D:
        """
        Helper to create a text actor at a midpoint displaying the distance.

        Returns vtk.vtkBillboardTextActor3D
        """
        color = self.colors[self.color_index]
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
        spacing = np.array(self.LoadMRI.spacing[0][0])
        return np.linalg.norm((end - start) * spacing)

    def add_to_table(self,view_name:str,distance:float):
        #line
        #view
        #coordinate
        #length
        #tableWidget_meaurement
        # self.LoadMRI.measurement_table

        if view_name == 'axial':
            coordinate = f"z={str(self.LoadMRI.slice_indices[0][0]+1)}"
        elif view_name == 'coronal':
            coordinate = f"y={str(self.LoadMRI.slice_indices[0][1]+1)}"
        elif view_name == 'sagittal':
            coordinate = f"x={str(self.LoadMRI.slice_indices[0][2]+1)}"

        if self.LoadMRI.measurement_table.rowCount() == 0:
            self.LoadMRI.measurement_table.setColumnCount(4)
            self.LoadMRI.measurement_table.setHorizontalHeaderLabels(["","View", "Coordinate", "Length\n[mm]"])
            self.LoadMRI.measurement_table.setColumnWidth(0, 20)
            self.LoadMRI.measurement_table.setColumnWidth(1, 50)
            self.LoadMRI.measurement_table.setColumnWidth(2, 80)

        row = self.LoadMRI.measurement_table.rowCount()
        self.LoadMRI.measurement_table.insertRow(row)
        item = QTableWidgetItem()
        item.setBackground(QColor(255, 0, 0))  # red
        item.setText("")
        self.LoadMRI.measurement_table.setItem(row, 0, item)
        self.LoadMRI.measurement_table.setItem(row, 1, QTableWidgetItem(str(view_name.capitalize())))
        self.LoadMRI.measurement_table.setItem(row, 2, QTableWidgetItem(str(coordinate)))
        self.LoadMRI.measurement_table.setItem(row, 3, QTableWidgetItem(str(distance)))



    def delete_measurement(self):
        #self.LoadMRI.measurement_lines.append((view_name, actor, line_slice_index, text_actor,line))
        rows = self.LoadMRI.measurement_table.selectionModel().selectedRows()

        for index in range(len(rows)):
            selected_row = rows[0].row()

            [view_name, actor, line_slice_index, text_actor,line,dashed_lines,points] = self.LoadMRI.measurement_lines[selected_row]
            renderer = self.LoadMRI.measurement_renderer[view_name]
            renderer.RemoveActor(actor)
            renderer.RemoveActor(dashed_lines[1])
            renderer.RemoveActor(dashed_lines[3])
            renderer.RemoveActor(text_actor)
            renderer.RemoveActor(points[2])

            #remove from list (3 enteries)
            self.LoadMRI.measurement_lines.pop(selected_row)

            #remove from table
            self.LoadMRI.measurement_table.removeRow(selected_row)
            #self.LoadMRI.measurement_table.selectionModel().selectionChanged.connect(selected_row)

        #re-render
        self.LoadMRI.renderers[0][view_name].GetRenderWindow().Render()


    def change_color(self,index):
        selected_row = self.LoadMRI.measurement_table.selectionModel().selectedRows()[0].row()
        [view_name, actor, _, text_actor,_,dashed_lines,points] = self.LoadMRI.measurement_lines[selected_row]

        color = self.colors[self.color_index]

        #if index ==0:
        actor.GetProperty().SetColor(*color)
        dashed_lines[1].GetProperty().SetColor(*color)
        dashed_lines[3].GetProperty().SetColor(*color)
        text_actor.GetTextProperty().SetColor(*color)
        points[2].GetProperty().SetColor(*color)

        item = QTableWidgetItem()
        item.setBackground(QColor(*color))  # red
        item.setText("")
        self.LoadMRI.measurement_table.setItem(selected_row, 0, item)
        #re-render
        self.LoadMRI.renderers[0][view_name].GetRenderWindow().Render()



