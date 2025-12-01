# This Python file uses the following encoding: utf-8
import vtk
import numpy as np


class Contrast:
    """
    Handles contrast/brightness adjustment for MRI volumes using a VTK lookup table (LUT).

    Notes
    -----
    - Contrast = window width, controls range of intensities displayed.
    - Brightness = window center, shifts intensity midpoint.
    - Automatically computes histogram-based defaults to avoid outliers.
    - Updates all registered VTK actors and renderers immediately.
    - Designed to be initialized once per loaded volume.
    """
    def __init__(self, LoadMRI,data_index:int):
        """
        Initialize contrast management for all available image indices.
        """
        self.initialise_class( LoadMRI,data_index)

    def initialise_class(self,LoadMRI,data_index):
        """
        Initialize contrast management for all available image indices.
        """
        # Store LUT parameters per image index
        self.LoadMRI = LoadMRI
        self.initial_window = {}
        self.initial_level = {}
        self.window = {}
        self.level = {}
        self.window_auto = {}
        self.level_auto = {}
        self.lut_vtk = {}
        #Set window and level and get the UI connected
        ui = self.LoadMRI.contrast_ui_elements[data_index]
        self.display_level_sliders = {}
        self.display_window_sliders = {}
        self.level_sliders = {}
        self.window_sliders = {}
        self.auto_buttons = {}
        self.reset_buttons = {}
        # Percentile thresholds (0–100 range)
        self.vminmax_perc = [0, 1] #reset
        self.vminmax_auto = [0.0001, 0.9999] #auto

        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            # Level and window for auto and reset
            vmin, vmax = np.percentile(self.LoadMRI.volume[data_index][image_index], [self.vminmax_perc[0]*100, self.vminmax_perc[1]*100]) #in percentage
            vmin_auto, vmax_auto = np.percentile(self.LoadMRI.volume[data_index][image_index], [self.vminmax_auto[0]*100, self.vminmax_auto[1]*100]) #in percentage
            self.initial_window[image_index] = vmax - vmin
            self.initial_level[image_index] = (vmax + vmin)/2
            self.window_auto[image_index] = vmax_auto - vmin_auto
            self.level_auto[image_index] = (vmax_auto + vmin_auto)/2

            self.window[image_index] = self.initial_window[image_index]
            self.level[image_index] = self.initial_level[image_index]
            #apply initial lut
            self.compute_lut(image_index,data_index)

            self.update_lut_window_level(image_index)

            #attach ui widgets
            self.display_level_sliders[image_index] =  ui[f"display_level{image_index}"]
            self.display_window_sliders[image_index] =  ui[f"display_window{image_index}"]
            self.window_sliders[image_index] =  ui[f"contrast{image_index}"]
            self.level_sliders[image_index] =  ui[f"brightness{image_index}"]
            self.auto_buttons[image_index] = ui[f"auto{image_index}"]
            self.reset_buttons[image_index] = ui[f"reset{image_index}"]

            #initialiye slider limits and values
            self.window_sliders[image_index].setMinimum(1)
            self.window_sliders[image_index].setMaximum(int(self.LoadMRI.volume[data_index][image_index].max()))
            self.window_sliders[image_index].setValue(int(self.window[image_index]))
            self.level_sliders[image_index].setMinimum(1)
            self.level_sliders[image_index].setMaximum(int(self.LoadMRI.volume[data_index][image_index].max()))
            self.level_sliders[image_index].setValue(int(self.level[image_index]))
            self.display_level_sliders[image_index].display(int(self.level[image_index]))
            self.display_window_sliders[image_index].display(int(self.window[image_index]))



    def compute_lut(self,image_index:int,data_index):
        """
        Creates a grayscale VTK lookup table based on the volume’s min and max intensities
        """
        if image_index==3: #take volume of first image
            vmin, vmax = np.percentile(self.LoadMRI.volume[data_index][0], [self.vminmax_perc[0]*100, self.vminmax_perc[1]*100])
        else:
            vmin, vmax = np.percentile(self.LoadMRI.volume[data_index][image_index], [self.vminmax_perc[0]*100, self.vminmax_perc[1]*100])
        self.lut_vtk[image_index] = vtk.vtkLookupTable()
        self.lut_vtk[image_index].SetTableRange(vmin, vmax)
        self.lut_vtk[image_index].SetValueRange(0.0, 1.0)
        self.lut_vtk[image_index].SetSaturationRange(0.0, 0.0)
        self.lut_vtk[image_index].Build()



    def update_lut_window_level(self,image_index:int):
        """
        Updates the LUT and re-renders all VTK actors using the current selected window (contrast) and level (brightness).
        """
        vmin = self.level[image_index] - self.window[image_index] / 2
        vmax = self.level[image_index] + self.window[image_index] / 2

        # Update the VTK LUT if table range has changed
        if not hasattr(self, "last_range") or self.last_range != (vmin, vmax):
            self.lut_vtk[image_index].SetTableRange(vmin, vmax)
            self.lut_vtk[image_index].Build()
            self.last_range = (vmin, vmax)

        # Force all actors to use updated LUT
        for actors_dict in self.LoadMRI.actors.values(): #if view_name in self.actors[image_index]:
            for _,actor in actors_dict.items():
                prop = actor.GetProperty()
                prop.UseLookupTableScalarRangeOn()

        # change in original and minimap image
        for vn in 'axial','coronal','sagittal':
            renderer = self.LoadMRI.renderers[image_index].get(vn, None)
            if renderer is not None:
                renderer.GetRenderWindow().Render()
            if hasattr(self.LoadMRI.minimap,"minimap_renderers"):
                minimap_renderer = self.LoadMRI.minimap.minimap_renderers[image_index].get(vn, None)
                if  minimap_renderer is not None:
                    if self.LoadMRI.minimap.minimap_actors[image_index][vn].GetVisibility():
                        minimap_renderer.GetRenderWindow().Render()



    def auto(self,image_index:int):
        """
        Sets window and level to automatically computed values and updates the LUT and sliders.
        """
        self.window[image_index] = self.window_auto[image_index].copy()
        self.level[image_index] = self.level_auto[image_index].copy()
        # Block signals while updating sliders
        self.block_signals(image_index,True)

        self.display_level_sliders[image_index].display(int(self.level_auto[image_index]))
        self.display_window_sliders[image_index].display(int(self.window_auto[image_index]))
        self.level_sliders[image_index].setValue(int(self.level_auto[image_index]))
        self.window_sliders[image_index].setValue(int(self.window_auto[image_index]))
        # Re-enable signals
        self.block_signals(image_index,False)

        self.update_lut_window_level(image_index)


    def reset(self,image_index:int):
        """
        Resets window and level to their initial values and updates the LUT and sliders.
        """
        self.window[image_index] = self.initial_window[image_index].copy()
        self.level[image_index] = self.initial_level[image_index].copy()
        # Block signals while updating sliders
        self.block_signals(image_index,True)

        self.display_level_sliders[image_index].display(int(self.initial_level[image_index]))
        self.display_window_sliders[image_index].display(int(self.initial_window[image_index]))
        self.level_sliders[image_index].setValue(int(self.initial_level[image_index]))
        self.window_sliders[image_index].setValue(int(self.initial_window[image_index]))
        # Re-enable signals
        self.block_signals(image_index,False)

        self.update_lut_window_level(image_index)

    def changed_sliders(self,value:int,image_index:int):
        """
        Updates the window and level from slider positions and refreshes the LUT accordingly.
        """
        self.window[image_index] = self.window_sliders[image_index].value()
        self.level[image_index] = self.level_sliders[image_index].value()

        self.display_level_sliders[image_index].display(int(self.level[image_index]))
        self.display_window_sliders[image_index].display(int(self.window[image_index]))

        self.update_lut_window_level(image_index)


    def recompute_luttable(self, volume: np.ndarray,image_index:int,data_index:int):
        """
        Recompute LUT and window/level ranges when timestamp is changed
        """
        vmin, vmax = np.percentile(volume, [self.vminmax_perc[0]*100, self.vminmax_perc[1]*100]) #in percentage
        # Level and window for auto and reset
        self.initial_window[image_index] = vmax - vmin
        self.initial_level[image_index] = (vmax + vmin)/2
        vmin_auto, vmax_auto = np.percentile(self.LoadMRI.volume[data_index][image_index], [self.vminmax_auto[0]*100, self.vminmax_auto[1]*100]) #in percentage
        self.window_auto[image_index] = vmax_auto - vmin_auto
        self.level_auto[image_index] = (vmax_auto + vmin_auto)/2

        self.window[image_index] = self.initial_window[image_index]
        self.level[image_index] = self.initial_level[image_index]
        #apply initial lut
        self.compute_lut(image_index,data_index)
        self.update_lut_window_level(image_index)

        # Block signals while updating sliders
        self.block_signals(image_index,True)

        self.window_sliders[image_index].setMaximum(int(volume.max()))
        self.window_sliders[image_index].setValue(int(self.window[image_index]))
        self.level_sliders[image_index].setMaximum(int(volume.max()))
        self.level_sliders[image_index].setValue(int(self.level[image_index]))
        self.display_level_sliders[image_index].display(int(self.level[image_index]))
        self.display_window_sliders[image_index].display(int(self.window[image_index]))

        # Re-enable signals
        self.block_signals(image_index,False)


    def block_signals(self,image_index:int,block_bool:bool):
        """
        Temporarily block or unblock all connected Qt signals for a given image index.
        """
        self.level_sliders[image_index].blockSignals(block_bool)
        self.window_sliders[image_index].blockSignals(block_bool)
        self.display_level_sliders[image_index].blockSignals(block_bool)
        self.display_window_sliders[image_index].blockSignals(block_bool)

