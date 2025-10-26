# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
from vtkmodules.vtkFiltersSources import vtkRegularPolygonSource
from vtkmodules.vtkRenderingCore import vtkActor,vtkPolyDataMapper,vtkProperty
from PySide6.QtGui import QStandardItemModel,QFont,QStandardItem
#from PySide6.QtWidgets import QHeaderView
import numpy as np

class SegmentationInitialization:
    def __init__(self,LoadMRI):
        super().__init__()

        self.LoadMRI = LoadMRI
        self.actor_bubble = []
        self.index = 0
        self.selected = False
        self.actor_selected = []

        #Use threshold image
        self.th_img = self.LoadMRI.th_img

    def get_bubble_center(self,view_name):
        if view_name == "axial":      # z fixed -> (x,y)
            self.center = [
                self.LoadMRI.slice_indices[2]*self.LoadMRI.spacing[0][2],
                self.LoadMRI.slice_indices[1]*self.LoadMRI.spacing[0][1],
                1.1 #otherwise not visible
            ]
        elif view_name == "coronal": # y fixed -> (z,x)
            self.center = [
                self.LoadMRI.slice_indices[2]*self.LoadMRI.spacing[0][2],
                self.LoadMRI.slice_indices[0]*self.LoadMRI.spacing[0][0],
                1.1 #otherwise not visible
            ]
        elif view_name == "sagittal":# x fixed -> (y,z)
            self.center = [
                (self.LoadMRI.volume[0][0].shape[0]-self.LoadMRI.slice_indices[0])*self.LoadMRI.spacing[0][0],
                self.LoadMRI.slice_indices[1]*self.LoadMRI.spacing[0][1],
                1.1 #otherwise not visible
            ]
        self.center_px = self.LoadMRI.slice_indices


    def row_selected(self,selected,deselected):
        for ix in selected.indexes():
            self.row_index = ix.row()
            self.selected = True
            self.update_bubbles_visible()
            break

    def draw_bubble(self,push_btn):
        for view_name in 'axial','sagittal','coronal':
            #Get cursor position
            self.get_bubble_center(view_name)

            polygonSource = vtkRegularPolygonSource()
            polygonSource.GeneratePolygonOn()
            polygonSource.SetNumberOfSides(100)
            polygonSource.SetRadius(self.radius)
            polygonSource.SetCenter(self.center)

            mapper = vtkPolyDataMapper()
            mapper.SetInputConnection(polygonSource.GetOutputPort())

            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(1,0,0)
            actor.GetProperty().SetOpacity(0.3)

            renderer = self.LoadMRI.renderers[0][view_name]
            renderer.AddActor(actor)
            self.LoadMRI.renderers[0][view_name].GetRenderWindow().Render()
            self.actor_bubble.append([view_name,actor,self.center,self.radius,self.center_px,polygonSource])

            self.create_circle_around_selected_bubble(view_name,self.radius,self.center)

        self.selected = True
        row = self.model.rowCount()
        self.row_index = row
        self.model.insertRow(row)
        self.model.setItem(row,0, QStandardItem(str(self.center_px[2]+1)))
        self.model.setItem(row,1, QStandardItem(str(self.center_px[1]+1)))
        self.model.setItem(row,2, QStandardItem(str(self.center_px[0]+1)))
        self.model.setItem(row,3, QStandardItem(str(self.radius)))
        self.index += 1

        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()

        if not push_btn.isEnabled():
            push_btn.setEnabled(True)


    def create_table(self,table):
        self.table = table
        self.model = QStandardItemModel(0,4)
        self.model.setHorizontalHeaderLabels(["X","Y","Z","Radius"])
        header_font = QFont()
        header_font.setBold(True)

        self.table.setModel(self.model)

        self.table.setColumnWidth(0,35)
        self.table.setColumnWidth(1,35)
        self.table.setColumnWidth(2,35)
        self.table.setColumnWidth(3,60)

        self.table.horizontalHeader().setFont(header_font)
        self.table.verticalHeader().setVisible(False)
        self.table.show()


    def create_circle_around_selected_bubble(self,view_name,radius,center):
        for i,[view_name, actor,center,radius,c_px,_] in enumerate(self.actor_bubble):
            if i < len(self.actor_bubble)-1:
                #actor.SetVisibility(0)
                actor_cirlce = self.actor_selected[i]
                actor_cirlce[2].SetVisibility(0)

        polygonSource = vtkRegularPolygonSource()
        polygonSource.GeneratePolygonOff()
        polygonSource.SetNumberOfSides(100)
        polygonSource.SetRadius(radius)
        polygonSource.SetCenter(center)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(polygonSource.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1,0,0)
        actor.GetProperty().SetOpacity(1)

        renderer = self.LoadMRI.renderers[0][view_name]
        renderer.AddActor(actor)
        self.actor_selected.append([view_name,self.index,actor,polygonSource])

    def update_bubbles_visible(self):
        for i,[view_name, actor,center,radius,c_px,_] in enumerate(self.actor_bubble):
            # Correct spacing per view
            if view_name == "axial":      # z fixed -> (x,y)
                distance = (self.LoadMRI.slice_indices[0] - c_px[0])*self.LoadMRI.spacing[0][0]
            elif view_name == "sagittal":# x fixed -> (z,y)
                distance = (self.LoadMRI.slice_indices[2] - c_px[2])*self.LoadMRI.spacing[0][2]
            elif view_name == "coronal": # y fixed -> (x,z)
                distance = (self.LoadMRI.slice_indices[1] - c_px[1])*self.LoadMRI.spacing[0][1]

            if radius > abs(distance):
                actor.SetVisibility(1)
                radius_new = np.sqrt(radius**2-distance**2)
                self.update_bubble_radius(i, radius_new)
            else:
                #Make invisible: Actor and Outline-Circle
                actor.SetVisibility(0)
                actor_cirlce = self.actor_selected[i]
                actor_cirlce[2].SetVisibility(0)


        for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, widget in vtk_widget_image.items():
                widget.GetRenderWindow().Render()


    def update_bubble_radius(self, index, new_radius):
        actor_entry = self.actor_bubble[index]
        polygonSource = actor_entry[5]
        polygonSource.SetRadius(new_radius)
        polygonSource.Modified()

        #circles of selected bubbles
        if self.row_index == int(index/3) and self.selected:
            actor_entry = self.actor_selected[index]
            actor_entry[2].SetVisibility(1)
            polygonSource = actor_entry[3]
            polygonSource.SetRadius(new_radius)
            polygonSource.Modified()
        else:
            actor_entry = self.actor_selected[index]
            actor_entry[2].SetVisibility(0)





