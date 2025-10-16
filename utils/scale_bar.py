# This Python file uses the following encoding: utf-8

import vtk

class Scale:
    """
    Handles creation and updating of a 2D scale bar overlay for VTK renderers.

    Notes
    -----
    - The scale bar dynamically adapts between cm and mm depending on zoom level.
    - Designed to be called per view (axial, coronal, sagittal).
    """
    def __init__(self,LoadMRI,vol_dim):
        self.LoadMRI = LoadMRI
        self.actors = {}
        self.lines = {}
        self.texts = {}
        self.actors = {}
        self.lines = {}
        self.texts = {}
        self.vol_dim = vol_dim
        self.use_mm = False #bool
        self.unit_changed = False #bool


    def create_bar(self, renderer: vtk.vtkRenderer,view_name:str,length_cm: float=1.0, color: tuple[float, float, float] = (0, 1, 0)):
        """
        Create and add a new scale bar to the given VTK renderer ONCE.
        """
        xmin, xmax, ymin, ymax, zmin, zmax = renderer.ComputeVisiblePropBounds()
        window_width, _ = renderer.GetSize()

        # Convert min / max bounds to display coordinates
        renderer.SetWorldPoint(xmin, ymin, zmin, 1.0)
        renderer.WorldToDisplay()
        x_nmin = renderer.GetDisplayPoint()[0] / window_width

        renderer.SetWorldPoint(xmax, ymax, zmax, 1.0)
        renderer.WorldToDisplay()
        x_nmax = renderer.GetDisplayPoint()[0] / window_width

        # Compute length
        diff_x_norm = x_nmax - x_nmin
        length_mm = length_cm * 10  # convert cm to mm
        length_x = diff_x_norm/(xmax-xmin)*length_mm

        # Decide between cm and mm
        if length_x > 0.45:
            self.use_mm = True
            length_x /= 10
        else:
            self.use_mm = False

        # Line actor
        line = vtk.vtkLineSource()
        line.SetPoint1(0, 0, 0)
        line.SetPoint2(length_x*window_width, 0, 0)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputConnection(line.GetOutputPort())

        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetLineWidth(3)

        # Position in normalized display coordinates
        actor.SetPositionCoordinate(vtk.vtkCoordinate())
        actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        offset=(0.95-length_x,0.05)
        actor.GetPositionCoordinate().SetValue(*offset)

        # Text actor
        text = vtk.vtkTextActor()
        if self.use_mm:
            text.SetInput(f"{length_cm} mm")
        else:
            text.SetInput(f"{length_cm} cm")
        text.GetPositionCoordinate().SetValue(0.83, offset[1] + 0.03)
        text.GetTextProperty().SetColor(*color)
        text.GetTextProperty().SetFontSize(14)
        text.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()

        for image_index in range(self.LoadMRI.num_images):
            renderer = self.LoadMRI.renderers[image_index][view_name]
            renderer.AddActor2D(actor)
            renderer.AddActor(text)

        self.lines[view_name]=line
        self.actors[view_name]=actor
        self.texts[view_name]=text


    def update_bar(self, renderer: vtk.vtkRenderer,view_name:str,length_cm:float=1.0, color:tuple[float,float,float]=(0, 1, 0)):
        """
        Update the scale bar position and units after zoom changes
        """
        xmin, xmax, ymin, ymax, zmin, zmax = renderer.ComputeVisiblePropBounds()
        window_width, _ = renderer.GetSize()

        # Convert min / max bounds to display coordinates
        renderer.SetWorldPoint(xmin, ymin, zmin, 1.0)
        renderer.WorldToDisplay()
        x_nmin = renderer.GetDisplayPoint()[0] / window_width

        renderer.SetWorldPoint(xmax, ymax, zmax, 1.0)
        renderer.WorldToDisplay()
        x_nmax = renderer.GetDisplayPoint()[0] / window_width

        # Compute length
        diff_x_norm = x_nmax - x_nmin
        length_mm = length_cm * 10  # convert cm to mm
        length_x = diff_x_norm/(xmax-xmin)*length_mm

        line = self.lines[view_name]
        actor = self.actors[view_name]
        text = self.texts[view_name]

        # Decide between cm and mm
        if length_x > 0.45:
            self.use_mm = True
            line.SetPoint2(length_x/10*window_width, 0, 0)
            offset=(0.95-length_x/10,0.05)
        else:
            self.use_mm = False
            line.SetPoint2(length_x*window_width, 0, 0)
            offset=(0.95-length_x,0.05)
        line.Modified()

        for image_index in range(self.LoadMRI.num_images):
            renderer = self.LoadMRI.renderers[image_index][view_name]

            # Switch between cm and mm when threshold crossed
            if (self.use_mm==True and length_x < 0.45) or (self.use_mm==False and length_x >0.45):
                renderer.RemoveActor2D(text)
                renderer.RemoveActor2D(actor)
                self.unit_changed = True
            else:
                self.unit_changed = False

            if self.unit_changed:
                text = vtk.vtkTextActor()
                actor = vtk.vtkActor2D()

            # Update actor position
            actor.SetPositionCoordinate(vtk.vtkCoordinate())
            actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
            actor.GetPositionCoordinate().SetValue(*offset)

            #Update text
            if self.use_mm:
                text.SetInput(f"{length_cm} mm")
                text.GetPositionCoordinate().SetValue(0.83, offset[1] + 0.03)
            else:
                text.SetInput(f"{length_cm} cm")
                text.GetPositionCoordinate().SetValue(0.83, offset[1] + 0.03)

            #Re-create actor and text
            if self.unit_changed:
                #add text
                text.GetTextProperty().SetColor(*color)
                text.GetTextProperty().SetFontSize(14)
                text.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()

                #add actor
                mapper = vtk.vtkPolyDataMapper2D()
                mapper.SetInputConnection(line.GetOutputPort())

                actor.SetMapper(mapper)
                actor.GetProperty().SetColor(*color)
                actor.GetProperty().SetLineWidth(3)

                # Position in normalized display coordinates
                actor.SetPositionCoordinate(vtk.vtkCoordinate())
                actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
                actor.GetPositionCoordinate().SetValue(*offset)

        self.lines[view_name] = line
        self.actors[view_name] = actor
        self.texts[view_name] = text
