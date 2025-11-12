# This Python file uses the following encoding: utf-8
import vtk
from utils.zoom import Zoom

class Minimap:
    """
    Handles creation and updating of minimaps used for zooming in and camera panning.

    TODO: this function is not very readable at the moment, I am sorry
    """
    def __init__(self,LoadMRI):
        """
        Initialize Minimap with reference to LoadMRI instance.
        """
        self.LoadMRI = LoadMRI
        self.minimap_actors = {}
        self.size_rectangle = {}
        self.zoom_rects = {}
        self.last_center_x_norm = {}
        self.last_center_y_norm = {}
        for image_index in range(3):
            self.size_rectangle[image_index]: dict[str, list[float]] = {view: [] for view in ("axial", "sagittal", "coronal")}
        self.last_center_x_norm: dict[str, list[float]] = {view: 0.0 for view in ("axial", "sagittal", "coronal")}
        self.last_center_y_norm: dict[str, list[float]] = {view: 0.0 for view in ("axial", "sagittal", "coronal")}
        self.minimap_borders = {}
        self.half_width = {}
        self.half_height = {}
        self.LoadMRI.rect_old_x = 0.5
        self.LoadMRI.rect_old_y = 0.5
        self.LoadMRI.rect_old_z = 0.5


    def add_minimap(self,view_name:str,img_vtk:vtk.vtkImageData,image_index:int,vtk_widget):
        """
        Adds or updates three minimaps (axial, coronal, sagittal) to the given vtk widgets.
        """
        #Create or reuse the mini-map renderer
        if view_name not in self.minimap_renderers[image_index]:
            mm_renderer = vtk.vtkRenderer()
            rw, rh = self.LoadMRI.renderers[image_index][view_name].GetSize()
            w =  min(0.3,rh/rw*0.3)
            h =  min(0.3,rw/rh*0.3)
            self.size_rectangle[image_index][view_name] = [w,h]
            mm_renderer.SetViewport(0.0, 0.0,w,h)  # bottom-left corner
            mm_renderer.SetLayer(1)
            vtk_widget.GetRenderWindow().SetNumberOfLayers(3)
            vtk_widget.GetRenderWindow().AddRenderer(mm_renderer)
            self.minimap_renderers[image_index][view_name] = mm_renderer

        mm_renderer = self.minimap_renderers[image_index][view_name]

        # Create or reuse the mini-map image actor
        if view_name not in self.minimap_actors:
            actor = vtk.vtkImageActor()
            actor.GetMapper().SetInputData(img_vtk)
            actor.GetProperty().SetLookupTable(self.LoadMRI.lut_vtk[image_index])
            actor.GetProperty().UseLookupTableScalarRangeOn()
            actor.SetPickable(False)
            mm_renderer.AddActor(actor)
            self.minimap_actors[image_index][view_name] = actor
        mm_renderer.ResetCamera()

        # Remove old border if it exists
        if hasattr(self, "minimap_borders") and view_name in self.minimap_borders:
            mm_renderer.RemoveActor(self.minimap_borders[image_index][view_name])

        # Compute display bounds
        (xmin, xmax, ymin, ymax, _, _) = mm_renderer.ComputeVisiblePropBounds()
        mm_renderer.SetWorldPoint(xmin, ymin, 0, 1.0)
        mm_renderer.WorldToDisplay()
        display_min = mm_renderer.GetDisplayPoint()
        mm_renderer.SetWorldPoint(xmax, ymax, 0, 1.0)
        mm_renderer.WorldToDisplay()
        display_max = mm_renderer.GetDisplayPoint()
        window_width, window_height = mm_renderer.GetRenderWindow().GetSize()
        vxmin, vymin, vxmax, vymax = mm_renderer.GetViewport()

        points = vtk.vtkPoints()
        points.InsertNextPoint(display_min[0], display_min[1], 0)
        points.InsertNextPoint(display_max[0], display_min[1], 0)
        points.InsertNextPoint(display_max[0], display_max[1], 0)
        points.InsertNextPoint(display_min[0], display_max[1], 0)
        points.InsertNextPoint(display_min[0], display_min[1], 0)  # close rectangle

        lines = vtk.vtkCellArray()
        lines.InsertNextCell(5)
        for i in range(5):
            lines.InsertCellPoint(i)
        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetLines(lines)
        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(poly_data)

        border_actor = vtk.vtkActor2D()
        border_actor.SetMapper(mapper)
        border_actor.GetProperty().SetColor(1, 1, 1)
        border_actor.GetProperty().SetLineWidth(1)
        border_actor.GetPositionCoordinate().SetCoordinateSystemToDisplay()
        border_actor.SetPosition(0, 0)
        mm_renderer.AddActor(border_actor)

        self.minimap_borders[image_index][view_name] = border_actor

        if not self.LoadMRI.zoom_tf[view_name]: # Hide at the beginning
            self.minimap_borders[image_index][view_name].SetVisibility(False)
            self.minimap_actors[image_index][view_name].SetVisibility(False)

    def create_small_rectangle(self,vn: str=None,new_x: float=0,new_y: float=0):
        """
        Draws or updates the zoom rectangle on the minimap.
        Also triggers camera panning in main renderers.
        """
        if new_x!=0:
            if vn == 'axial':
                self.LoadMRI.rect_old_x = new_x
            elif vn == 'coronal':
                self.LoadMRI.rect_old_x = new_x
            elif vn == 'sagittal':
                self.LoadMRI.rect_old_z = new_x
                new_x = 1-new_x
        if new_y!=0:
            if vn == 'axial':
                self.LoadMRI.rect_old_y = new_y
            elif vn == 'coronal':
                self.LoadMRI.rect_old_z = new_y
            elif vn == 'sagittal':
                self.LoadMRI.rect_old_y = new_y


        if new_x==0 and new_y==0:
            self.LoadMRI.rect_old_x = 0.5
            self.LoadMRI.rect_old_z = 0.5
            self.LoadMRI.rect_old_y = 0.5

        display_min = {}
        display_max = {}
        half_width = {}
        half_height = {}
        # Create rectangle polyline
        points_a = vtk.vtkPoints()
        points_c = vtk.vtkPoints()
        points_s = vtk.vtkPoints()
        points = {}

        #Zoom is the same over all images -> image_index= 0
        image_index = 0
        for view_name in self.LoadMRI.minimap.minimap_renderers[image_index]:
            #only renderer of image 0
            mm_renderer = self.LoadMRI.minimap.minimap_renderers[image_index][view_name]
            points[view_name] = vtk.vtkPoints()
            camera = self.LoadMRI.renderers[image_index][view_name].GetActiveCamera()
            half_height[view_name] = camera.GetParallelScale()
            aspect = self.LoadMRI.renderers[image_index][view_name].GetSize()[0] / self.LoadMRI.renderers[image_index][view_name].GetSize()[1]
            half_width[view_name] = half_height[view_name] * aspect
            xmin, xmax, ymin, ymax = Zoom.bounds[view_name]
            xminR, xmaxR, yminR, ymaxR,_,_ = self.LoadMRI.renderers[image_index][view_name].ComputeVisiblePropBounds()
            tolerance = 1e-3
            if (xmin <= xminR + tolerance and xmax >= xmaxR - tolerance and ymin <= yminR + tolerance and ymax >= ymaxR - tolerance):
                for image_index in range(self.LoadMRI.num_images):
                    self.LoadMRI.zoom_tf[view_name]=False
                    self.minimap_borders[image_index][view_name].SetVisibility(False)
                    self.minimap_actors[image_index][view_name].SetVisibility(False)
                    if view_name in self.zoom_rects[image_index]:
                        self.zoom_rects[image_index][view_name].SetVisibility(False)
            else:
                for image_index in range(self.LoadMRI.num_images):
                    self.LoadMRI.zoom_tf[view_name]=True
                    #self.minimap_borders[image_index][view_name].SetVisibility(True)
                    self.minimap_actors[image_index][view_name].SetVisibility(True)
                    if view_name in self.zoom_rects[image_index]:
                        self.zoom_rects[image_index][view_name].SetVisibility(True)

            if view_name == 'axial':
                display_min = {}
                display_max = {}
            mm_renderer.SetWorldPoint(xmin, ymin, 0, 1.0)
            mm_renderer.WorldToDisplay()
            display_min[view_name] = mm_renderer.GetDisplayPoint()
            mm_renderer.SetWorldPoint(xmax, ymax, 0, 1.0)
            mm_renderer.WorldToDisplay()
            display_max[view_name] = mm_renderer.GetDisplayPoint()
            #mm_renderer.GetRenderWindow().Render()

        if not self.LoadMRI.zoom_tf['axial'] and not self.LoadMRI.zoom_tf['coronal'] and not self.LoadMRI.zoom_tf['sagittal']:
            for image_index,views in enumerate(self.LoadMRI.minimap.minimap_renderers.values()):
                for view_name, mm_renderer in views.items():
                    mm_renderer = self.LoadMRI.minimap.minimap_renderers[image_index][view_name]
                    mm_renderer.GetRenderWindow().Render()
            return

        if (new_x!=0 or new_y!=0):
            mm_renderer = self.minimap_renderers[image_index][vn]
            (w_norm, h_norm) = self.LoadMRI.minimap.size_rectangle[image_index][view_name]
            window_width, window_height = mm_renderer.GetSize()

            new_x *= window_width
            new_y *= window_height

            half_width['axial'] = (display_max['axial'][0] - display_min['axial'][0])/2
            half_height['axial'] = (display_max['axial'][1] - display_min['axial'][1])/2
            half_width['sagittal'] = (display_max['sagittal'][0] - display_min['sagittal'][0])/2
            half_height['sagittal'] = (display_max['sagittal'][1] - display_min['sagittal'][1])/2
            half_width['coronal'] = (display_max['coronal'][0] - display_min['coronal'][0])/2
            half_height['coronal'] = (display_max['coronal'][1] - display_min['coronal'][1])/2
            if vn == 'axial':
                ax = new_x
                ay = new_y
                ax_min = new_x - half_width['axial']
                ax_max = new_x + half_width['axial']
                ay_min = new_y - half_height['axial']
                ay_max = new_y + half_height['axial']
                sx = (display_min['sagittal'][0] + display_max['sagittal'][0])/2
                sy = new_y
                sx_min = display_min['sagittal'][0] #display_min[0]
                sx_max = display_max['sagittal'][0] #display_max[0]
                sy_min = new_y - half_height['sagittal']
                sy_max = new_y + half_height['sagittal']
                cx = new_x
                cy = (display_min['coronal'][1] + display_max['coronal'][1])/2
                cx_min = new_x - half_width['coronal']
                cx_max = new_x + half_width['coronal']
                cy_min = display_min['coronal'][1]
                cy_max = display_max['coronal'][1]
            elif vn == 'sagittal':
                mm_s = self.minimap_renderers[image_index]['sagittal']
                (xmin_global, xmax_global, ymin_global, ymax_global, _, _) = mm_s.ComputeVisiblePropBounds()
                mm_s.SetWorldPoint(xmax_global, ymax_global, 0, 1.0)
                mm_s.WorldToDisplay()
                display_max_global = mm_s.GetDisplayPoint()
                #'axial'
                ax = (display_min['axial'][0] + display_max['axial'][0])/2
                ay = new_y
                ax_min = display_min['axial'][0]
                ax_max = display_max['axial'][0]
                ay_min = new_y - half_height['axial']
                ay_max = new_y + half_height['axial']
                #'sagittal'
                sx = new_x
                sy = new_y
                sx_min = new_x - half_width['sagittal']
                sx_max = new_x + half_width['sagittal']
                sy_min = new_y - half_height['sagittal']
                sy_max = new_y + half_height['sagittal']
                #'coronal'
                cx = (display_max['coronal'][0] + display_min['coronal'][0])/2
                cy = display_max_global[0] - new_x
                cx_min = display_min['coronal'][0]
                cx_max = display_max['coronal'][0]
                cy_min = display_max['sagittal'][0] - new_x - half_width['coronal']
                cy_max = display_max['sagittal'][0] - new_x + half_width['coronal']
            elif vn == 'coronal':
                mm_c = self.minimap_renderers[image_index]['sagittal']
                (xmin_global, xmax_global, ymin_global, ymax_global, _, _) = mm_c.ComputeVisiblePropBounds()
                mm_c.SetWorldPoint(xmax_global, ymax_global, 0, 1.0)
                mm_c.WorldToDisplay()
                display_max_global = mm_c.GetDisplayPoint()
                #'axial'
                ax = new_x
                ay = (display_max['axial'][1] + display_min['axial'][1])/2
                ax_min = new_x - half_width['axial']
                ax_max = new_x + half_width['axial']
                ay_min = display_min['axial'][1]
                ay_max = display_max['axial'][1]
                #'sagittal'
                sx = display_max['sagittal'][0] -new_y
                sy = (display_max['sagittal'][1] + display_min['sagittal'][1])/2
                sx_min = display_max['sagittal'][0] -new_y - half_width['sagittal']
                sx_max = display_max['sagittal'][0] -new_y + half_width['sagittal']
                sy_min = display_min['sagittal'][1]
                sy_max = display_max['sagittal'][1]
                #'coronal'
                cx = new_x
                cy = new_y
                cx_min = new_x - half_width['coronal']
                cx_max = new_x + half_width['coronal']
                cy_min = new_y - half_height['coronal']
                cy_max = new_y + half_height['coronal']
            if self.LoadMRI.zoom_tf['axial']: #axial
                points_a.InsertNextPoint(ax_min, ay_min, 0)
                points_a.InsertNextPoint(ax_max, ay_min, 0)
                points_a.InsertNextPoint(ax_max, ay_max, 0)
                points_a.InsertNextPoint(ax_min, ay_max, 0)
                points_a.InsertNextPoint(ax_min, ay_min, 0)
            if self.LoadMRI.zoom_tf['sagittal']:#sagittal
                points_s.InsertNextPoint(sx_min, sy_min, 0)
                points_s.InsertNextPoint(sx_max, sy_min, 0)
                points_s.InsertNextPoint(sx_max, sy_max, 0)
                points_s.InsertNextPoint(sx_min, sy_max, 0)
                points_s.InsertNextPoint(sx_min, sy_min, 0)
            if self.LoadMRI.zoom_tf['coronal']: #coronal
                points_c.InsertNextPoint(cx_min, cy_min, 0)
                points_c.InsertNextPoint(cx_max, cy_min, 0)
                points_c.InsertNextPoint(cx_max, cy_max, 0)
                points_c.InsertNextPoint(cx_min, cy_max, 0)
                points_c.InsertNextPoint(cx_min, cy_min, 0)
            for image_index,views in enumerate(self.LoadMRI.minimap.minimap_renderers.values()):
                for view_name, mm_renderer in views.items():
                    self.pan_from_minimap('axial', [ax/window_width,ay/window_height],image_index)
                    self.pan_from_minimap('sagittal', [sx/window_width,sy/window_height],image_index)
                    self.pan_from_minimap('coronal', [cx/window_width,cy/window_height],image_index)
        else:
            for image_index,views in enumerate(self.LoadMRI.minimap.minimap_renderers.values()):
                for view_name, mm_renderer in views.items():
                    window_width, window_height = mm_renderer.GetSize()
                    self.last_center_x_norm[view_name] = ((display_max[view_name][0] + display_min[view_name][0])/2)/window_width
                    self.last_center_y_norm[view_name] = ((display_max[view_name][1] + display_min[view_name][1])/2)/window_height
                    if not self.LoadMRI.zoom_tf[view_name]:
                        continue
                    points[view_name].InsertNextPoint(display_min[view_name][0], display_min[view_name][1], 0.2)
                    points[view_name].InsertNextPoint(display_max[view_name][0], display_min[view_name][1], 0.2)
                    points[view_name].InsertNextPoint(display_max[view_name][0], display_max[view_name][1], 0.2)
                    points[view_name].InsertNextPoint(display_min[view_name][0], display_max[view_name][1], 0.2)
                    points[view_name].InsertNextPoint(display_min[view_name][0], display_min[view_name][1], 0.2)

        for image_index,views in enumerate(self.LoadMRI.minimap.minimap_renderers.values()):
            for view_name, mm_renderer in views.items():
                if not self.LoadMRI.zoom_tf[view_name]:
                    continue
                if view_name not in self.zoom_rects[image_index]:
                    poly_data = vtk.vtkPolyData()
                    if new_x!=0 or new_y!=0:
                        if view_name == 'axial':
                            poly_data.SetPoints(points_a)
                        elif view_name == 'coronal':
                            poly_data.SetPoints(points_c)
                        elif view_name == 'sagittal':
                            poly_data.SetPoints(points_s)
                    else:
                        poly_data.SetPoints(points[view_name])
                    lines = vtk.vtkCellArray()
                    lines.InsertNextCell(5)
                    for i in range(5):
                        lines.InsertCellPoint(i)
                    poly_data.SetLines(lines)
                    mapper = vtk.vtkPolyDataMapper2D()
                    mapper.SetInputData(poly_data)
                    actor = vtk.vtkActor2D()
                    actor.SetMapper(mapper)
                    actor.GetProperty().SetColor(1, 0, 0)
                    actor.GetProperty().SetLineWidth(2)
                    mm_renderer.AddActor(actor)
                    self.zoom_rects[image_index][view_name] = actor
                    mm_renderer.GetRenderWindow().Render()
                else:
                    # Update existing actor
                    actor = self.zoom_rects[image_index][view_name]
                    poly_data = actor.GetMapper().GetInput()
                    if new_x!=0 or new_y!=0:
                        if view_name == 'axial':
                            poly_data.SetPoints(points_a)
                        elif view_name == 'coronal':
                            poly_data.SetPoints(points_c)
                        elif view_name == 'sagittal':
                            poly_data.SetPoints(points_s)
                    else:
                        poly_data.SetPoints(points[view_name])
                    poly_data.Modified()
                    mm_renderer.GetRenderWindow().Render()


    def pan_from_minimap(self, view_name, rect_pos,image_index):
        """
        Pan the main renderer camera based on the rectangle position in the minimap.
        """

        main_renderer = self.LoadMRI.renderers[image_index][view_name]
        center_x_norm = rect_pos[0]
        center_y_norm = rect_pos[1]

        delta_x = self.last_center_x_norm[view_name] - center_x_norm
        delta_y = self.last_center_y_norm[view_name] - center_y_norm

        (xmin, xmax, ymin, ymax, _,_) = main_renderer.ComputeVisiblePropBounds()
        world_width = xmax - xmin
        world_height = ymax - ymin

        center_x_world = xmin + center_x_norm * world_width
        center_y_world = ymin + center_y_norm * world_height

        camera = main_renderer.GetActiveCamera()
        camera.ParallelProjectionOn()
        focal = camera.GetFocalPoint()
        pos = camera.GetPosition()
        camera.SetFocalPoint(center_x_world, center_y_world, focal[2])
        camera.SetPosition(center_x_world, center_y_world, pos[2])

        [xmin, xmax, ymin, ymax] = Zoom.bounds[view_name]
        Zoom.bounds[view_name] = [xmin+delta_x,xmax+delta_x,ymin+delta_y,ymax+delta_y]

        self.last_center_x_norm[view_name] = center_x_norm
        self.last_center_y_norm[view_name] = center_y_norm

        main_renderer.GetRenderWindow().Render()
