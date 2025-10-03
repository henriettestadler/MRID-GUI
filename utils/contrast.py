# This Python file uses the following encoding: utf-8
import vtk
import numpy as np


class Contrast:
    """
    Handles contrast/brightness adjustment for MRI volumes using a VTK lookup table (LUT).

    Parameters
    ----------
    Load_MRI : object
        Must provide:
        - volume : np.ndarray
        - actors : dict[str, vtk.vtkActor]
        - renderers : dict[str, vtk.vtkRenderer]
        - minimap_renderers : dict[str, vtk.vtkRenderer]
        - contrast_ui_elements : dict with Qt widgets

    Notes
    -----
    - Contrast = window width, controls range of intensities displayed.
    - Brightness = window center, shifts intensity midpoint.
    - Automatically computes histogram-based defaults to avoid outliers.
    - Updates all registered VTK actors and renderers immediately.
    - Designed to be initialized once per loaded volume.
    """
    def __init__(self, Load_MRI):
        self.Load_MRI = Load_MRI
        #Set window and level
        self.initial_window = (self.Load_MRI.volume.max() - self.Load_MRI.volume.min())
        self.initial_level = (self.Load_MRI.volume.max() + self.Load_MRI.volume.min()) / 2
        self.window = self.initial_window
        self.level = self.initial_level

        # get the UI connected
        ui = self.Load_MRI.contrast_ui_elements
        self.window_slider = ui["contrast"]
        self.level_slider = ui["brightness"]
        self.display_level_slider = ui["display_level"]
        self.display_window_slider = ui["display_window"]
        self.auto_button = ui["auto"]
        self.reset_button = ui["reset"]
        self.window_slider.setMinimum(1)
        self.window_slider.setMaximum(int(self.Load_MRI.volume.max()))
        self.window_slider.setValue(int(self.window))
        self.window_slider.valueChanged.connect(self.changed_sliders)
        self.level_slider.setMinimum(1)
        self.level_slider.setMaximum(int(self.Load_MRI.volume.max()))
        self.level_slider.setValue(int(self.level))
        self.level_slider.valueChanged.connect(self.changed_sliders)
        self.display_level_slider.display(int(self.level))
        self.display_window_slider.display(int(self.window))

        self.auto_button.clicked.connect(self.auto)
        self.reset_button.clicked.connect(self.reset)

        #apply initial lut
        self.compute_histogram(self.Load_MRI.volume)
        self.compute_lut()
        self.update_lut_window_level()

    def compute_lut(self):
        """
        Creates a grayscale VTK lookup table based on the volume’s min and max intensities
        """
        self.Load_MRI.scalar_min = self.Load_MRI.volume.min()
        self.Load_MRI.scalar_max = self.Load_MRI.volume.max()

        self.Load_MRI.lut_vtk = vtk.vtkLookupTable()
        self.Load_MRI.lut_vtk.SetTableRange(self.Load_MRI.scalar_min, self.Load_MRI.scalar_max)
        self.Load_MRI.lut_vtk.SetValueRange(0.0, 1.0)
        self.Load_MRI.lut_vtk.SetSaturationRange(0.0, 0.0)
        self.Load_MRI.lut_vtk.Build()

    def update_lut_window_level(self):
        """
        Updates the LUT and re-renders all VTK actors using the current selected window (contrast) and level (brightness).
        """
        vmin = self.level - self.window / 2
        vmax = self.level + self.window / 2

        # Update the VTK LUT if table range has changed
        if not hasattr(self, "last_range") or self.last_range != (vmin, vmax):
            self.Load_MRI.lut_vtk.SetTableRange(vmin, vmax)
            self.Load_MRI.lut_vtk.Build()
            self.last_range = (vmin, vmax)

        # Force all actors to use updated LUT
        for actor in self.Load_MRI.actors.values():
            prop = actor.GetProperty()
            prop.UseLookupTableScalarRangeOn()

        # change in original and minimap image
        for renderer in self.Load_MRI.renderers.values():
            renderer.GetRenderWindow().Render()
        for renderer in self.Load_MRI.minimap.minimap_renderers.values():
            renderer.GetRenderWindow().Render()


    def compute_histogram(self,volume: np.ndarray):
        """
        Computes a cumulative histogram of the volume to determine automatic window and level values while ignoring outliers.
        """
        hist, bin_edges = np.histogram(volume, bins=4096, range=(volume.min(), volume.max()))
        # Cumulative histogram
        cum_hist = np.cumsum(hist)
        total = cum_hist[-1]

        # Choose low/high percentiles to ignore outliers (e.g., 1%–99%)
        low_idx = np.searchsorted(cum_hist, 0.005 * total)
        high_idx = np.searchsorted(cum_hist, 0.995 * total)

        # Map back to intensity values
        vmin = bin_edges[low_idx]
        vmax = bin_edges[high_idx]

        # Level and window
        self.level_auto = (vmax + vmin) / 2
        self.window_auto = vmax - vmin

    def auto(self):
        """
        Sets window and level to automatically computed values and updates the LUT and sliders.
        """
        self.window = self.window_auto
        self.level = self.level_auto

        # Block signals while updating sliders
        self.level_slider.blockSignals(True)
        self.window_slider.blockSignals(True)
        self.display_level_slider.blockSignals(True)
        self.display_window_slider.blockSignals(True)

        self.display_level_slider.display(int(self.level_auto))
        self.display_window_slider.display(int(self.window_auto))
        self.level_slider.setValue(int(self.level_auto))
        self.window_slider.setValue(int(self.window_auto))

        # Re-enable signals
        self.level_slider.blockSignals(False)
        self.window_slider.blockSignals(False)
        self.display_level_slider.blockSignals(False)
        self.display_window_slider.blockSignals(False)

        self.update_lut_window_level()


    def reset(self):
        """
        Resets window and level to their initial values and updates the LUT and sliders.
        """
        self.window = self.initial_window
        self.level = self.initial_level

        # Block signals while updating sliders
        self.level_slider.blockSignals(True)
        self.window_slider.blockSignals(True)
        self.display_level_slider.blockSignals(True)
        self.display_window_slider.blockSignals(True)

        self.display_level_slider.display(int(self.level))
        self.display_window_slider.display(int(self.window))
        self.level_slider.setValue(int(self.level))
        self.window_slider.setValue(int(self.window))

        # Re-enable signals
        self.level_slider.blockSignals(False)
        self.window_slider.blockSignals(False)
        self.display_level_slider.blockSignals(False)
        self.display_window_slider.blockSignals(False)

        self.update_lut_window_level()

    def changed_sliders(self):
        """
        Updates the window and level from slider positions and refreshes the LUT accordingly.
        """
        self.window = self.window_slider.value()
        self.level = self.level_slider.value()

        self.display_level_slider.display(int(self.level))
        self.display_window_slider.display(int(self.window))

        self.update_lut_window_level()

