# This Python file uses the following encoding: utf-8
from PySide6.QtGui import QColor
import os
import SimpleITK as sITK
from PySide6.QtCore import QObject, Signal
from mrid_utils import heatmap
import vtk
from vtk.util import numpy_support
import numpy as np
import matplotlib.pyplot as plt

class MRID_tags(QObject):
    """
    Class to manage MRI tags, labels, and saving functionality.
    Handles label creation, text file generation, and NIfTI saving.
    """
    fileSaved = Signal(str)  # define the signal — emits the saved file path

    def __init__(self,MainWindow:object,num_tags:int, tag_data: list[tuple[str, int]],num_regions:int,regions: list[tuple[str, int]]):
        """
            Initialize MRID_tags instance.

            Args:
                MainWindow (object): Main application window instance.
                num_tags (int): Number of MRI tags.
                tag_data (list[tuple[str,int]]): Tag names and counts.
                num_regions (int): Number of anatomical regions.
                regions (list[tuple[str,int]]): Region names and counts.
        """
        super().__init__()
        self.MW = MainWindow
        self.LoadMRI = MainWindow.LoadMRI
        self.tag_data = tag_data
        self.num_tags = num_tags
        self.num_regions = num_regions
        self.region_data = regions
        self.heatmap_sim = {}
        self.heatmap_nii = {}
        self.heatmap_slice = {}
        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            self.heatmap_sim[idx] = np.zeros((self.LoadMRI.volume[0][0].shape[2], self.LoadMRI.volume[0][0].shape[1],self.LoadMRI.volume[0][0].shape[0]))
            self.heatmap_nii[idx] = np.zeros((self.LoadMRI.volume[0][0].shape[2], self.LoadMRI.volume[0][0].shape[1],self.LoadMRI.volume[0][0].shape[0]))
            self.heatmap_slice[idx] = np.zeros((self.LoadMRI.volume[0][0].shape[2], self.LoadMRI.volume[0][0].shape[1],self.LoadMRI.volume[0][0].shape[0]))
        self.center_x = {}
        self.center_y = {}
        self.width = {}
        self.height = {}
        self.LoadMRI.legend_lut = {}
        self.LoadMRI.legend_scalar_bar = {}
        self.file_name = {}




    def create_labels(self):
        """
            Generate labels for anatomical regions and tags.
            Sets up colors for paintbrush, paintover, and histogram.
        """
        #predefined colors
        colors_predefined = ["red", "lime", "blue", "yellow", "aqua", "magenta", "orange", "DarkGreen", "Peru", "DarkMagenta",
                            "Maroon", "navy", "olive", "MediumBlue", "PapazaWhip","gold","violet","coral","Tan"]
        total_islands = sum([self.tag_data[i][1] for i in range(self.num_tags)])

        if total_islands > len(colors_predefined):
            #more colors have to be defined
            num_colors_needed = total_islands - len(colors_predefined)
            colors_predefined.extend([QColor.fromHsv(int(360/num_colors_needed * i), 255, 200).name() for i in range(num_colors_needed)])

        label_names = []
        label_text = []
        index = 0
        self.VIS_MSH = {}
        self.VIS_MSH[0] = [0,0]
        self.region_names = []
        self.mrid_names = []

        for name, count in self.region_data:
            for i in range(count):
                self.region_names.append(name)
                label_names.append(f"{name}") #anatomical regions
                label_text.append(colors_predefined[index])
                index += 1
                self.VIS_MSH[index] = [1, 1]

        for name, count in self.tag_data:
            for i in range(count):
                self.mrid_names.append(name)
                label_names.append(f"{name}{i+1}") #tags and islands
                label_text.append(colors_predefined[index])
                index += 1
                self.VIS_MSH[index] = [1, 1]

        # Active Labels
        self.LoadMRI.paintbrush.color_combobox = ["white"]
        self.LoadMRI.paintbrush.color_combobox.extend(label_text)
        self.LoadMRI.paintbrush.labels_combobox = ["Clear Labels"]
        self.LoadMRI.paintbrush.labels_combobox.extend(label_names)

        #paintover
        self.LoadMRI.paintbrush.color_paintover = ["black", "white"]
        self.LoadMRI.paintbrush.color_paintover.extend(label_text)
        self.LoadMRI.paintbrush.labels_paintover = ["All Labels","Clear Label"]
        self.LoadMRI.paintbrush.labels_paintover.extend(label_names)

        #Histogram
        print('histogram zeugs')
        self.LoadMRI.paintbrush.color_histogram = label_text
        self.LoadMRI.paintbrush.labels_histogram = label_names

        self.LoadMRI.paintbrush.RGBA = {}
        self.LoadMRI.paintbrush.RGBA[0] = [0,0,0,0]
        self.LoadMRI.paintbrush.RGB_table = []
        self.LoadMRI.paintbrush.RGB_table= [(0,0,0,0)]
        for i,color in enumerate(self.LoadMRI.paintbrush.color_combobox):
            if i == 0:
                continue
            if isinstance(color, str) and color.startswith("#"):
                qcolor = QColor(color)
                self.LoadMRI.paintbrush.RGBA[i] = qcolor.getRgb()
                r, g, b, a = qcolor.getRgb()
                self.LoadMRI.paintbrush.RGB_table.append([r/255,g/255,b/255,0.3]) #self.LoadMRI.paintbrush.labelOccupancy
            else:
                qcolor = QColor(color)
                r, g, b, a = qcolor.getRgb()
                self.LoadMRI.paintbrush.RGBA[i] = qcolor.getRgb()
                self.LoadMRI.paintbrush.RGB_table.append((r/255,g/255,b/255,0.3)) #self.LoadMRI.paintbrush.labelOccupancy


    def generate_textfile(self):
        """
        Save each tag and its color to a tab-separated text file.
        """

        folder = f"{self.LoadMRI.session_path}/anat"
        filename = os.path.join(folder, "labels.txt")
        label_names = self.LoadMRI.paintbrush.labels_combobox

        RGBA = self.LoadMRI.paintbrush.RGBA

        with open(filename, "w", encoding="utf-8") as f:
            #Write header
            f.write("###########################\n")
            f.write("# Label Description File \n")
            f.write("# File Format: \n")
            f.write("# IDX -R- -G- -B- -A-- VIS MSH LABEL \n")
            f.write("# Fields: \n")
            f.write("# IDX: Zero-based index \n")
            f.write("# -R-: Red color component (0..255) \n")
            f.write("# -G-: Green color component (0..255) \n")
            f.write("# -B-: Blue color component (0..255) \n")
            f.write("# -A--: Label transparency (0..1) \n")
            f.write("# VIS: Label visibility (0 or 1) \n")
            f.write("# MSH: Label mesh visibility (0 or 1) \n")
            f.write("# LABEL: Label description \n")
            f.write("###########################\n")

            for i,label in enumerate(label_names):
                f.write(f'{i}\t{RGBA[i][0]}\t{RGBA[i][1]}\t{RGBA[i][2]}\t{int(RGBA[i][3]/255)}\t{self.VIS_MSH[i][0]}\t{self.VIS_MSH[i][1]}\t"{label}"\n')

    def save_as_niigz(self):
        """
        Save the current label volume as a NIfTI (.nii.gz) file.
        Prompts the user for location and name. Copies image metadata from the original MRI.
        Emits:
            fileSaved(str): The path to the saved file.
        """
        # Convert your NumPy label array back to a SimpleITK image
        for data_index in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[data_index]
            if self.LoadMRI.tag_file:
                self.actor_heatmap = {}
                self.LoadMRI.renderers[3] = {}
                if data_view=='sagittal':
                    label_image = sITK.GetImageFromArray(np.swapaxes(self.LoadMRI.paintbrush.label_volume[data_index], 1, 2))
                else:
                    label_image = sITK.GetImageFromArray(self.LoadMRI.paintbrush.label_volume[data_index])
                size = list(self.LoadMRI.paintbrush.label_volume[data_index].shape[::-1]) + [0]  # Extract 1 time frame
            else: #without segmentation labels
                if data_view=='sagittal':
                    label_volume = np.swapaxes(self.LoadMRI.paintbrush.label_volume[data_index], 1, 2)
                else:
                    label_volume = self.LoadMRI.paintbrush.label_volume[data_index].copy()
                label_volume[label_volume <= self.num_regions] = 0
                label_image = sITK.GetImageFromArray(label_volume)
                size = list(self.LoadMRI.paintbrush.label_volume[data_index].shape[::-1]) + [0]  # Extract 1 time frame
            ref_image = sITK.ReadImage(self.LoadMRI.file_name[data_index])

            reference_image = sITK.Extract(
                ref_image,
                size=size,
                index=[0, 0, 0, 0]  # take time=0 frame
            )
            label_image = sITK.Flip(label_image, self.LoadMRI.axes_to_flip[data_index], flipAboutOrigin=False)
            label_image.CopyInformation(reference_image)

            # Suggest a default name (for example, based on the original file name)
            if self.LoadMRI.tag_file:
                file_name = self.LoadMRI.file_name[data_index][:-7]
                default_name = f"{file_name}-anat.nii.gz"
            else:
                file_name = self.LoadMRI.file_name[data_index][:-7]
                default_name = f"{file_name}-segmentation.nii.gz"

            save_path = default_name

            if not save_path:
                return

            # Ensure the filename ends with .nii.gz
            if not save_path.lower().endswith(".nii.gz"):
                save_path += ".nii.gz"

            sITK.WriteImage(label_image, save_path)

            self.fileSaved.emit(save_path)  # emit the signal
            self.file_name[data_index] = file_name

        self.start_heatmap()




    def start_heatmap(self):
        """
            Generate and visualize heatmap for the saved segmentation.

            Args:
                file_name (str): Base file name without extension
        """
        #needed to add heatmap later to heatmap
        self.LoadMRI.minimap.minimap_renderers[3] = {}
        self.LoadMRI.minimap.size_rectangle[3] = {}
        self.LoadMRI.minimap.zoom_rects[3] = {}
        self.LoadMRI.minimap.minimap_actors[3] = {}
        for data_index in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[data_index]
            file_name = self.file_name[data_index]
            #,file_name:str,data_view,data_index
            sessionpath = self.LoadMRI.session_path
            #start unsupervised
            basestructs = self.region_names
            slice_orientation = data_view
            if self.LoadMRI.tag_file:
                if self.heatmap_unsuper:
                    _, self.heatmap_nii[data_index], _ = heatmap.get_relaxation_unsupervised(file_name, sessionpath, basestructs, slice_orientation)
                scale = self.visualize_heatmap(self.heatmap_nii[data_index][:,:,self.LoadMRI.slice_indices[data_index][0]],True,data_view,data_index)
                #add to intensity table
                table_class = getattr(self.MW.LoadMRI, f"intensity_table{data_index}")
                table_class.update_table('Heatmap', self.heatmap_nii[data_index].T,data_index,visibility_enabled=False)
            else:
                heatmaps, self.heatmap_nii[data_index], slice_idx = heatmap.get_relaxation(os.path.basename(file_name), self.mrid_names, sessionpath, basestructs, slice_orientation)
                #scale = self.visualize_heatmap(self.heatmap_nii[data_index][:,:,self.LoadMRI.slice_indices[data_index][0]],True,data_view,data_index)
                #change volume in intensity table
                table_class = getattr(self.MW.LoadMRI, f"intensity_table{data_index}")
                for i in range(table_class.table.rowCount()):
                    if table_class.table.item(i,1).text()=='Heatmap':
                        table_class.intensity_volumes[i]=self.heatmap_nii[data_index].T
            self.heatmap_slice[data_index] = self.heatmap_nii[data_index]

        self.LoadMRI.tag_file = False
        #after minimaps are created, rectanlges are still needed
        self.LoadMRI.minimap.create_small_rectangle(zoom_factor=1)
        #interaction!



    def update_heatmap(self,view_name,data_index,roi_indices=None):
        """
            Update the heatmap visualization for selected ROI indices.

            Parameters
            ----------
            roi_indices : array-like, optional
                Indices of the regions of interest to update. If None, the method
                will use the currently selected brush color from the paintbrush.

        """
        sessionpath = self.LoadMRI.session_path
        #start unsupervised
        basestructs = self.region_names
        if roi_indices is None:
            roi_indices = np.array([self.LoadMRI.paintbrush.color_combobox.index(self.LoadMRI.paintbrush.brush_color)])

        for roi_index in roi_indices:
            if roi_index <= self.num_regions:
                continue
            slice_orientation = view_name.capitalize()
            flip_axes = tuple(i for i, flip in enumerate(self.LoadMRI.axes_to_flip[data_index][::-1]) if flip)
            if view_name=='sagittal':
                seg_arr = np.swapaxes(self.LoadMRI.paintbrush.label_volume[data_index], 1, 2)
                segmentation = np.flip(seg_arr, axis=flip_axes)
            else:
                segmentation = np.flip(self.LoadMRI.paintbrush.label_volume[data_index], axis=flip_axes)
            file_name = self.file_name[data_index]

            heatmap_sim, _, slice_idx = heatmap.get_relaxation_simultaneously(file_name, roi_index, sessionpath, basestructs, slice_orientation, segmentation)
            self.heatmap_sim[data_index][:, :, slice_idx] = self.heatmap_sim[data_index][:, :, slice_idx] + heatmap_sim
            self.heatmap_slice[data_index] = self.heatmap_sim[data_index]

            self.visualize_heatmap(self.heatmap_sim[data_index][:,:,self.LoadMRI.slice_indices[data_index][0]],False,view_name,data_index) #heatmap_nii, z coordinate

            #change volume in intensity table
            table_class = getattr(self.MW.LoadMRI, f"intensity_table{data_index}")
            for i in range(table_class.table.rowCount()):
                if table_class.table.item(i,1).text()=='Heatmap':
                    table_class.intensity_volumes[i] =self.heatmap_sim[data_index].T


    def visualize_heatmap(self, img_slice,reset_camera:bool,view_name,data_index):
        """
            Visualize a single heatmap slice in the 4th VTK widget of the corresponding view.

            Parameters
            ----------
            img_slice : ndarray
                2D numpy array representing the heatmap slice to display.
            reset_camera : bool
                Whether to reset the camera to focus on the heatmap area.
        """
        # add to vtkwidgets for rendering and zooming
        vtk_widget = self.LoadMRI.vtk_widgets[3][view_name]
        if view_name != 'sagittal':
            img_slice = img_slice.T
            img_slice = np.flip(img_slice)
        else:
            img_slice = np.flip(img_slice,axis=0)

        vtk_data = numpy_support.numpy_to_vtk(img_slice.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        h, w = img_slice.shape
        spacing = (self.LoadMRI.spacing[data_index][2], self.LoadMRI.spacing[data_index][1], 1)

        #reset_camera = False
        if reset_camera:
            renderer,img_vtk = self.open_mainimage(vtk_widget,vtk_data, spacing,w,h,view_name)

            nonzero_y, nonzero_x = np.nonzero(img_slice)
            spacing_x, spacing_y = spacing[1], spacing[0]  # careful: VTK x=cols, y=rows
            if len(nonzero_x) == 0 or len(nonzero_y) == 0:
                ny, nx = np.nonzero(self.LoadMRI.paintbrush.label_volume[self.LoadMRI.slice_indices[0],:,:])
                # Get pixel bounds
                x_min, x_max = nx.min()-1, nx.max()+1
                y_min, y_max = ny.min()-1, ny.max()+1

                # Convert pixel coordinates to world coordinates
                self.center_x[data_index] = (x_min + x_max) / 2 * spacing_x
                self.center_y[data_index] = (y_min + y_max) / 2 * spacing_y
                self.width[data_index] = (x_max - x_min) * spacing_x
                self.height[data_index] = (y_max - y_min) * spacing_y

            else:
                # Get pixel bounds
                x_min, x_max = nonzero_x.min()-1, nonzero_x.max()+1
                y_min, y_max = nonzero_y.min()-1, nonzero_y.max()+1

                # Convert pixel coordinates to world coordinates
                self.center_x[data_index] = (x_min + x_max) / 2 * spacing_x
                self.center_y[data_index] = (y_min + y_max) / 2 * spacing_y
                self.width[data_index] = (x_max - x_min) * spacing_x
                self.height[data_index] = (y_max - y_min) * spacing_y

            ##camera_base = self.LoadMRI.renderers[0][view_name].GetActiveCamera()
            ##camera = renderer.GetActiveCamera()
            ##fp = camera_base.GetFocalPoint()
            ##pos = camera_base.GetPosition()
            ##self.center_x[data_index] = fp[0]
            ##self.center_y[data_index] = fp[1]
            ##sca = camera.GetParallelScale()
            ##self.width[data_index] = sca
            ##self.height[data_index] = sca


            #camera.SetFocalPoint(self.center_x[data_index], self.center_y[data_index], fp[2])
            #camera.SetPosition(self.center_x[data_index], self.center_y[data_index], pos[2])  # small offset in z
            #camera.ParallelProjectionOn()
            #camera.SetParallelScale(max(self.width[data_index], self.height[data_index])) #/2)

            # Add image to actor to then be added to renderer
            actor = vtk.vtkImageActor()
            scalar = img_vtk.GetScalarRange()
            actor.GetProperty().SetColorWindow(scalar[1])
            actor.GetProperty().SetColorLevel(scalar[1]/2)

            actor.SetInputData(img_vtk)
            actor.Modified()
            actor.GetProperty().SetInterpolationTypeToNearest() #Linear()
            actor.GetProperty().SetOpacity(1)

            # use a standard heat colormap (blue→green→yellow→red)
            lut = vtk.vtkLookupTable()
            vmin, vmax = np.percentile(vtk_data, [0,100])
            lut.SetNumberOfColors(256)
            lut.SetHueRange(0.667, 0)
            #lut.SetSaturationRange(0, 0)
            lut.SetTableRange(scalar[0], scalar[1])
            lut.Build()
            # make low values (blue end) transparent
            # now build alpha: all zero voxels → alpha = 0
            n = lut.GetNumberOfTableValues()
            for i in range(n):
                rgba = list(lut.GetTableValue(i))
                # Compute scalar value represented by this LUT entry
                scalar_value = np.min(img_slice) + (np.max(img_slice) - np.min(img_slice)) * (i / n)
                if scalar_value <= 0.0:      # intensity == 0
                    rgba[3] = 0.0            # fully transparent
                else:
                    rgba[3] = 1.0            # fully opaque
                lut.SetTableValue(i, *rgba)
            lut.Build()
            prop = actor.GetProperty()
            prop.SetLookupTable(lut)
            prop.UseLookupTableScalarRangeOn()

            renderer.AddActor(actor)

            self.LoadMRI.heatmap = True
            self.LoadMRI.renderers[3][view_name] = renderer
            self.actor_heatmap[data_index] = actor
        else:
            if not self.heatmap_unsuper:
                _,img_vtk = self.open_mainimage(vtk_widget,vtk_data, spacing,w,h)
                scalar = img_vtk.GetScalarRange()
                # use a standard heat colormap (blue→green→yellow→red)
                lut = vtk.vtkLookupTable()
                vmin, vmax = np.percentile(vtk_data, [0,100])
                lut.SetNumberOfColors(256)
                lut.SetHueRange(0.667, 0)
                #lut.SetSaturationRange(0, 0)
                lut.SetTableRange(scalar[0], scalar[1])
                lut.Build()
                # make low values (blue end) transparent
                # now build alpha: all zero voxels → alpha = 0
                n = lut.GetNumberOfTableValues()
                for i in range(n):
                    rgba = list(lut.GetTableValue(i))
                    # Compute scalar value represented by this LUT entry
                    scalar_value = np.min(img_slice) + (np.max(img_slice) - np.min(img_slice)) * (i / n)
                    if scalar_value <= 0.0:      # intensity == 0
                        rgba[3] = 0.0            # fully transparent
                    else:
                        rgba[3] = 1.0            # fully opaque
                    lut.SetTableValue(i, *rgba)
                lut.Build()
                prop = self.actor_heatmap[data_index].GetProperty()
                prop.SetLookupTable(lut)
                prop.UseLookupTableScalarRangeOn()
                self.heatmap_unsuper=True

            renderer = self.LoadMRI.renderers[3][view_name]
            img_vtk = vtk.vtkImageData()
            img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth
            img_vtk.SetSpacing(spacing)
            img_vtk.GetPointData().SetScalars(vtk_data)

            self.actor_heatmap[data_index].SetInputData(img_vtk)
            self.actor_heatmap[data_index].Modified()

            #camera_base = self.LoadMRI.renderers[0][view_name].GetActiveCamera()
            #fp = camera_base.GetFocalPoint()
            #pos = camera_base.GetPosition()

            #camera = renderer.GetActiveCamera()
            #camera.SetFocalPoint(self.center_x[data_index], self.center_y[data_index], fp[2])
            #camera.SetPosition(self.center_x[data_index], self.center_y[data_index], pos[2])  # small offset in z
            #camera.ParallelProjectionOn()
            #camera.SetParallelScale(max(self.width[data_index], self.height[data_index])/2)

        vtk_widget.GetRenderWindow().Render()
        self.add_legend(img_slice,reset_camera,data_index)

        if reset_camera:
            for _, renderer_items in self.LoadMRI.renderers.items():
                for vn, renderer in renderer_items.items():
                    if vn == view_name:
                        camera = renderer.GetActiveCamera()
                        pos = camera.GetPosition()
                        camera.SetFocalPoint(self.center_x[data_index], self.center_y[data_index], 0)
                        camera.SetPosition(self.center_x[data_index], self.center_y[data_index], pos[2])  # small offset in z
                        camera.ParallelProjectionOn()
                        camera.SetParallelScale(max(self.width[data_index], self.height[data_index]))
            scale = camera.GetParallelScale()
            self.LoadMRI.cursor.add_cursor4image(view_name,data_index, scale,img_vtk) #index = 0 at start
            return scale

    def open_mainimage(self,vtk_widget,vtk_data:vtk.vtkDataArray, spacing:tuple,w:int,h:int,view_name):
        """
            Open a new VTK renderer for a main image slice.
        """
        img_vtk = vtk.vtkImageData()
        img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth
        img_vtk.SetSpacing(spacing)
        img_vtk.GetPointData().SetScalars(vtk_data)

        #create new renderer
        renderer = vtk.vtkRenderer()
        vtk_widget.GetRenderWindow().AddRenderer(renderer)
        vtk_widget.GetRenderWindow().SetMultiSamples(16)
        renderer.SetUseDepthPeeling(1)
        renderer.SetMaximumNumberOfPeels(200)
        renderer.SetOcclusionRatio(0.05)

        actor = self.LoadMRI.actors[0][view_name]
        renderer.AddActor(actor)

        return renderer,img_vtk

    def add_legend(self,heatmap,reset_camera:bool,data_index):
        """
            Add and update a color legend (scalar bar) for the heatmap.

            Parameters
            ----------
            heatmap : ndarray
                The heatmap slice used to compute color range.
            reset_camera : bool
                Whether to create a new renderer for the legend or just update.
        """
        if reset_camera:
            vtk_widget = self.LoadMRI.vtk_widgets_legend[data_index]
            renderer = vtk.vtkRenderer()
            vtk_widget.GetRenderWindow().AddRenderer(renderer)

            lut = vtk.vtkLookupTable()
            lut.SetNumberOfTableValues(256)
            lut.Build()

            jet = plt.get_cmap('jet', 256)
            for i in range(256):
                r, g, b, a = jet(i)
                lut.SetTableValue(i, r, g, b, a)
            vmax = heatmap.max()
            lut.SetRange(0, vmax)

            # create scalarbar
            scalar_bar = vtk.vtkScalarBarActor()
            scalar_bar.SetLookupTable(lut)
            scalar_bar.SetNumberOfLabels(6)
            scalar_bar.SetOrientationToHorizontal()
            scalar_bar.SetMaximumWidthInPixels(400)
            scalar_bar.SetMaximumHeightInPixels(60)
            scalar_bar.SetPosition(0.05, 0.1)  # position in normalized viewport coords (0-1)
            scalar_bar.SetWidth(0.9)            # width as fraction of window
            scalar_bar.SetHeight(0.75)           # height as fraction of window
            scalar_bar.GetLabelTextProperty().SetColor(1, 1, 1)
            scalar_bar.GetLabelTextProperty().SetFontSize(13)

            renderer.AddActor2D(scalar_bar)
            self.LoadMRI.legend_lut[data_index] = lut
            self.LoadMRI.legend_scalar_bar[data_index] = scalar_bar


        vmax = heatmap.max()
        self.LoadMRI.legend_lut[data_index].SetRange(0, vmax)
        self.LoadMRI.legend_scalar_bar[data_index].SetLookupTable(self.LoadMRI.legend_lut[data_index])

        self.LoadMRI.vtk_widgets_legend[data_index].GetRenderWindow().Render()


