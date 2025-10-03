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
    def __init__(self):
        self.actor = None #vtk.vtkActor2D
        self.text = None #vtk.vtkTextActor
        self.use_mm = False #bool


    def create_bar(self, renderer: vtk.vtkRenderer,length_cm: float=1.0, color: tuple[float, float, float] = (0, 1, 0),offset: tuple[float, float] = (0.8, 0.5)):
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
        self.line = vtk.vtkLineSource()
        self.line.SetPoint1(0, 0, 0)
        self.line.SetPoint2(length_x*window_width, 0, 0)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputConnection(self.line.GetOutputPort())

        self.actor = vtk.vtkActor2D()
        self.actor.SetMapper(mapper)
        self.actor.GetProperty().SetColor(*color)
        self.actor.GetProperty().SetLineWidth(3)

        # Position in normalized display coordinates
        self.actor.SetPositionCoordinate(vtk.vtkCoordinate())
        self.actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        offset=(0.95-length_x,0.05)
        self.actor.GetPositionCoordinate().SetValue(*offset)

        renderer.AddActor2D(self.actor)

        # Text actor
        self.text = vtk.vtkTextActor()
        if self.use_mm:
            self.text.SetInput(f"{length_cm} mm")
        else:
            self.text.SetInput(f"{length_cm} cm")
        self.text.GetPositionCoordinate().SetValue(0.83, offset[1] + 0.03)
        self.text.GetTextProperty().SetColor(*color)
        self.text.GetTextProperty().SetFontSize(14)
        self.text.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()

        renderer.AddActor2D(self.text)
        renderer.GetRenderWindow().Render()

    def update_bar(self, renderer: vtk.vtkRenderer,length_cm:float=1.0, color:tuple[float,float,float]=(0, 1, 0),offset:tuple[float,float]=(0.8, 0.5)):
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
        self.unit_changed = False

        # Switch between cm and mm when threshold crossed
        if (self.use_mm==True and length_x < 0.45) or (self.use_mm==False and length_x >0.45):
            renderer.RemoveActor2D(self.text)
            renderer.RemoveActor2D(self.actor)
            self.unit_changed = True
            renderer.GetRenderWindow().Render()

        # Decide between cm and mm
        if length_x > 0.45:
            self.use_mm = True
            self.line.SetPoint2(length_x/10*window_width, 0, 0)
            offset=(0.95-length_x/10,0.05)
        else:
            self.use_mm = False
            self.line.SetPoint2(length_x*window_width, 0, 0)
            offset=(0.95-length_x,0.05)


        self.line.Modified()

        if self.unit_changed:
            self.text = vtk.vtkTextActor()
            self.actor = vtk.vtkActor2D()

        # Update actor position
        self.actor.SetPositionCoordinate(vtk.vtkCoordinate())
        self.actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        self.actor.GetPositionCoordinate().SetValue(*offset)

        #Update text
        if self.use_mm:
            self.text.SetInput(f"{length_cm} mm")
            self.text.GetPositionCoordinate().SetValue(0.83, offset[1] + 0.03)
        else:
            self.text.SetInput(f"{length_cm} cm")
            self.text.GetPositionCoordinate().SetValue(0.83, offset[1] + 0.03)

        #Re-create actor and text
        if self.unit_changed:
            #add text
            self.text.GetTextProperty().SetColor(*color)
            self.text.GetTextProperty().SetFontSize(14)
            self.text.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
            renderer.AddActor(self.text)
            #add actor
            mapper = vtk.vtkPolyDataMapper2D()
            mapper.SetInputConnection(self.line.GetOutputPort())

            self.actor = vtk.vtkActor2D()
            self.actor.SetMapper(mapper)
            self.actor.GetProperty().SetColor(*color)
            self.actor.GetProperty().SetLineWidth(3)

            # Position in normalized display coordinates
            self.actor.SetPositionCoordinate(vtk.vtkCoordinate())
            self.actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()

            self.actor.GetPositionCoordinate().SetValue(*offset)

            renderer.AddActor2D(self.actor)

        renderer.GetRenderWindow().Render()
