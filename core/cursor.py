# This Python file uses the following encoding: utf-8

import vtk
import numpy as np
from core.interactor_style import CustomInteractorStyle

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
    def __init__(self, LoadMRI, ui_elements,data_index,data_view):
        """
        Initialize the cursor handler.
        """
        self.LoadMRI = LoadMRI
        self.ui = ui_elements
        self.dragging = False

        #create cursor lines
        self.cursor_lines = {}
        self.create_cursor_lines(data_index,data_view)
        self.init_widgets(data_index,data_view)



    def init_widgets(self,data_index,data_view):
        """
        Initialize scrollbars and spinboxes, and connect signals to handlers.
        """
        lm = self.LoadMRI
        # spinboxes
        spin_x = lm.cursor_ui[f"spin_x{data_index}"]
        spin_y = lm.cursor_ui[f"spin_y{data_index}"]
        spin_z = lm.cursor_ui[f"spin_z{data_index}"]
        spin_x.setRange(1, lm.volume[data_index][0].shape[2])
        spin_y.setRange(1, lm.volume[data_index][0].shape[1])
        spin_z.setRange(1, lm.volume[data_index][0].shape[0])
        spin_x.valueChanged.connect(lambda val: self.cursor_coord_changed('x', val,data_index,data_view))
        spin_y.valueChanged.connect(lambda val: self.cursor_coord_changed('y', val,data_index,data_view))
        spin_z.valueChanged.connect(lambda val: self.cursor_coord_changed('z', val,data_index,data_view))

        # scrollbars
        if self.LoadMRI.vol_dim==3:
            self.ui["scroll_2"].setRange(0, lm.volume[data_index][0].shape[0]-1)
            self.ui["scroll_2"].setValue(self.LoadMRI.slice_indices[data_index][0])
            self.ui["scroll_2"].valueChanged.connect(lambda val: self.scroll_slice('axial', 0,data_index,val=val))
            self.ui["scroll_1"].setRange(0, lm.volume[data_index][0].shape[2]-1)
            self.ui["scroll_1"].setValue(self.LoadMRI.slice_indices[data_index][0])
            self.ui["scroll_1"].valueChanged.connect(lambda val: self.scroll_slice('sagittal', 0,data_index,val=val))
            self.ui["scroll_0"].setRange(0, lm.volume[data_index][0].shape[1]-1)
            self.ui["scroll_0"].setValue(self.LoadMRI.slice_indices[data_index][0])
            self.ui["scroll_0"].valueChanged.connect(lambda val: self.scroll_slice('coronal', 0,data_index,val=val))
        else:
            self.ui[f"scroll_{data_index}"].setRange(0, lm.volume[data_index][0].shape[0]-1)
            self.ui[f"scroll_{data_index}"].setValue(self.LoadMRI.slice_indices[data_index][0])
            self.ui[f"scroll_{data_index}"].valueChanged.connect(lambda val: self.scroll_slice(data_view, 0,data_index,val=val))

    def update_cursor_display(self,data_index):
        """
        Update spinboxes, scrollbar and intensity display based on current cursor position.
        """
        lm = self.LoadMRI
        if not hasattr(lm, 'slice_indices') or lm.volume is None:
            return
        indices = lm.slice_indices[data_index].copy()
        x, y, z = indices[2] + 1, indices[1] + 1, indices[0]+ 1
        spin_x = lm.cursor_ui[f"spin_x{data_index}"]
        spin_y = lm.cursor_ui[f"spin_y{data_index}"]
        spin_z = lm.cursor_ui[f"spin_z{data_index}"]
        spin_x.blockSignals(True)
        spin_y.blockSignals(True)
        spin_z.blockSignals(True)

        for key in [f"scroll_{data_index}"]:
            self.ui[key].blockSignals(True)

        # Block spinBox signals to avoid recursion
        if self.LoadMRI.vol_dim==3:
            spin_x.setValue(x)
            spin_y.setValue(y)
            spin_z.setValue(z)
            self.ui['scroll_0'].setValue(lm.slice_indices[data_index][1])
            self.ui['scroll_1'].setValue(lm.slice_indices[data_index][2])
            self.ui['scroll_2'].setValue(lm.slice_indices[data_index][0])
        else:
            spin_x.setValue(x)
            spin_y.setValue(y)
            spin_z.setValue(z)
            self.ui[f"scroll_{data_index}"].setValue(lm.slice_indices[data_index][0])

        if hasattr(self.LoadMRI, f"intensity_table{data_index}"):
            table_class = getattr(self.LoadMRI, f"intensity_table{data_index}")
            table_class.update_intensity_values(data_index)

        # Unblock signals
        spin_x.blockSignals(False)
        spin_y.blockSignals(False)
        spin_z.blockSignals(False)
        for key in [f"scroll_{data_index}"]:
            self.ui[key].blockSignals(False)

    def start_cursor(self,cursor_on:bool,data_index,data_view):
        """
        Enable or disable interactive cursor mode.

        If cursor_on=True, crosshair is visible and draggable.
        Otherwise, cursor is static (uses default interactor).
        """

        if cursor_on: #Cursor is usable
            print('Cursor init start cursor')
            self.create_cursor_lines(data_index,data_view)
            self.update_cursor_display(data_index)
            self.add_cursor_interaction(data_index)
        else:
            # cursor visible but not changeable
            for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, vtk_widget in vtk_widget_image.items():
                    interactor = vtk_widget.GetRenderWindow().GetInteractor()
                    interactor.SetInteractorStyle(vtk.vtkInteractorStyleImage())
            if hasattr(self.LoadMRI, 'vtk_widgets_heatmap'):
                vtk_widget = self.LoadMRI.vtk_widgets_heatmap[view_name]
                interactor = vtk_widget.GetRenderWindow().GetInteractor()
                interactor.SetInteractorStyle(vtk.vtkInteractorStyleImage())


    def create_cursor_lines(self,data_index,data_view):
        """
        Create VTK actors for the crosshair lines in each slice view.
        """
        lm = self.LoadMRI
        if data_view in self.cursor_lines:
            return

        print('hier in cursor lines',self.cursor_lines, data_view)

        if self.LoadMRI.vol_dim==3:
            image_index =0
            for view_name in 'coronal','sagittal','axial':
                self.cursor_lines[view_name] = {}
                renderer = self.LoadMRI.renderers[image_index][view_name]
                line_h = vtk.vtkLineSource()
                line_v = vtk.vtkLineSource()
                line_h,line_v = self.set_line_points(view_name, line_h, line_v,data_index)

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

                self.cursor_lines[view_name][image_index] = {
                    'horizontal': {'actor': actor_h, 'source': line_h},
                    'vertical': {'actor': actor_v, 'source': line_v}
                }
        else:
            self.cursor_lines[data_view] = {}
            for image_index,vtk_widget_image in lm.vtk_widgets.items():
                for view_name, vtk_widget in vtk_widget_image.items():
                    if data_view==view_name:
                        renderer = self.LoadMRI.renderers[image_index][view_name]
                        line_h = vtk.vtkLineSource()
                        line_v = vtk.vtkLineSource()
                        line_h,line_v = self.set_line_points(view_name, line_h, line_v,data_index)

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

                        self.cursor_lines[view_name][image_index] = {
                            'horizontal': {'actor': actor_h, 'source': line_h},
                            'vertical': {'actor': actor_v, 'source': line_v}
                        }

        for image_index,vtk_widget_image in lm.vtk_widgets.items():
            for idx, (view_name, vtk_widget) in enumerate(vtk_widget_image.items()):
                vtk_widget.GetRenderWindow().Render()

    def update_cursor_lines(self,data_index):
        """
        Update positions of the crosshair lines based on slice indices.
        """
        lm = self.LoadMRI
        for image_index,vtk_widget_image in lm.vtk_widgets.items():
            if image_index==3:
                continue
            for idx, (view_name, vtk_widget) in enumerate(vtk_widget_image.items()):
                if idx == data_index or self.LoadMRI.vol_dim==3: #only change cursor of the corresponding view
                    line_h = self.cursor_lines[view_name][image_index]['horizontal']['source']
                    line_v = self.cursor_lines[view_name][image_index]['vertical']['source']
                    line_h,line_v = self.set_line_points(view_name, line_h, line_v,data_index)

                    line_h.Modified()
                    line_v.Modified()

        for image_index,vtk_widget_image in lm.vtk_widgets.items():
            for view_name, vtk_widget in vtk_widget_image.items():
                vtk_widget.GetRenderWindow().Render()

    def set_line_points(self, view_name:str, line_h: vtk.vtkLineSource, line_v: vtk.vtkLineSource,data_index,height = 1)-> tuple[vtk.vtkLineSource, vtk.vtkLineSource]:
        """
        Update the endpoints of the horizontal and vertical crosshair lines
        for the given view based on the current slice indices.
        Returns updated line sources as tuple[vtk.vtkLineSource, vtk.vtkLineSource]
        """
        lm = self.LoadMRI

        z = lm.slice_indices[data_index][0]*lm.spacing[data_index][0]
        y = lm.slice_indices[data_index][1]*lm.spacing[data_index][1]
        x = lm.slice_indices[data_index][2]*lm.spacing[data_index][2]

        if view_name == "axial" or (self.LoadMRI.vol_dim==4 and view_name=="coronal"):
            if self.LoadMRI.axes_to_flip[data_index][1]==False:
                line_h.SetPoint1(0, y, height)
                line_h.SetPoint2((lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2], y, height)
            else:
                line_h.SetPoint1(0, (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1]-y, height)
                line_h.SetPoint2((lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2], (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1]-y, height)
            if self.LoadMRI.axes_to_flip[data_index][0]==False:
                line_v.SetPoint1(x, 0, height)
                line_v.SetPoint2(x, (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1], height)
            else:
                line_v.SetPoint1((lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2]-x, 0, height)
                line_v.SetPoint2((lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2]-x, (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1], height)
        elif view_name == "coronal":
            if self.LoadMRI.axes_to_flip[data_index][2]==False:
                line_h.SetPoint1(0, z, height)
                line_h.SetPoint2((lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2], z, height)
            else:
                line_v.SetPoint1((lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0]-z, 0, height)
                line_v.SetPoint2((lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0]-z, (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1], height)
            if self.LoadMRI.axes_to_flip[data_index][0]==False:
                line_v.SetPoint1(x, 0, height)
                line_v.SetPoint2(x, (lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0], height)
            else:
                line_v.SetPoint1((lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2]-x, 0, height)
                line_v.SetPoint2((lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2]-x, (lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0], height)
        elif (self.LoadMRI.vol_dim==4 and view_name=="sagittal"):
            if self.LoadMRI.axes_to_flip[data_index][1]==True:
                line_v.SetPoint1((lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1]-y,0, height)
                line_v.SetPoint2((lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1]-y,(lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2], height)
            else:
                line_v.SetPoint1(y, 0, height)
                line_v.SetPoint2(y,(lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2], height)
            if self.LoadMRI.axes_to_flip[data_index][0]==True:
                line_h.SetPoint1(0,(lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2]-x, height)
                line_h.SetPoint2((lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1], (lm.volume[data_index][0].shape[2]-1)*lm.spacing[data_index][2]-x, height)
            else:
                line_h.SetPoint1(0, x, height)
                line_h.SetPoint2((lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1], x, height)
        elif view_name == "sagittal":
            if self.LoadMRI.axes_to_flip[data_index][1]==False:
                line_h.SetPoint1(0, y, height)
                line_h.SetPoint2((lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0], y, height)
            else:
                line_h.SetPoint1(0, (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1]-y, height)
                line_h.SetPoint2((lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0], (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1]-y, height)
            if self.LoadMRI.axes_to_flip[data_index][2]==False:
                line_v.SetPoint1((lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0]-z, 0, height)
                line_v.SetPoint2((lm.volume[data_index][0].shape[0]-1)*lm.spacing[data_index][0]-z, (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1], height)
            else:
                line_v.SetPoint1(z, 0, height)
                line_v.SetPoint2(z, (lm.volume[data_index][0].shape[1]-1)*lm.spacing[data_index][1], height)

        return line_h,line_v


    def add_cursor_interaction(self,data_index):
        """
        Attach the custom interactor style to each view for cursor dragging.
        """
        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for idx, (view_name, vtk_widget) in enumerate(vtk_widget_image.items()):
                if data_index==idx or self.LoadMRI.vol_dim==3:
                    interactor = vtk_widget.GetRenderWindow().GetInteractor()
                    interactor.SetInteractorStyle(CustomInteractorStyle(self,view_name,image_index,None,data_index))

                    if hasattr(self.LoadMRI, 'vtk_widgets_heatmap'):
                        vtk_widget = self.LoadMRI.vtk_widgets_heatmap[view_name]
                        interactor = vtk_widget.GetRenderWindow().GetInteractor()
                        interactor.SetInteractorStyle(CustomInteractorStyle(self, view_name,image_index,None,idx))

    def update_cursor_from_interactor(self, interactor, view_name:str,data_index):
        """
        Pick world coordinates from the interactor, convert to voxel indices,
        and update the cursor position accordingly.
        """
        lm = self.LoadMRI
        old_indices = lm.slice_indices[data_index].copy()

        x, y = interactor.GetEventPosition()

        picker = vtk.vtkPropPicker()
        renderer = interactor.GetRenderWindow().GetRenderers().GetFirstRenderer()

        suc = picker.Pick(x, y, 0, renderer)

        if suc:
            pos = picker.GetPickPosition()
            if view_name == "axial" or (self.LoadMRI.vol_dim==4 and view_name=='coronal'):
                if lm.axes_to_flip[data_index][0]==False:
                    xi = pos[0]/lm.spacing[data_index][2]
                else:
                    xi = lm.volume[data_index][0].shape[2]-1-pos[0]/lm.spacing[data_index][2]
                if lm.axes_to_flip[data_index][1]==False:
                    yi = pos[1]/lm.spacing[data_index][1]
                else:
                    yi = lm.volume[data_index][0].shape[1]-1-pos[1]/lm.spacing[data_index][1]
                zi = old_indices[0]
            elif (self.LoadMRI.vol_dim==4 and view_name=='sagittal'):
                if lm.axes_to_flip[data_index][0]==False:
                    xi = pos[1]/lm.spacing[data_index][1]
                else:
                    xi = lm.volume[data_index][0].shape[1]-1-pos[1]/lm.spacing[data_index][1]
                if lm.axes_to_flip[data_index][1]==False:
                    yi = pos[0]/lm.spacing[data_index][2]
                else:
                    yi = lm.volume[data_index][0].shape[2]-1-pos[0]/lm.spacing[data_index][2]
                zi = old_indices[0]
            elif view_name == "sagittal":
                xi = old_indices[2]
                if lm.axes_to_flip[data_index][1]==False:
                    yi = pos[1]/lm.spacing[data_index][1]
                else:
                    yi = lm.volume[data_index][0].shape[1]-1-pos[1]/lm.spacing[data_index][1]
                if lm.axes_to_flip[data_index][2]==False:
                    zi = lm.volume[data_index][0].shape[0]-1-pos[0]/lm.spacing[data_index][0]
                else:
                    zi = pos[0]/lm.spacing[data_index][0]
            elif view_name == "coronal":
                if lm.axes_to_flip[data_index][0]==False:
                    xi = pos[0]/lm.spacing[data_index][2]
                else:
                    xi = lm.volume[data_index][0].shape[2]-1-pos[0]/lm.spacing[data_index][2]
                yi = old_indices[1]
                if lm.axes_to_flip[data_index][2]==False:
                    zi = pos[1]/lm.spacing[data_index][0]
                else:
                    zi = lm.volume[data_index][0].shape[0]-1-pos[1]/lm.spacing[data_index][0]

            zi = max(0, min(zi, lm.volume[data_index][0].shape[0]-1))
            yi = max(0, min(yi, lm.volume[data_index][0].shape[1]-1))
            xi = max(0, min(xi, lm.volume[data_index][0].shape[2]-1))
            lm.slice_indices[data_index] = [int(round(zi)),int(round(yi)),int(round(xi))]
        else:
            actor = lm.actors[0][view_name] #image index
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
                if view_name == "axial" or (self.LoadMRI.vol_dim==4 and view_name=='coronal'):
                    if lm.axes_to_flip[data_index][0]==False:
                        xi = pos[0]/lm.spacing[data_index][2]
                    else:
                        xi = lm.volume[data_index][0].shape[2]-1-pos[0]/lm.spacing[data_index][2]
                    if lm.axes_to_flip[data_index][1]==False:
                        yi = pos[1]/lm.spacing[data_index][1]
                    else:
                        yi = lm.volume[data_index][0].shape[1]-1-pos[1]/lm.spacing[data_index][1]
                    zi = old_indices[0]
                elif self.LoadMRI.vol_dim==4 and view_name=='sagittal':
                    if lm.axes_to_flip[data_index][0]==False:
                        xi = pos[1]/lm.spacing[data_index][1]
                    else:
                        xi = lm.volume[data_index][0].shape[1]-1-pos[1]/lm.spacing[data_index][1]
                    if lm.axes_to_flip[data_index][1]==False:
                        yi = pos[0]/lm.spacing[data_index][2]
                    else:
                        yi = lm.volume[data_index][0].shape[2]-1-pos[0]/lm.spacing[data_index][2]
                    zi = old_indices[0]
                elif view_name == "sagittal":
                    xi = old_indices[2]
                    if lm.axes_to_flip[data_index][1]==False:
                        yi = pos[1]/lm.spacing[data_index][1]
                    else:
                        yi = lm.volume[data_index][0].shape[1]-1-pos[1]/lm.spacing[data_index][1]
                    if lm.axes_to_flip[data_index][2]==False:
                        zi = lm.volume[data_index][0].shape[0]-1-pos[0]/lm.spacing[data_index][0]
                    else:
                        zi = pos[0]/lm.spacing[data_index][0]
                elif view_name == "coronal":
                    if lm.axes_to_flip[data_index][0]==False:
                        xi = pos[0]/lm.spacing[data_index][2]
                    else:
                        xi = lm.volume[data_index][0].shape[2]-1-pos[0]/lm.spacing[data_index][2]
                    yi = old_indices[1]
                    if lm.axes_to_flip[data_index][2]==False:
                        zi = pos[1]/lm.spacing[data_index][0]
                    else:
                        zi = lm.volume[data_index][0].shape[0]-1-pos[1]/lm.spacing[data_index][0]
                zi = max(0, min(zi, lm.volume[data_index][0].shape[0]-1))
                yi = max(0, min(yi, lm.volume[data_index][0].shape[1]-1))
                xi = max(0, min(xi, lm.volume[data_index][0].shape[2]-1))

                lm.slice_indices[data_index] = [int(round(zi)),int(round(yi)),int(round(xi))]
            else:
                lm.slice_indices[data_index] = old_indices

        # Refresh all
        if lm.vol_dim== 3:
            lm.update_slices(0,data_index,view_name)
        else:
            for i in 0,1,2:
                lm.update_slices(i,data_index,view_name)

        self.update_cursor_display(data_index)
        if view_name not in self.cursor_lines:
            print('suc 1 2')
            self.create_cursor_lines(data_index,view_name)
        self.update_cursor_lines(data_index)

    def scroll_slice(self, view_name:str, delta:int,data_index,val:int=-1):
        """
        Update cursor position from scrollbar.
        """
        lm = self.LoadMRI
        if val != -1:
            if view_name == 'axial' or (self.LoadMRI.vol_dim==4 and view_name=='coronal') or (self.LoadMRI.vol_dim==4 and view_name=='sagittal'):
                lm.slice_indices[data_index][0] = np.clip(val, 0, lm.volume[data_index][0].shape[0]-1)
            elif view_name == 'coronal':
                lm.slice_indices[data_index][1] = np.clip(val, 0, lm.volume[data_index][0].shape[1]-1)
            elif view_name == 'sagittal':
                lm.slice_indices[data_index][2] = np.clip(val, 0, lm.volume[data_index][0].shape[2]-1)
        else:
            if view_name == 'axial' or (self.LoadMRI.vol_dim==4 and view_name=='coronal') or (self.LoadMRI.vol_dim==4 and view_name=='sagittal'):
                lm.slice_indices[data_index][0] = np.clip(lm.slice_indices[data_index][0] + delta, 0, lm.volume[data_index][0].shape[0]-1)
            elif view_name == 'coronal':
                lm.slice_indices[data_index][1] = np.clip(lm.slice_indices[data_index][1] + delta, 0, lm.volume[data_index][0].shape[1]-1)
            elif view_name == 'sagittal':
                lm.slice_indices[data_index][2] = np.clip(lm.slice_indices[data_index][2] + delta, 0, lm.volume[data_index][0].shape[2]-1)
        # Refresh all
        if lm.vol_dim == 3:
            lm.update_slices(0,data_index,view_name)
        else:
            for i in 0,1,2:
                lm.update_slices(i,data_index,view_name)

        self.update_cursor_display(data_index)
        self.update_cursor_lines(data_index)

    def cursor_coord_changed(self,axis:str, value:int,data_index,view_name):
        """
        Update cursor position when a spinbox value changes.
        """
        if axis == 'x':
            self.LoadMRI.slice_indices[data_index][2] = value -1
        elif axis == 'y':
            self.LoadMRI.slice_indices[data_index][1] = value -1
        elif axis == 'z':
            self.LoadMRI.slice_indices[data_index][0] = value -1

        # Refresh all
        if self.LoadMRI.vol_dim == 3:
            self.LoadMRI.update_slices(0,data_index,view_name)
        else:
            for i in 0,1,2:
                self.LoadMRI.update_slices(i,data_index,view_name)
        self.update_cursor_display(data_index)
        self.update_cursor_lines(data_index)


    def add_cursor4image(self,view_name,data_index,zoom_factor,img_vtk,image_index = 3):
        """
        Add cursor lines to the 4th image (image_index=3): heatmap and final visualisation
        """

        #create_cursor_lines
        vtk_widget = self.LoadMRI.vtk_widgets[image_index][view_name]

        renderer = self.LoadMRI.renderers[image_index][view_name]
        line_h = vtk.vtkLineSource()
        line_v = vtk.vtkLineSource()
        line_h,line_v = self.set_line_points(view_name, line_h, line_v,data_index,height = 0)

        mapper_h = vtk.vtkPolyDataMapper()
        mapper_h.SetInputConnection(line_h.GetOutputPort())
        actor_h = vtk.vtkActor()
        actor_h.SetMapper(mapper_h)
        actor_h.GetProperty().SetColor(1, 1,1)
        renderer.AddActor(actor_h)

        mapper_v = vtk.vtkPolyDataMapper()
        mapper_v.SetInputConnection(line_v.GetOutputPort())
        actor_v = vtk.vtkActor()
        actor_v.SetMapper(mapper_v)
        actor_v.GetProperty().SetColor(1, 1,1)
        renderer.AddActor(actor_v)

        self.cursor_lines[view_name][image_index] = {
            'horizontal': {'actor': actor_h, 'source': line_h},
            'vertical': {'actor': actor_v, 'source': line_v}
        }

        vtk_widget.GetRenderWindow().Render()

        self.update_cursor_lines(data_index)
        #Add axes to each widget
        if self.LoadMRI.vol_dim==4:
            if view_name=='coronal':
                 self.LoadMRI.add_axes(renderer, img_vtk, 'axial')
            else:
                self.LoadMRI.add_axes(renderer, img_vtk, view_name)
        else:
            self.LoadMRI.add_axes(renderer, img_vtk, view_name)



        #self.LoadMRI.minimap.add_minimap(view_name,img_vtk,image_index,vtk_widget,data_index)
