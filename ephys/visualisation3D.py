# This Python file uses the following encoding: utf-8
import os
import SimpleITK as sITK
import pyvista as pv
from pyvistaqt import QtInteractor
from pathlib import Path
import pandas as pd
from matplotlib.colors import ListedColormap
import numpy as np
from PySide6.QtWidgets import QVBoxLayout
from sklearn.decomposition import PCA
import matplotlib.colors as mcolors
import nibabel as nib
from PySide6.QtGui import QIcon

from PySide6.QtWidgets import QTableWidgetItem,QMenu
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import vtk
from concurrent.futures import ThreadPoolExecutor
import colorsys

class Visualisation3D:
    def __init__(self,session_path,MW,electrode_localisation=False,chMap=None,Ephys=None):
        self.electrode_localisation=electrode_localisation
        self.MW = MW
        self.ui = MW.ui
        self.enable_picking = False
        self.norm_vec = None
        self.parallel_projection = True
        self.poly_otherMrids = {}
        self.opacityBackground = 0.2
        self.opacityRegions = 0.9
        self.opacityRoI = 0.9
        self.session_path = session_path

        self.list_of_good_colors = [(1.0,1.0,1.0),(0.224,1.0,0.078),(1.0,0.078,0.576),(0.0,1.0,1.0),(1.0,0.647,0.0),(0.0,0.588,1.0),
            (1.0,1.0,0.0),(0.749,0.0,1.0),(0.0,1.0,0.588),(1.0,0.196,0.196),(1.0,0.392,1.0),(0.392,1.0,1.0),(1.0,0.784,0.0),
            (0.196,1.0,0.784),(1.0,0.314,0.0),(0.706,1.0,0.0),(0.0,0.784,1.0),(1.0,0.0,0.392),(0.588,0.196,1.0),(0.0,1.0,0.314),(1.0,0.627,0.196)
        ]

        self.clipped_meshes = False

        #set up layout
        pv.global_theme.background = 'black'

        if electrode_localisation:
            self.ui.tabWidget_visualisation.tabBar().setVisible(True)
            layout = QVBoxLayout(self.ui.vtkWidget_vis3D)
            layout.setContentsMargins(0, 0, 0, 0)
            self.plotter = QtInteractor(self.ui.vtkWidget_vis3D)

            self.ui.resetCamera_vis3D.clicked.connect(self.plotter.reset_camera)
            self.ui.change_perspective_vis3D.clicked.connect(self.change_perspective)
            self.combobox = self.ui.comboBox_anatRegion_vis3D
            self.spinbox = self.ui.spinBox_channelID_vis3D
            self.coord_x = self.ui.spinBox_x_vis3D
            self.coord_y = self.ui.spinBox_y_vis3D
            self.coord_z = self.ui.spinBox_z_vis3D
            self.comboBox_mrid = self.ui.comboBox_mridTag_vis3D
            self.comboBox_mrid.setEnabled(False)

            self.btn_change_perspective = self.ui.change_perspective_vis3D
            self.btn_slicex = self.ui.pushButton_slicex_vis3D
            self.btn_slicey = self.ui.pushButton_slicey_vis3D
            self.btn_slicez = self.ui.pushButton_slicez_vis3D
            self.ui.pushButton_Noslicing_vis3D.clicked.connect(self.no_slicing)

            self.table_excel = self.MW.ui.tableWidget_vis3D
            self.table_excel.cellClicked.connect(self.on_table_click)

            self.comboBox_mrid.addItems(self.MW.ButtonsGUI_4D.totalmrid)
            self.totalatlasCoordinates_pkl = self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl
            self.mrid_tags = self.MW.ButtonsGUI_4D.totalmrid
            self.index = self.MW.ButtonsGUI_4D.mrid_index
        else:
            self.Ephys = Ephys
            layout = QVBoxLayout(self.ui.vtkWidget_ephys)
            layout.setContentsMargins(0, 0, 0, 0)
            self.plotter = QtInteractor(self.ui.vtkWidget_ephys)

            self.ui.resetCamera_ephys.clicked.connect(self.plotter.reset_camera)
            self.ui.change_perspective_ephys.clicked.connect(self.change_perspective)
            self.combobox = self.ui.comboBox_anatRegion
            self.spinbox = self.ui.spinBox_channelID
            self.coord_x = self.ui.spinBox_x_ephys
            self.coord_y = self.ui.spinBox_y_ephys
            self.coord_z = self.ui.spinBox_z_ephys
            self.comboBox_mrid = self.ui.comboBox_mridTag

            self.btn_change_perspective = self.ui.change_perspective_ephys
            self.btn_slicex = self.ui.pushButton_slicex
            self.btn_slicey = self.ui.pushButton_slicey
            self.btn_slicez = self.ui.pushButton_slicez
            self.ui.pushButton_Noslicing.clicked.connect(self.no_slicing)

            combo_items = []
            for i, mrid in enumerate(self.Ephys.mrid_info.mrid_coordinates):
                text = f"{mrid} (Channel Group: {i})"
                combo_items.append(text)
            self.comboBox_mrid.addItems(combo_items)

            self.MW.ui.pushButton_selectAll.clicked.connect(lambda: self.toggle_all_channels(Qt.Checked))
            self.MW.ui.pushButton_deselectAll.clicked.connect(lambda: self.toggle_all_channels(Qt.Unchecked))

            self.MW.ui.pushButton_showChannels.toggled.connect(self.show_only_selected_channels)
            self.MW.ui.horizontalSlider_ElectrodeRegion.setValue(self.opacityRoI*100)
            self.MW.ui.horizontalSlider_OtherRegions.setValue(self.opacityRegions*100)
            self.MW.ui.horizontalSlider_Background.setValue(self.opacityBackground*100)

            self.mrid_tags = self.Ephys.mrid_info.mrid_tags
            self.index = self.Ephys.mrid_info.xml_group_idx
            self.totalatlasCoordinates_pkl = self.Ephys.mrid_info.totalatlasCoordinates_pkl

        self.create_atlas_region_file(self.mrid_tags[self.index])

        self.btn_slicex.clicked.connect(self.slice_vol_x)
        self.btn_slicey.clicked.connect(self.slice_vol_y)
        self.btn_slicez.clicked.connect(self.slice_vol_z)

        layout.addWidget(self.plotter)

        self.load_atlas(self.filepath_atlas)


        self.plotter.iren.add_observer('MouseMoveEvent', self.on_hover)
        self.hover_label = vtk.vtkTextActor()
        self.hover_label.SetInput("")
        self.hover_label.GetTextProperty().SetFontSize(14)
        self.hover_label.GetTextProperty().SetColor(1, 1, 1)  # white
        self.plotter.renderer.AddActor2D(self.hover_label)



    def initialize_mridTag(self,mrid,chMap=None):
        if not hasattr(self,'chMap'):
            self.chMap = chMap

        self.old_target_idx = 0 #Clear Label
        self.spinbox.setMinimum(min(self.chMap))
        self.spinbox.setMaximum(max(self.chMap))
        self.update_electrode_points(self.filepath_atlas,mrid)

        if self.electrode_localisation:
            self.fill_table(channels=[],dead_channels=[])

        index = self.comboBox_mrid.findText(mrid, Qt.MatchContains)
        if index != -1:
            self.comboBox_mrid.setCurrentIndex(index)

        self.add_other_mrids()


    def channel_changed(self,index):
        point_index = self.chMap.index(index)
        point = self.coords_list[point_index]
        self.show_coords(point)

    def on_hover(self, obj, event):
        x, y = self.plotter.iren.get_event_position()
        picker = vtk.vtkPropPicker()
        picker.InitializePickList()
        picker.AddPickList(self.plotter.actors['background'])
        picker.AddPickList(self.plotter.actors['atlas'])
        picker.SetPickFromList(True)
        picker.PickProp(x, y, self.plotter.renderer)
        actor = picker.GetViewProp()
        point = picker.GetPickPosition()

        if actor==self.plotter.actors['background']:
            mesh = actor.mapper.dataset
            idx = mesh.find_closest_cell(point)
            nifti_value = mesh.cell_data['NIFTI'][idx]
            #nifti_value = int(round(mesh.point_data['NIFTI'][idx]))
        elif actor==self.plotter.actors['atlas']:
            mesh = actor.mapper.dataset
            idx = mesh.find_closest_cell(point)
            nifti_value = mesh.cell_data['NIFTI'][idx]
        else:
            self.hover_label.SetInput("")
            return

        row_index = self.atlaslabelsdf[self.atlaslabelsdf['IDX'] == nifti_value].index[0]
        label = self.atlaslabelsdf['LABEL'].values[row_index]

        self.hover_label.SetPosition(x + 5, y + 5)
        self.hover_label.SetInput(f"{label}")
        self.plotter.render()

    def on_click(self,point):
        idx = np.where(np.all(np.isclose(self.coords_list, point, atol=0.025), axis=1))[0]
        if len(idx)==0:
            for i, tag in enumerate(self.mrid_tags):
                if i == self.index:
                    continue
                closest_idx = self.poly_otherMrids[i].find_closest_point(point)
                closest_pt = self.poly_otherMrids[i].points[closest_idx]
                if np.allclose(closest_pt, point, atol=1.0):  # tune tolerance
                    self.Ephys.change_mridTAG(i)
                    return
        else:
            self.show_coords(point)


    def show_coords(self,point):
        idx = np.where(np.all(np.isclose(self.coords_list, point, atol=0.025), axis=1))[0]

        if len(idx)==0:
            return

        if not self.electrode_localisation:
            if self.chMap[idx[0]] in self.Ephys.ephys_data.dead_channels:
                return

        if len(idx):
            row = self.points_data.iloc[idx[0]]
            self.coord_x.setValue(point[0]/self.spacing+1)
            self.coord_y.setValue(point[1]/self.spacing+1)
            self.coord_z.setValue(point[2]/self.spacing+1)
            self.spinbox.blockSignals(True)
            self.spinbox.setValue(self.chMap[idx[0]])

            self.spinbox.blockSignals(False)
            index = self.combobox.findText(row['Channel Label'])
            if index != -1:
                self.combobox.setCurrentIndex(index)

            if self.clipped_meshes:
                self.render_clipped(self.render_normal)
                self.plotter.add_points(
                    point,
                    color="red",
                    point_size=20,
                    name="picked_point",
                    render_points_as_spheres=True,
                    reset_camera=False,
                    render=False
                )
                self.plotter.set_focus(point)
            else:
                self.manually_pick_point(point,idx=idx[0])

    def delete_volumes(self,mrid,new_label_idx, point_idx):
        self.plotter.iren.remove_observer(self.on_hover)

        self.norm_vec = None
        ## load atlas new
        img = nib.load(self.filepath_atlas)
        data = img.get_fdata().astype(int)[::3, ::3, ::3]
        vol_small = pv.ImageData()
        vol_small.dimensions = np.array(data.shape) + 1
        vol_small.spacing = tuple(s * 3 for s in img.header.get_zooms()[:3])
        vol_small.origin = (0.0, 0.0, 0.0)
        vol_small.cell_data['NIFTI'] = data.flatten(order='F')
        self.unique_vals = np.unique(vol_small.active_scalars)
        nifti_vals = np.round(vol_small.cell_data['NIFTI']).astype(int)
        colors = np.array([self.cmap.colors[int(v)] for v in nifti_vals])
        vol_small.cell_data['colors'] = (colors[:, :3] * 255).astype(np.uint8)
        self.mesh_atlas = vol_small
        self.mesh_atlas = self.mesh_atlas.threshold(value=[1, 502], scalars='NIFTI')
        ## load excel new
        self.update_electrode_points(os.path.join(self.filepath_atlas),mrid)

        #update background
        self.background_small = self.background_small.threshold(value=0.5)
        for val in self.unique_vals:
            self.background_small = self.background_small.threshold(value=[val - 0.5, val + 0.5],invert=True)
        idx_colors = 0
        if np.all(self.rgba[new_label_idx, :3] == [0, 0, 0]): #self.rgba[new_label_idx, :3] == [0 0 0]:
            self.rgba[new_label_idx, :3] = self.list_of_good_colors[idx_colors]
            self.rgba[new_label_idx, 3] = 1
            idx_colors += 1
            self.cmap = ListedColormap(self.rgba)

        #load new
        self.manually_pick_point([],idx=point_idx)

        self.plotter.iren.remove_observer(self.on_hover)


    def change_perspective(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if self.parallel_projection==True:
            self.plotter.disable_parallel_projection()
            self.btn_change_perspective.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","projection_prespective.png")))
            self.parallel_projection=False
        else:
            self.plotter.enable_parallel_projection()
            self.btn_change_perspective.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","projection_parallel.png")))
            self.parallel_projection=True


    def manually_pick_point(self,point,idx=None,resetTo3D=False):
        if len(point)==0:
            self.spinbox.setValue(self.chMap[idx])
            index = self.combobox.findText(self.points_data.iloc[idx]['Channel Label'])
            if index != -1:
                self.combobox.setCurrentIndex(index)
            point = self.coords_list[idx]
            self.coord_x.setValue(point[0]/self.spacing+1)
            self.coord_y.setValue(point[1]/self.spacing+1)
            self.coord_z.setValue(point[2]/self.spacing+1)
        else:
            point = np.array(point) #*self.spacing
            index = self.combobox.findText(self.points_data.iloc[idx]['Channel Label'])

        target_idx = self.atlaslabelsdf['IDX'].values[index]
        if self.old_target_idx != target_idx or resetTo3D:
            self.old_target_idx = target_idx
            if target_idx==0:
                self.plotter.remove_actor('atlas')
                self.plotter.remove_actor('atlas_region')
            else:
                volomue_thresholded = self.mesh_atlas.threshold([target_idx - 0.5, target_idx + 0.5], invert=True)
                nifti_vals = np.round(volomue_thresholded.cell_data['NIFTI']).astype(int)
                colors = np.array([self.cmap.colors[int(v)] for v in nifti_vals])
                volomue_thresholded.cell_data['colors']= (colors[:, :3]*255).astype(np.uint8)
                surface = volomue_thresholded.extract_surface(algorithm='dataset_surface')
                smoothed_vol = surface.smooth_taubin(n_iter=50, pass_band=0.1)

                self.plotter.add_mesh(
                    smoothed_vol,
                    scalars='colors',
                    rgb=True,
                    show_scalar_bar=False,
                    name='atlas',
                    style='surface',
                    pickable=False,
                    opacity=self.opacityRegions,
                    reset_camera=False,
                    render=False,
                    culling='front',
                )

                ##REGION MESH
                region_mesh = self.mesh_atlas.threshold([target_idx - 0.5, target_idx + 0.5], invert=False)
                surface = region_mesh.extract_surface(algorithm='dataset_surface')
                smoothed_region = surface.smooth_taubin(n_iter=50, pass_band=0.1)
                color = self.cmap.colors[target_idx]
                self.plotter.add_mesh(
                    smoothed_region, #region_mesh,
                    color=color,
                    opacity=self.opacityRoI,
                    show_scalar_bar=False,
                    name='atlas_region',
                    style='surface',
                    pickable=False,
                    reset_camera=False,
                    render=False,
                    culling='front',
                )

                smoothed_vol = smoothed_vol.cell_data_to_point_data()

        self.plotter.add_points(
            point,
            color="red",
            point_size=20,
            name="picked_point",
            render_points_as_spheres=True,
            reset_camera=False,
            render=False
        )

        #look at point and render
        self.focus_on_point(point,idx)
        #self.table_excel.verticalScrollBar().setValue(idx / (len(self.Ephys.ephys_data.all_channels)-1)*self.table_excel.verticalScrollBar().maximum())


    def load_atlas(self,filepath):
        # Define the two independent loading tasks
        def load_atlas_mesh():
            img = nib.load(filepath)
            data = img.get_fdata().astype(int)[::3, ::3, ::3]
            vol_small = pv.ImageData()
            vol_small.dimensions = np.array(data.shape) + 1
            vol_small.spacing = tuple(s * 3 for s in img.header.get_zooms()[:3])
            vol_small.origin = (0.0, 0.0, 0.0)
            vol_small.cell_data['NIFTI'] = data.flatten(order='F')

            unique_vals = np.unique(vol_small.active_scalars)
            return vol_small, unique_vals

        def load_background_mesh():
            background_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                           "Files", 'Atlas', 'WHS_SD_rat_atlas_v4.nii.gz')

            img = nib.load(background_path)
            scale_background= 3
            data = img.get_fdata().astype(int)[::scale_background, ::scale_background, ::scale_background]
            mesh_small = pv.ImageData()
            mesh_small.dimensions = np.array(data.shape) + 1
            mesh_small.spacing = tuple(s * scale_background for s in img.header.get_zooms()[:3])
            mesh_small.origin = (0.0, 0.0, 0.0)
            mesh_small.cell_data['NIFTI'] = data.flatten(order='F')

            return mesh_small

        def load_labels():
            labels_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                       "Files", 'Atlas', 'WHS_SD_rat_atlas_v4.label')
            if Path(labels_path).is_file():
                return pd.read_csv(labels_path, comment='#', sep='\s+',
                                   names=['IDX', 'R', 'G', 'B', 'A', 'VIS', 'MSH', 'LABEL'])
            return None

        # Run all three file reads in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_atlas = executor.submit(load_atlas_mesh)
            future_background = executor.submit(load_background_mesh)
            future_labels = executor.submit(load_labels)

            vol_small,self.unique_vals = future_atlas.result()
            background_mesh = future_background.result()
            self.atlaslabelsdf = future_labels.result()
            self.background_mesh = background_mesh

            background_small = background_mesh.threshold(value=0.5)
            for val in self.unique_vals:
                background_small = background_small.threshold(value=[val - 0.5, val + 0.5],invert=True)
            self.background_small = background_small


        if 'background' not in self.plotter.actors:
            self.add_background(background_mesh)  # pass mesh directly
        max_idx = int(self.atlaslabelsdf['IDX'].max())
        self.rgba = np.zeros((max_idx + 1, 4))
        rgba_background = np.zeros((max_idx + 1, 4))
        #rgba_background[:] = [0.9, 0.9, 0.9, 1]
        idx_colors = 0
        for _, row in self.atlaslabelsdf.iterrows():
            if row['IDX'] in self.unique_vals:
                self.rgba[int(row['IDX']), :3] = self.list_of_good_colors[idx_colors]
                self.rgba[int(row['IDX']), 3] = 1
                idx_colors += 1
            else:
                r, g, b = row['R']/255, row['G']/255, row['B']/255
                r, g, b = self.desaturate((r, g, b), 0.25)  # 0=grey, 1=full color
                rgba_background[int(row['IDX'])] = [r, g, b, 1]
                #rgba_background[int(row['IDX']), :] = [row['R']/255, row['G']/255, row['B']/255, 0.1]

        self.cmap = ListedColormap(self.rgba)
        self.cmap_background = ListedColormap(rgba_background)

        self.combobox.addItems(self.atlaslabelsdf['LABEL'].values)
        self.opacity = np.full(len(self.atlaslabelsdf), 0.5)
        self.opacity[0]=0

        self.plotter.add_axes()

        nifti_vals = np.round(vol_small.cell_data['NIFTI']).astype(int)
        colors = np.array([self.cmap.colors[int(v)] for v in nifti_vals])
        vol_small.cell_data['colors'] = (colors[:, :3] * 255).astype(np.uint8)
        self.mesh_atlas = vol_small
        self.mesh_atlas = self.mesh_atlas.threshold(value=[1, 502], scalars='NIFTI')

    def desaturate(self,rgb, factor):
        r, g, b = rgb
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        s *= factor  # reduce saturation
        return colorsys.hsv_to_rgb(h, s, v)


    def update_electrode_points(self,filepath,mrid):
        if "electrode_points" not in self.plotter.actors:
            img = sITK.ReadImage(filepath)
            self.spacing = img.GetSpacing()[0]

        points_electrodes_path = os.path.join(os.path.join(os.path.join(self.session_path,"analysed")),mrid,'channel_atlas_coordinates.xlsx')
        self.points_data = pd.read_excel(points_electrodes_path,header=0)
        self.coords_list = self.points_data.iloc[:, -3:].values*self.spacing

        point_colors = []
        rgb = self.atlaslabelsdf[['R', 'G', 'B']].values / 255
        for label in self.points_data.iloc[:, 1].values:
            idx = np.where(self.atlaslabelsdf['IDX'].values ==label)  # fallback: gray
            base_color = rgb[idx]
            r, g, b = mcolors.to_rgb(base_color)
            comp_color = (1 - r, 1 - g, 1 - b) #complementary_color(base_color)
            point_colors.append(comp_color)

        poly = pv.PolyData(np.array(self.coords_list))
        poly['Labels'] = self.chMap
        poly.point_data['colors'] = point_colors

        self.plotter.add_mesh(
            poly,
            color='blue',
            point_size=10,
            name="electrode_points",
            render_points_as_spheres=True,
            render=False,show_scalar_bar=False, reset_camera=False
        )

        self.plotter.add_point_labels(poly, 'Labels', point_size=20, font_size=12,name='electrode_labels',reset_camera=False,render=False,)
        self.points_poly = poly
        if self.enable_picking==False:
            self.plotter.enable_point_picking(callback=self.on_click,show_message=False,left_clicking=True,color='red',picker='point',show_point=False)
            self.enable_picking = True




    def add_background(self,mesh_downsampled):
        background = mesh_downsampled.threshold(value=0.5)
        background = background.extract_surface(algorithm='dataset_surface')
        background = background.clean().triangulate()
        background = background.fill_holes(hole_size=1e10)
        background = background.clean().triangulate()

        smoothed = background.smooth_taubin(n_iter=50, pass_band=0.1)


        self.plotter.add_mesh(
            smoothed,
            color='white',
            opacity=self.opacityBackground,
            style='surface',
            line_width=0.5,
            pickable=False,
            name='background',
            reset_camera=False,
            render=False,
            culling='front',
        )

        self.clipped_meshes= False


    def add_other_mrids(self):
        ## show the other tags -> clickable switch to them (Label = Name)
        points = []
        lines_connectivity = []
        self.poly_list = []

        for i in range(len(self.totalatlasCoordinates_pkl)):
            if i == self.index:
                self.poly_list.append([])
                self.poly_otherMrids[i] = None
                if self.mrid_tags[i] in self.plotter.actors:
                    self.plotter.remove_actor(self.mrid_tags[i])
                    self.plotter.remove_actor(self.mrid_tags[i] + '_label')
                continue

            atlasCoordinates = self.totalatlasCoordinates_pkl[i]

            linepoints = np.array(atlasCoordinates)*self.spacing

            for j in range(len(linepoints) - 1):
                p1 = linepoints[j]
                p2 = linepoints[j + 1]
                t = np.linspace(0, 1, 102)
                idx = len(points)
                interpolated = p1 + t[:, None] * (p2 - p1)
                n = len(interpolated)
                points.extend(interpolated)
                lines_connectivity.extend([n] + list(range(idx, idx + n)))

            poly = pv.PolyData()
            poly.points = np.array(points)
            poly.lines = np.array(lines_connectivity)
            self.poly_list.append(poly)
            self.plotter.add_mesh(poly, color='gray', line_width=8,name=self.mrid_tags[i],reset_camera=False,render=False,pickable=True)
            self.plotter.add_point_labels([poly.center],[self.mrid_tags[i]],font_size=10,text_color='white',name=self.mrid_tags[i] + '_label',reset_camera=False,render=False)
            self.poly_otherMrids[i] = poly

        if self.electrode_localisation:
            self.manually_pick_point(point=[],idx=0)



    def focus_on_point(self, point,index,distance=4):
        """point = [x, y, z]"""
        #already focuing on this point
        focal_point = self.plotter.camera.focal_point
        if np.array_equal(focal_point, point):#if focal_point==point:
            return

        # Preserve viewing direction
        if self.parallel_projection==True:
            self.plotter.disable_parallel_projection()

        if self.norm_vec is None:
            self.norm_vec = self.find_best_fit_plane()
        new_pos = np.array(point) + self.norm_vec * distance  # distance controls how close

        self.plotter.camera_position.focal_point = np.array(point)
        self.plotter.set_position(new_pos)
        self.plotter.set_focus(point)

        self.plotter.camera.roll = -90 #aligns with xy-axis at the bottom of render

        if self.parallel_projection==True:
            self.plotter.enable_parallel_projection()

        if not self.electrode_localisation:
            self.Ephys.VisEphys.highlight_channel(index)
        else:
            self.table_excel.selectRow(index)


    def find_best_fit_plane(self):
        """Find the plane where most points lie and return its normal vector"""
        coords = np.array(self.coords_list)

        # Center the points
        centroid = coords.mean(axis=0)
        coords_centered = coords - centroid

        # PCA to find principal components
        pca = PCA(n_components=3)
        pca.fit(coords_centered)

        # The normal to the plane is the direction of least variance (smallest eigenvalue)
        normal_vector = pca.components_[-1]  # Last component (smallest variance)

        normal_vector = normal_vector/np.linalg.norm(normal_vector)
        return normal_vector


    def slice_vol_x(self,val):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if self.btn_slicex.isChecked():
            normal = '-x'
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_coronal_back.png")))
        else:
            normal = 'x'
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_coronal_front.png")))

        self.render_clipped(normal)


    def slice_vol_y(self,val):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if self.btn_slicey.isChecked():
            normal = '-y'
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_coronal_back.png")))
        else:
            normal = 'y'
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_coronal_front.png")))

        self.render_clipped(normal)


    def slice_vol_z(self,val):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if self.btn_slicez.isChecked():
            normal = '-z'
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_axial_bottom.png")))
        else:
            normal = 'z'
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_axial_top.png")))

        self.render_clipped(normal)


    def no_slicing(self,val):
        # reset opacity
        self.MW.ui.horizontalSlider_Background.blockSignals(True)
        self.MW.ui.horizontalSlider_ElectrodeRegion.blockSignals(True)
        self.MW.ui.horizontalSlider_OtherRegions.blockSignals(True)
        self.opacityBackground = 0.2
        self.opacityRegions = 0.9
        self.opacityRoI = 0.9
        self.MW.ui.horizontalSlider_Background.setValue(self.opacityBackground*100)
        self.MW.ui.horizontalSlider_ElectrodeRegion.setValue(self.opacityRoI*100)
        self.MW.ui.horizontalSlider_OtherRegions.setValue(self.opacityRegions*100)
        self.MW.ui.horizontalSlider_Background.blockSignals(False)
        self.MW.ui.horizontalSlider_ElectrodeRegion.blockSignals(False)
        self.MW.ui.horizontalSlider_OtherRegions.blockSignals(False)
        self.MW.ui.horizontalSlider_ElectrodeRegion.setEnabled(True)

        self.hover_label.SetInput("")

        self.add_background(self.background_mesh)
        items = self.table_excel.selectedItems()
        if items:
            row = items[0].row()
            self.manually_pick_point(point=[],idx=row,resetTo3D=True)

        self.update_electrode_points(self.filepath_atlas,self.Ephys.mrid_info.mrid)
        self.add_other_mrids()

    def render_clipped(self,normal):
        self.render_normal = normal

        x0 = (self.coord_x.value()-1)*self.spacing
        y0 = (self.coord_y.value()-1)*self.spacing
        z0 = (self.coord_z.value()-1)*self.spacing
        #base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        axis_map = {'x': 0, 'y': 1, 'z': 2}
        axis = normal.lstrip('-')
        col = axis_map[axis]
        coord = {'x': x0, 'y': y0, 'z': z0}[axis]

        if normal.startswith('-'):
            mask = self.points_poly.points[:, col] >= coord
            roll_angle = 0
            print(col,flush=True)
            if col==0:
                vector = [-1,0,0]
                self.plotter.camera.up = (0, 1,0)
                roll_angle = 90
            elif col==1:
                vector = [0,-1,0]
                self.plotter.camera.up = (0, 0,1)
                roll_angle = 0
            elif col==2:
                vector = [0,0,-1]
                self.plotter.camera.up = (0, 1,0)
                roll_angle = 0
        else:
            mask = self.points_poly.points[:, col] <= coord
            if col==0:
                vector = [1,0,0]
                self.plotter.camera.up = (0, -1,0)
                roll_angle = -90
            elif col==1:
                vector = [0,1,0]
                self.plotter.camera.up = (0, 0,-1)
                roll_angle = 180
            elif col==2:
                vector = [0,0,1]
                self.plotter.camera.up = (0, -1,0)
                roll_angle = 0

        # set camera so that slice is in 2D view
        focal_point = self.plotter.camera.focal_point
        # Preserve viewing direction
        if self.parallel_projection==True:
            self.plotter.disable_parallel_projection()
        distance = 60
        new_pos = np.array(focal_point) + np.array(vector) * distance  # distance controls how close
        self.plotter.set_position(new_pos)

        self.plotter.camera.roll = roll_angle
        if self.parallel_projection==True:
            self.plotter.enable_parallel_projection()

        clipped_poly_otherMrids = {}
        clipped_background = self.background_small.clip(normal=normal, origin=(x0, y0, z0))
        clipped_atlas = self.mesh_atlas.clip(normal=normal, origin=(x0, y0, z0),crinkle=True)
        clipped_poly = self.points_poly.clip(normal=normal, origin=(x0, y0, z0))

        clipped_labels = np.array(self.points_poly['Labels'])[mask]
        clipped_poly['Labels'] = clipped_labels

        for i in range(len(self.totalatlasCoordinates_pkl)):
            if i == self.index:
                clipped_poly_otherMrids[i] = None
                continue
            clipped_poly_otherMrids[i] = self.poly_otherMrids[i].clip(normal=normal, origin=(x0, y0, z0))

        self.MW.ui.horizontalSlider_Background.blockSignals(True)
        self.MW.ui.horizontalSlider_ElectrodeRegion.blockSignals(True)
        self.opacityBackground = 1
        self.opacityRegions = 1
        self.MW.ui.horizontalSlider_Background.setValue(self.opacityBackground*100)
        self.MW.ui.horizontalSlider_OtherRegions.setValue(self.opacityRegions*100)
        self.MW.ui.horizontalSlider_Background.blockSignals(False)
        self.MW.ui.horizontalSlider_ElectrodeRegion.blockSignals(False)
        self.MW.ui.horizontalSlider_ElectrodeRegion.setEnabled(False)

        nifti_vals = np.round(clipped_background.cell_data['NIFTI']).astype(int)
        colors = np.array([self.cmap_background.colors[int(v)] for v in nifti_vals])
        clipped_background.cell_data['colors'] = (colors[:, :3] * 255).astype(np.uint8)

        clipped_background = clipped_background.extract_surface(algorithm='dataset_surface')
        clipped_background = clipped_background.smooth_taubin(n_iter=50, pass_band=0.1)

        self.plotter.add_mesh(
            clipped_background,
            scalars='colors',
            rgb=True,
            show_scalar_bar=False,
            opacity=self.opacityBackground,
            style='surface',
            line_width=0.5,
            pickable=True,
            name='background',
            reset_camera=False,
            render=False,
        )

        clipped_atlas = clipped_atlas.extract_surface(algorithm='dataset_surface').smooth_taubin(n_iter=50, pass_band=0.1)

        self.plotter.add_mesh(
            clipped_atlas,
            scalars='colors',
            rgb=True,
            show_scalar_bar=False,
            name='atlas',
            style='surface',
            pickable=True,
            opacity=self.opacityRegions,
            reset_camera=False,
            render=False,
        )

        if 'atlas_region' in self.plotter.actors:
            self.plotter.remove_actor('atlas_region')

        self.plotter.add_mesh(
            clipped_poly,
            color='blue',
            point_size=10,
            name="electrode_points",
            render_points_as_spheres=True,
            render=False,show_scalar_bar=False, reset_camera=False
        )

        self.plotter.remove_actor('electrode_labels')

        self.plotter.add_point_labels(
            clipped_poly, 'Labels', point_size=20,
            font_size=12,name='electrode_labels',
            reset_camera=False,render=False
        )

        for i,poly_otherMrid in clipped_poly_otherMrids.items():
            if poly_otherMrid is None or poly_otherMrid.n_points == 0:
                self.plotter.remove_actor(self.mrid_tags[i])
                self.plotter.remove_actor(self.mrid_tags[i] + '_label')
                continue
            self.plotter.add_mesh(
                poly_otherMrid, color='gray', line_width=8,
                name=self.mrid_tags[i],
                reset_camera=False,render=False,pickable=True
            )
            self.plotter.add_point_labels(
                [clipped_poly_otherMrids[i].center],
                [self.mrid_tags[i]],
                font_size=10,
                text_color='white',
                name=self.mrid_tags[i] + '_label',
                reset_camera=False,
                render=False
            )

        self.clipped_meshes = True




    def fill_table(self,channels,dead_channels):
        df = self.points_data
        df['Coordinates'] = df[['Atlas x', 'Atlas y', 'Atlas z']].astype(str).apply(', '.join, axis=1)
        df_col = df['Channel']
        df = df.drop(columns=['Atlas x', 'Atlas y', 'Atlas z','Channel'])
        if channels:
            df['Channel ID']=channels
        df = df.rename(columns={'Channel ID': 'ID'})

        self.table_excel.setRowCount(len(df))
        self.table_excel.setColumnCount(len(df.columns)+1)
        self.table_excel.setHorizontalHeaderLabels(['All'] + df.columns.tolist())
        self.table_excel.verticalHeader().setVisible(False)

        #add checkbox for selelcting / deselecing all channels
        checkbox_item = QTableWidgetItem()
        checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        checkbox_item.setCheckState(Qt.Checked)
        self.table_excel.setItem(0, 0, checkbox_item)

        # Fill
        for row_idx, row in df.iterrows():
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Checked)
            self.table_excel.setItem(row_idx, 0, checkbox_item)

            max_idx = self.atlaslabelsdf['IDX'].max()
            rgba = self.cmap(df_col[row_idx] / max_idx)
            r, g, b,a = rgba
            color = QColor(r*255, g*255, b*255)
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setForeground(color)
                self.table_excel.setItem(row_idx, col_idx+1, item)
                if df['ID'][row_idx] in dead_channels:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                    color = QColor(0.5*255, 0.5*255, 0.5*255) #GREY
                    item.setForeground(color)
                    checkbox_item.setCheckState(Qt.Unchecked)
                    checkbox_item.setFlags(checkbox_item.flags() & ~Qt.ItemIsEnabled)

        self.table_excel.resizeColumnsToContents()
        self.table_excel.resizeRowsToContents()

        self.table_excel.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_excel.customContextMenuRequested.connect(self.on_table_right_click)
        self.table_excel.itemChanged.connect(self.on_channel_toggled)

        ##HEADER CHECKBOX
        # after setting up the table
        #checkbox_item = QTableWidgetItem()
        #checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        #checkbox_item.setCheckState(Qt.Checked)
        #self.table_excel.setHorizontalHeaderItem(0,checkbox_item)


    def on_channel_toggled(self, item_table):#, state):
        if item_table.column() != 0:  # only care about checkbox column
            return

        checked = item_table.checkState() == Qt.Checked
        row = item_table.row()

        channel_number = int(self.table_excel.item(row, 1).text())
        # add logic here
        if not self.electrode_localisation:
            if checked:
                #add channel to plot, but keeping the indices the same
                idx = next((self.Ephys.VisEphys.displayed_channels.index(v) for v in self.Ephys.ephys_data.all_channels[:self.Ephys.ephys_data.all_channels.index(channel_number)][::-1] if v in self.Ephys.VisEphys.displayed_channels), None)
                if idx is None:
                    self.Ephys.VisEphys.displayed_channels.insert(0, channel_number)
                else:
                    self.Ephys.VisEphys.displayed_channels.insert(idx + 1, channel_number)
                self.Ephys.VisEphys.visualize_data(self.Ephys.VisEphys.displayed_channels)
            else:
                #remove channel from plot
                if channel_number in self.Ephys.VisEphys.displayed_channels:
                    self.Ephys.VisEphys.displayed_channels.remove(channel_number)
                    self.Ephys.VisEphys.visualize_data(self.Ephys.VisEphys.displayed_channels)

    def on_table_right_click(self, position):
        menu = QMenu()
        row = self.table_excel.rowAt(position.y())
        checkbox_item = self.table_excel.item(row, 0)

        if checkbox_item.checkState() == Qt.Checked:
            action_skip_channel = menu.addAction("Skip Channel")
            action_unskip_channel = None
        else:
            action_skip_channel = None
            action_unskip_channel = menu.addAction("Unskip Channel")
        action = menu.exec(self.table_excel.viewport().mapToGlobal(position))

        if action == action_skip_channel:
            self.skip_channel(row,True)
        elif action == action_unskip_channel:
            self.skip_channel(row,False)


    def skip_channel(self,row,skip):
        channel_number = int(self.table_excel.item(row, 1).text())
        checkbox_item = self.table_excel.item(row, 0)
        if skip:
            checkbox_item.setCheckState(Qt.Unchecked)
            checkbox_item.setFlags(checkbox_item.flags() & ~Qt.ItemIsEnabled)
            color = QColor(0.5*255, 0.5*255, 0.5*255) #GREY
            # make table row grey and uneditable
            for col_idx in 1,2,3:
                item = self.table_excel.item(row, col_idx)
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setForeground(color)
            #remove channel from plot
            idx = next((self.Ephys.ephys_data.dead_channels.index(v) for v in self.Ephys.ephys_data.all_channels[:self.Ephys.ephys_data.all_channels.index(channel_number)][::-1] if v in self.Ephys.ephys_data.dead_channels), None)
            if idx is None:
                self.Ephys.ephys_data.dead_channels.insert(0, channel_number)
            else:
                self.Ephys.ephys_data.dead_channels.insert(idx + 1, channel_number)

            self.Ephys.change_xml_file(channel_number,1)
        else:
            checkbox_item.setCheckState(Qt.Checked)
            checkbox_item.setFlags(checkbox_item.flags() | Qt.ItemIsEnabled)
            # make table row colorful and editable
            max_idx = self.atlaslabelsdf['IDX'].max()
            rgba = self.cmap(self.points_data['Channel'].iloc[row] / max_idx)
            r, g, b,a = rgba
            color = QColor(r*255, g*255, b*255,a*255)
            for col_idx in 1,2,3:
                item = self.table_excel.item(row, col_idx)
                item.setFlags(item.flags() | Qt.ItemIsEnabled)
                item.setForeground(color)
            self.Ephys.ephys_data.dead_channels.remove(channel_number)
            self.Ephys.change_xml_file(channel_number,0)



    def on_table_click(self,row,column):
        item = self.table_excel.item(row, column)
        if item and not (item.flags() & Qt.ItemIsEnabled):
            return

        # if unclicked -> click
        item_clicked = self.table_excel.item(row, 0)
        if item_clicked.checkState() != Qt.Checked and row!=0:
            item_clicked.setCheckState(Qt.Checked)

        point = self.coords_list[row]
        self.show_coords(point)

        if self.electrode_localisation:
            self.table_excel.selectRow(row)
        else:
            self.Ephys.VisEphys.highlight_channel(row)


    def toggle_all_channels(self,state):
        self.table_excel.blockSignals(True)
        channels = []
        for row_idx in range(self.table_excel.rowCount()):
            item = self.table_excel.item(row_idx, 0)
            if item and item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(state)
                if state==Qt.Checked:
                    channels.append(int(self.table_excel.item(row_idx, 1).text()))
        self.table_excel.blockSignals(False)

        self.Ephys.VisEphys.visualize_data(channels=channels)


    def show_only_selected_channels(self,checked):
        if checked:
            self.MW.ui.pushButton_showChannels.setText('Show only selected Channels')
            self.MW.ui.widget_pgEphys.yMax = len(self.Ephys.ephys_data.all_channels) * self.MW.ui.widget_pgEphys.slot_height
        else:
            self.MW.ui.pushButton_showChannels.setText('Show with deselected Channels')
            self.MW.ui.widget_pgEphys.yMax = len(self.Ephys.VisEphys.displayed_channels) * self.MW.ui.widget_pgEphys.slot_height

        self.MW.ui.widget_pgEphys.yMin = -self.MW.ui.widget_pgEphys.slot_height
        self.Ephys.VisEphys.visualize_data(self.Ephys.VisEphys.displayed_channels)


    def change_opacityBackground(self,val):
        actor = self.plotter.actors['background']
        actor.GetProperty().SetOpacity(val/100)
        self.opacityBackground = val/100

    def change_opacityRegionOfInterest(self,val):
        actor = self.plotter.actors['atlas_region']
        actor.GetProperty().SetOpacity(val/100)
        self.opacityRoI = val/100

    def change_opacityOtherRegions(self,val):
        actor = self.plotter.actors['atlas']
        actor.GetProperty().SetOpacity(val/100)
        self.opacityRegions = val/100

    def create_atlas_region_file(self,mrid):
        #new atlas with the new label
        self.filepath_atlas = os.path.join(self.session_path,"analysed",'atlas-regions.nii.gz')
        points_electrodes_path = os.path.join(os.path.join(self.session_path,"analysed"),mrid,'channel_atlas_coordinates.xlsx')

        if os.path.exists(self.filepath_atlas):
            mesh = pv.read(self.filepath_atlas)
            old_labels = np.unique(mesh.point_data['NIFTI'])
            new_labels = np.unique(pd.read_excel(points_electrodes_path,header=0).iloc[:, 1].values)
            if np.array_equal(old_labels[old_labels != 0], new_labels[new_labels != 0]):
                print(old_labels,new_labels,flush=True)
                return

        atlas_image = sITK.ReadImage(os.path.join(os.path.dirname(os.path.dirname((__file__))), "Files",'Atlas','WHS_SD_rat_atlas_v4.nii.gz'))
        volume = sITK.GetArrayFromImage(atlas_image)
        volume[~np.isin(volume,np.unique(pd.read_excel(points_electrodes_path,header=0).iloc[:, 1].values))]=0
        label_image = sITK.GetImageFromArray(volume)
        label_image.CopyInformation(atlas_image)
        save_path = os.path.join(self.session_path,'analysed','atlas-regions.nii.gz')
        sITK.WriteImage(label_image, save_path)