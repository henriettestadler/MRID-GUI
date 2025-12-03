# This Python file uses the following encoding: utf-8
import vtk
from utils.zoom import Zoom

class Minimap:
    """
    Handles creation and updating of minimaps used for zooming in and camera panning.
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
        self.minimap_renderers = {}
        for image_index in range(3):
            self.size_rectangle[image_index]: dict[str, list[float]] = {view: [] for view in ("axial", "sagittal", "coronal")}
            self.minimap_renderers[image_index] = {}
            self.minimap_actors[image_index] = {}
            self.zoom_rects[image_index] = {}

        self.last_center_x_norm: dict[str, list[float]] = {view: 0.0 for view in ("axial", "sagittal", "coronal")}
        self.last_center_y_norm: dict[str, list[float]] = {view: 0.0 for view in ("axial", "sagittal", "coronal")}
        self.half_width = {}
        self.half_height = {}
        self.LoadMRI.rect_old_x = 0.5
        self.LoadMRI.rect_old_y = 0.5
        self.LoadMRI.rect_old_z = 0.5
        self.new_x=0.5
        self.new_y=0.5



    def add_minimap(self,view_name:str,img_vtk:vtk.vtkImageData,image_index:int,vtk_widget,data_index):
        """
        Adds or updates three minimaps (axial, coronal, sagittal) to the given vtk widgets.
        """
        #Create or reuse the mini-map renderer
        if view_name not in self.minimap_renderers[image_index]:
            mm_renderer = vtk.vtkRenderer()
            rw, rh = self.LoadMRI.renderers[image_index][view_name].GetSize()
            w = min(0.3,rh/rw*0.3)
            h = min(0.3,rw/rh*0.3)
            self.size_rectangle[image_index][view_name] = [w,h]
            mm_renderer.SetViewport(0.0, 0.0,w,h)  # bottom-left corner
            mm_renderer.SetLayer(0)
            mm_renderer.SetBackground(1, 1, 1)
            vtk_widget.GetRenderWindow().SetNumberOfLayers(3)
            vtk_widget.GetRenderWindow().AddRenderer(mm_renderer)
            self.minimap_renderers[image_index][view_name] = mm_renderer
            (xmin, xmax, ymin, ymax, _, _) = self.LoadMRI.renderers[image_index][view_name].ComputeVisiblePropBounds()

        mm_renderer = self.minimap_renderers[image_index][view_name]

        # Create or reuse the mini-map image actor
        if view_name not in self.minimap_actors[image_index]:
            actor = vtk.vtkImageActor()
            actor.GetMapper().SetInputData(img_vtk)
            contrast_class = getattr(self.LoadMRI, f"contrastClass_{data_index}")
            if image_index not in contrast_class.lut_vtk:
                contrast_class.compute_lut(image_index,data_index)
            actor.GetProperty().SetLookupTable(contrast_class.lut_vtk[image_index])
            actor.GetProperty().UseLookupTableScalarRangeOn()
            actor.SetPickable(False)
            mm_renderer.AddActor(actor)
            self.minimap_actors[image_index][view_name] = actor
        mm_renderer.ResetCamera()

        if not self.LoadMRI.zoom_tf[view_name]: # Hide at the beginning
            self.minimap_actors[image_index][view_name].SetVisibility(False)
            mm_renderer.SetDraw(False)

    def create_small_rectangle(self,zoom_factor,vn: str=None,new_x: float=0,new_y: float=0,pan_arrow: bool=False):
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
            self.new_x = new_x

        if new_y!=0:
            if vn == 'axial':
                self.LoadMRI.rect_old_y = new_y
            elif vn == 'coronal':
                self.LoadMRI.rect_old_z = new_y
            elif vn == 'sagittal':
                self.LoadMRI.rect_old_y = new_y
            self.new_y = new_y


        if new_x==0 and new_y==0:
            self.LoadMRI.rect_old_x = 0.5
            self.LoadMRI.rect_old_z = 0.5
            self.LoadMRI.rect_old_y = 0.5

        display_min = {}
        display_max = {}
        half_width = {}
        half_height = {}
        # Create rectangle polyline
        points_rect = vtk.vtkPoints()
        points = {}

        #Zoom is the same over all images -> image_index= 0
        image_index = 0
        for view_name in self.LoadMRI.minimap.minimap_renderers[image_index]:
            #only renderer of image 0
            points[view_name] = vtk.vtkPoints()
            camera = self.LoadMRI.renderers[image_index][view_name].GetActiveCamera()
            half_height[view_name] = camera.GetParallelScale()
            aspect = self.LoadMRI.renderers[image_index][view_name].GetSize()[0] / self.LoadMRI.renderers[image_index][view_name].GetSize()[1]
            half_width[view_name] = half_height[view_name] * aspect
            xmin, xmax, ymin, ymax = Zoom.bounds[view_name]
            xminR, xmaxR, yminR, ymaxR,_,_ = self.LoadMRI.renderers[image_index][view_name].ComputeVisiblePropBounds()
            tolerance = 1e-3
            if (xmin <= xminR + tolerance and xmax >= xmaxR - tolerance and ymin <= yminR + tolerance and ymax >= ymaxR - tolerance):
                for idx in range(len(self.LoadMRI.renderers)):
                    mm_renderer = self.LoadMRI.minimap.minimap_renderers[idx][view_name]
                    self.LoadMRI.zoom_tf[view_name]=False
                    mm_renderer.SetDraw(False)
                    self.minimap_actors[idx][view_name].SetVisibility(False)
                    if view_name in self.zoom_rects[idx]:
                        self.zoom_rects[idx][view_name].SetVisibility(False)
            else:
                for idx in range(len(self.LoadMRI.renderers)):
                    self.LoadMRI.zoom_tf[view_name]=True
                    mm_renderer = self.LoadMRI.minimap.minimap_renderers[idx][view_name]
                    mm_renderer.SetDraw(True)
                    self.minimap_actors[idx][view_name].SetVisibility(True)
                    if view_name in self.zoom_rects[idx]:
                        self.zoom_rects[idx][view_name].SetVisibility(True)

            mm_renderer.SetWorldPoint(xmin, ymin, 0, 1.0)
            mm_renderer.WorldToDisplay()
            display_min[view_name] = mm_renderer.GetDisplayPoint()
            mm_renderer.SetWorldPoint(xmax, ymax, 0, 1.0)
            mm_renderer.WorldToDisplay()
            display_max[view_name] = mm_renderer.GetDisplayPoint()

        if not self.LoadMRI.zoom_tf['axial'] and not self.LoadMRI.zoom_tf['coronal'] and not self.LoadMRI.zoom_tf['sagittal']:
            for image_index,views in enumerate(self.LoadMRI.minimap.minimap_renderers.values()):
                for view_name, mm_renderer in views.items():
                    mm_renderer = self.LoadMRI.minimap.minimap_renderers[image_index][view_name]
                    mm_renderer.GetRenderWindow().Render()
                    if self.LoadMRI.vol_dim==4:
                        break
            return

        if (new_x!=0 or new_y!=0):
            mm_renderer = self.minimap_renderers[image_index][vn]
            (w_norm, h_norm) = self.LoadMRI.minimap.size_rectangle[image_index][view_name]
            window_width, window_height = mm_renderer.GetSize()

            new_x *= window_width
            new_y *= window_height

            if self.LoadMRI.vol_dim==3:
                half_width['axial'] = (display_max['axial'][0] - display_min['axial'][0])/2
                half_height['axial'] = (display_max['axial'][1] - display_min['axial'][1])/2
                half_width['sagittal'] = (display_max['sagittal'][0] - display_min['sagittal'][0])/2
                half_height['sagittal'] = (display_max['sagittal'][1] - display_min['sagittal'][1])/2
                half_width['coronal'] = (display_max['coronal'][0] - display_min['coronal'][0])/2
                half_height['coronal'] = (display_max['coronal'][1] - display_min['coronal'][1])/2
            else:
                half_width[view_name] = (display_max[view_name][0] - display_min[view_name][0])/2
                half_height[view_name] = (display_max[view_name][1] - display_min[view_name][1])/2

            if vn == 'axial':
                x_min = new_x - half_width['axial']
                x_max = new_x + half_width['axial']
                y_min = new_y - half_height['axial']
                y_max = new_y + half_height['axial']
            elif vn == 'sagittal':
                x_min = new_x - half_width['sagittal']
                x_max = new_x + half_width['sagittal']
                y_min = new_y - half_height['sagittal']
                y_max = new_y + half_height['sagittal']
            elif vn == 'coronal':
                x_min = new_x - half_width['coronal']
                x_max = new_x + half_width['coronal']
                y_min = new_y - half_height['coronal']
                y_max = new_y + half_height['coronal']
            points_rect.InsertNextPoint(x_min, y_min, 0)
            points_rect.InsertNextPoint(x_max, y_min, 0)
            points_rect.InsertNextPoint(x_max, y_max, 0)
            points_rect.InsertNextPoint(x_min, y_max, 0)
            points_rect.InsertNextPoint(x_min, y_min, 0)

            if not pan_arrow:
                for image_index,views in enumerate(self.LoadMRI.minimap.minimap_renderers.values()):
                    for view_name, mm_renderer in views.items():
                        self.pan_from_minimap(vn, [new_x/window_width,new_y/window_height],image_index)
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

        self.rectangle_render(new_x,new_y,points_rect,points,vn)

    def rectangle_render(self,new_x,new_y,points_rect,points,vn):
        """
        Update rectangle points and lines
        """
        for image_index,views in enumerate(self.LoadMRI.minimap.minimap_renderers.values()):
            for view_name, mm_renderer in views.items():
                if not self.LoadMRI.zoom_tf[view_name] or (view_name!=vn and vn!=None):
                    continue
                if view_name not in self.zoom_rects[image_index]:
                    poly_data = vtk.vtkPolyData()
                    if new_x!=0 or new_y!=0:
                        if view_name == 'axial':
                            poly_data.SetPoints(points_rect)
                        elif view_name == 'coronal':
                            poly_data.SetPoints(points_rect)
                        elif view_name == 'sagittal':
                            poly_data.SetPoints(points_rect)
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
                            poly_data.SetPoints(points_rect)
                        elif view_name == 'coronal':
                            poly_data.SetPoints(points_rect)
                        elif view_name == 'sagittal':
                            poly_data.SetPoints(points_rect)
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

    def pan_arrows(self,view_name,diff_x,diff_y,data_index,data_3d=False):
        """
        Panning images when GUI arrows are used.
        """
        renderer = self.LoadMRI.renderers[0][view_name].GetRenderWindow().GetRenderers().GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        scale = camera.GetParallelScale()
        fp = camera.GetFocalPoint()
        fp_new = [fp[0]+diff_x, fp[1]+diff_y, fp[2]]
        pos = camera.GetPosition()
        pos_new = [pos[0]+diff_x, pos[1]+diff_y, pos[2]]

        if data_3d:
            camera.ParallelProjectionOn()
            camera.SetParallelScale(scale)
            camera.SetFocalPoint(fp_new)
            camera.SetPosition(pos_new)
            self.LoadMRI.vtk_widgets[0][view_name].GetRenderWindow().Render()
            renderer.ResetCameraClippingRange()
            image_index = 0
        else:
            for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for idx, (vn, widget) in enumerate(vtk_widget_image.items()):
                    if idx==data_index:
                        renderer = widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
                        camera = renderer.GetActiveCamera()
                        camera.ParallelProjectionOn()
                        camera.SetParallelScale(scale)
                        camera.SetFocalPoint(fp_new)
                        camera.SetPosition(pos_new)
                        widget.GetRenderWindow().Render()
                        renderer.ResetCameraClippingRange()

        #return
        main_renderer = self.LoadMRI.renderers[image_index][view_name]
        (xmin, xmax, ymin, ymax, _,_) = main_renderer.ComputeVisiblePropBounds()
        world_width = xmax - xmin
        world_height = ymax - ymin

        new_x = (fp_new[0] - xmin)/world_width
        new_y = (fp_new[1] - ymin)/world_height

        self.create_small_rectangle(scale, vn=view_name, new_x=new_x,new_y=new_y,pan_arrow=True)

