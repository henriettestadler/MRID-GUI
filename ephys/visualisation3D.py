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

from PySide6.QtWidgets import QTableWidgetItem,QCheckBox,QMenu,QHeaderView
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

class Visualisation3D:
    def __init__(self,session_path,MW,mrid,electrode_localisation=False,index=None,chMap=None):

        self.electrode_localisation=electrode_localisation
        self.MW = MW
        self.session_path = session_path
        self.ui = MW.ui
        self.enable_picking = False
        self.index = index
        self.norm_vec = None
        self.parallel_projection = True
        self.slice_z= 'top'
        self.slice_x= 'right'
        self.slice_y= 'front'
        self.poly_otherMrids = {}

        self.list_of_good_colors = [(1.0,1.0,1.0),(0.224,1.0,0.078),(1.0,0.078,0.576),(0.0,1.0,1.0),(1.0,0.647,0.0),(1.0,1.0,0.0),
            (0.0,0.588,1.0),(1.0,0.196,0.196),(0.749,0.0,1.0),(0.0,1.0,0.588),(1.0,0.392,1.0),(0.392,1.0,1.0),(1.0,0.784,0.0),
            (0.196,1.0,0.784),(1.0,0.314,0.0),(0.706,1.0,0.0),(0.0,0.784,1.0),(1.0,0.0,0.392),(0.588,0.196,1.0),(0.0,1.0,0.314),(1.0,0.627,0.196)
        ]

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
        else:
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
            for i, mrid in enumerate(self.MW.Ephys.coordinates):
                text = f"{mrid} (Channel Group: {i})"
                combo_items.append(text)
            self.comboBox_mrid.addItems(combo_items)

        self.btn_slicex.clicked.connect(self.slice_vol_x)
        self.btn_slicey.clicked.connect(self.slice_vol_y)
        self.btn_slicez.clicked.connect(self.slice_vol_z)

        layout.addWidget(self.plotter)

        filepath = os.path.join(self.session_path,"analysed",'atlas-regions.nii.gz')
        self.load_atlas(filepath)




    def initialize_mridTag(self,mrid,chMap=None):
        if not hasattr(self,'chMap'):
            self.chMap = chMap

        self.old_target_idx = 0 #Clear Label
        self.spinbox.setMinimum(min(self.chMap))
        self.spinbox.setMaximum(max(self.chMap))
        filepath = os.path.join(self.session_path,"analysed",'atlas-regions.nii.gz')
        self.update_electrode_points(filepath,mrid)

        if self.electrode_localisation:
            self.fill_table(channels=[],skipped_ch=[])

        index = self.comboBox_mrid.findText(mrid, Qt.MatchContains)
        if index != -1:
            self.comboBox_mrid.setCurrentIndex(index)


    def channel_changed(self,index):
        point_index = self.chMap.index(index)
        point = self.coords_list[point_index]
        self.show_coords(point)

    def show_coords(self,point):
        idx = np.where(np.all(np.isclose(self.coords_list, point, atol=0.025), axis=1))[0]

        if self.chMap[idx[0]] in self.skipped_ch:
            return

        if len(idx):
            row = self.points_data.iloc[idx[0]]
            print(row,idx,flush=True)
            self.coord_x.setValue(point[0]/self.spacing+1)
            self.coord_y.setValue(point[1]/self.spacing+1)
            self.coord_z.setValue(point[2]/self.spacing+1)
            self.spinbox.blockSignals(True)
            self.spinbox.setValue(self.chMap[idx[0]])

            self.spinbox.blockSignals(False)
            index = self.combobox.findText(row['Channel Label'])
            if index != -1:
                self.combobox.setCurrentIndex(index)
            print('SHOW COORDS',self.points_data.iloc[idx[0]].name,idx,flush=True)
            self.manually_pick_point(point,idx=idx[0] ) #self.chMap[idx[0]]) #row['Channel ID'])
        else:
            if hasattr(self.MW,'ButtonsGUI_4D'):
                for j, poly in enumerate(self.poly_list):
                    if poly == []:
                        continue
                    pts = poly.points
                    idx = np.where(np.all(np.isclose(pts, point, atol=0.025), axis=1))[0]
                    if len(idx):
                        self.MW.ButtonsGUI_4D.fill_table_and_plots(j)
                        return


    def delete_volumes(self,mrid,new_label_idx, point_idx):
        self.norm_vec = None
        #self.visualization_3D(mrid)
        ## load atlas new
        img = nib.load(os.path.join(self.session_path,"analysed",'atlas-regions.nii.gz'))
        data = img.get_fdata().astype(int)[::3, ::3, ::3]
        vol_small = pv.ImageData()
        vol_small.dimensions = np.array(data.shape) + 1
        vol_small.spacing = tuple(s * 3 for s in img.header.get_zooms()[:3])
        vol_small.origin = (0.0, 0.0, 0.0)
        vol_small.cell_data['NIFTI'] = data.flatten(order='F')
        self.unique_vals = np.unique(vol_small.active_scalars)
        self.mesh_atlas = vol_small
        ## load excel new
        self.update_electrode_points(os.path.join(self.session_path,"analysed",'atlas-regions.nii.gz'),mrid)

        if np.all(self.rgba[new_label_idx, :3] == [0, 0, 0]): #self.rgba[new_label_idx, :3] == [0 0 0]:
            self.rgba[new_label_idx, :3] = self.list_of_good_colors[self.idx_colors]
            self.rgba[new_label_idx, 3] = 1
            self.idx_colors += 1
            self.cmap = ListedColormap(self.rgba)

        #load new
        print('DELETE VOLUMES',flush=True)
        self.manually_pick_point([],idx=point_idx)

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


    def manually_pick_point(self,point,idx=None):
        print(point,idx,flush=True)
        #index should be passed -> coordinates should be somehow received
        if len(point)==0:
            self.spinbox.setValue(self.chMap[idx]) #self.points_data.iloc[idx]['Channel ID'])
            index = self.combobox.findText(self.points_data.iloc[idx]['Channel Label'])
            if index != -1:
                self.combobox.setCurrentIndex(index)
            point = self.coords_list[idx]
            self.coord_x.setValue(point[0]/self.spacing+1)
            self.coord_y.setValue(point[1]/self.spacing+1)
            self.coord_z.setValue(point[2]/self.spacing+1)
        else:
            point = np.array(point) #*self.spacing
            #idx = np.where((self.coords_list == point).all(axis=1))[0][0]
            index = self.combobox.findText(self.points_data.iloc[idx]['Channel Label'])

        target_idx = self.atlaslabelsdf['IDX'].values[index]
        if self.old_target_idx != target_idx:
            self.old_target_idx = target_idx
            if target_idx==0:
                self.plotter.remove_actor('atlas')
                self.plotter.remove_actor('atlas_region')
            else:
                volomue_thresholded = self.mesh_atlas.threshold(value=[1, 502], scalars='NIFTI').threshold([target_idx - 0.5, target_idx + 0.5], invert=True)
                nifti_vals = np.round(volomue_thresholded.cell_data['NIFTI']).astype(int)
                colors = np.array([self.cmap.colors[int(v)] for v in nifti_vals])
                volomue_thresholded.cell_data['colors']= (colors[:, :3]*255).astype(np.uint8)
                surface = volomue_thresholded.extract_surface(algorithm='dataset_surface')
                smoothed_vol = surface.smooth_taubin(n_iter=50, pass_band=0.1)

                self.plotter.add_mesh(
                    smoothed_vol, #volomue_thresholded,
                    scalars='colors',
                    rgb=True,
                    show_scalar_bar=False,
                    name='atlas',
                    style='surface',
                    pickable=False,
                    #point_size=0.02,
                    opacity=0.1,
                    reset_camera=False,
                    render=False,
                    culling=True,
                    show_edges=True,
                )

                ##REGION MESH
                region_mesh = self.mesh_atlas.threshold([target_idx - 0.5, target_idx + 0.5])
                surface = region_mesh.extract_surface(algorithm='dataset_surface')
                #smoothed = surface.smooth(n_iter=50, relaxation_factor=0.1)
                smoothed_region = surface.smooth_taubin(n_iter=50, pass_band=0.1)
                color = self.cmap.colors[target_idx]
                self.plotter.add_mesh(
                    smoothed_region, #region_mesh,
                    color=color,
                    opacity=0.5,
                    show_scalar_bar=False,
                    name='atlas_region',
                    style='surface',
                    pickable=False,
                    reset_camera=False,
                    render=False,
                    culling=True,
                    show_edges=True,
                )

                self.atlas = smoothed_vol #volomue_thresholded
                self.atlas_region = smoothed_region

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

    def load_atlas(self,filepath):
        from concurrent.futures import ThreadPoolExecutor

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
            mesh = pv.read(background_path)
            mesh_small = mesh.extract_subset(
                voi=(0, mesh.dimensions[0]-1,
                     0, mesh.dimensions[1]-1,
                     0, mesh.dimensions[2]-1),
                rate=(6,6,6)
            )
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
            background_mesh_small = future_background.result()
            self.atlaslabelsdf = future_labels.result()
            self.background_mesh_small = background_mesh_small

        if 'background' not in self.plotter.actors:
            self.add_background(background_mesh_small)  # pass mesh directly
        max_idx = int(self.atlaslabelsdf['IDX'].max())
        self.rgba = np.zeros((max_idx + 1, 4))
        self.idx_colors = 0
        for _, row in self.atlaslabelsdf.iterrows():
            if row['IDX'] in self.unique_vals:
                self.rgba[int(row['IDX']), :3] = self.list_of_good_colors[self.idx_colors] #[row['R']/255, row['G']/255, row['B']/255, row['A']/255]
                self.rgba[int(row['IDX']), 3] = 1
                self.idx_colors += 1
        self.cmap = ListedColormap(self.rgba)

        self.combobox.addItems(self.atlaslabelsdf['LABEL'].values)
        self.opacity = np.full(len(self.atlaslabelsdf), 0.5)
        self.opacity[0]=0

        self.plotter.add_axes()

        self.mesh_atlas = vol_small




    def update_electrode_points(self,filepath,mrid):
        if "electrode_points" not in self.plotter.actors:
            img = sITK.ReadImage(filepath)
            self.spacing = img.GetSpacing()[0]

        points_electrodes_path = os.path.join(os.path.join(self.session_path,"analysed"),mrid,'channel_atlas_coordinates.xlsx')
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
            self.plotter.enable_point_picking(callback=self.show_coords,show_message=False,left_clicking=True,color='red',picker='point',show_point=False)
            self.enable_picking = True

        if self.electrode_localisation:
            self.add_other_mrids()



    def add_background(self,mesh_downsampled):
        background = mesh_downsampled.threshold(value=0.5)
        background = background.extract_surface(algorithm='dataset_surface')
        opacity = np.full(len(self.atlaslabelsdf), 0.15)
        opacity[0]=0
        #surface = background.extract_surface(algorithm='dataset_surface')
        smoothed = background.smooth_taubin(n_iter=50, pass_band=0.1)

        self.plotter.add_mesh(
            smoothed, #background,
            color='white',
            opacity=0.2,
            style='surface',  # or 'wireframe'
            line_width=0.5,
            pickable=False,
            name='background',
            reset_camera=False,
            render=False,
            culling=True,
        )

        self.background = smoothed# background

    def add_other_mrids(self):
        ## show the other tags -> clickable switch to them (Label = Name)
        points = []
        lines_connectivity = []
        self.poly_list = []

        for i in range(len(self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl)):
            if i == self.index:
                self.poly_list.append([])
                self.poly_otherMrids[i] = None
                continue

            atlasCoordinates = self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl[i]

            linepoints = np.array(atlasCoordinates)*self.spacing

            for j in range(len(linepoints) - 1):
                p1 = linepoints[j]
                p2 = linepoints[j + 1]
                t = np.linspace(0, 1, 102)
                idx = len(points)
                interpolated = p1 + t[:, None] * (p2 - p1)
                n = len(interpolated)
                points.extend(interpolated)
                #lines_connectivity.extend([2, idx, idx + 1])  # 2 = number of points in cell
                lines_connectivity.extend([n] + list(range(idx, idx + n)))

            poly = pv.PolyData()
            poly.points = np.array(points)
            poly.lines = np.array(lines_connectivity)
            self.poly_list.append(poly)
            self.plotter.add_mesh(poly, color='white', line_width=8,name=self.MW.ButtonsGUI_4D.totalmrid[i],reset_camera=False,render=False,pickable=True)
            self.plotter.add_point_labels([poly.center],[self.MW.ButtonsGUI_4D.totalmrid[i]],font_size=10,text_color='white',name=self.MW.ButtonsGUI_4D.totalmrid[i] + '_label',reset_camera=False,render=False)
            self.poly_otherMrids[i] = poly
            print('ADD OTHER PKL',flush=True)
        self.manually_pick_point(point=[],idx=0)



    def focus_on_point(self, point,index,distance=4):
        """point = [x, y, z]"""
        #already focuing on this point
        focal_point = self.plotter.camera.focal_point
        if np.array_equal(focal_point, point):#if focal_point==point:
            print('BEFORE FOCAL POINT SAME AS POINT, HENCE RETURN',flush=True)
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
            self.MW.Ephys.VisEphys.highlight_channel(index)
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
        x0 = (self.coord_x.value()-1)*self.spacing
        y0 = (self.coord_y.value()-1)*self.spacing
        z0 = (self.coord_z.value()-1)*self.spacing
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clipped_poly_otherMrids = {}

        if self.slice_x== 'right':
            clipped_background = self.background.clip(normal='-x', origin=(x0, y0, z0))
            clipped_atlas = self.atlas.clip(normal='-x', origin=(x0, y0, z0))
            clipped_region = self.atlas_region.clip(normal='-x', origin=(x0, y0, z0))
            clipped_poly = self.points_poly.clip(normal='-x', origin=(x0, y0, z0))
            mask = self.points_poly.points[:, 0] >= x0
            clipped_labels = np.array(self.points_poly['Labels'])[mask]
            clipped_poly['Labels'] = clipped_labels
            self.btn_slicex.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_sagittal_left.png")))
            self.slice_x= 'left'
            vector = [-1,0,0]
            roll_angle = 90
            if hasattr(self.MW,'ButtonsGUI_4D'):
                for i in range(len(self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl)):
                    if i == self.index:
                        clipped_poly_otherMrids[i] = None
                        continue
                    clipped_poly_otherMrids[i] = self.poly_otherMrids[i].clip(normal='-x', origin=(x0, y0, z0))
        else:
            clipped_background = self.background.clip(normal='x', origin=(x0, y0, z0))
            clipped_atlas = self.atlas.clip(normal='x', origin=(x0, y0, z0))
            clipped_region = self.atlas_region.clip(normal='x', origin=(x0, y0, z0))
            clipped_poly = self.points_poly.clip(normal='x', origin=(x0, y0, z0))
            mask = self.points_poly.points[:,0] <= x0
            clipped_labels = np.array(self.points_poly['Labels'])[mask]
            clipped_poly['Labels'] = clipped_labels
            self.slice_x= 'right'
            self.btn_slicex.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_sagittal_right.png")))
            vector = [1,0,0]
            roll_angle = -90
            if hasattr(self.MW,'ButtonsGUI_4D'):
                for i in range(len(self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl)):
                    if i == self.index:
                        clipped_poly_otherMrids[i] = None
                        continue
                    clipped_poly_otherMrids[i] = self.poly_otherMrids[i].clip(normal='x', origin=(x0, y0, z0))

        self.render_clipped(clipped_background, clipped_atlas,clipped_region,clipped_poly,clipped_poly_otherMrids)

        # set camera so that slice is in 2D view
        focal_point = self.plotter.camera.focal_point
        # Preserve viewing direction
        if self.parallel_projection==True:
            self.plotter.disable_parallel_projection()
        distance = 40
        new_pos = np.array(focal_point) + np.array(vector) * distance  # distance controls how close
        self.plotter.set_position(new_pos)

        self.plotter.camera.roll = roll_angle

        if self.parallel_projection==True:
            self.plotter.enable_parallel_projection()



    def slice_vol_y(self,val):
        x0 = (self.coord_x.value()-1)*self.spacing
        y0 = (self.coord_y.value()-1)*self.spacing
        z0 = (self.coord_z.value()-1)*self.spacing
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clipped_poly_otherMrids = {}

        if self.slice_y== 'front':
            clipped_background = self.background.clip(normal='-y', origin=(x0, y0, z0))
            clipped_atlas = self.atlas.clip(normal='-y', origin=(x0, y0, z0))
            #clipped_atlas = clipped_atlas.fill_holes(hole_size=1000)
            clipped_region = self.atlas_region.clip(normal='-y', origin=(x0, y0, z0))
            clipped_region = clipped_region.fill_holes(hole_size=1000)
            clipped_poly = self.points_poly.clip(normal='-y', origin=(x0, y0, z0))
            mask = self.points_poly.points[:, 1] >= y0
            clipped_labels = np.array(self.points_poly['Labels'])[mask]
            clipped_poly['Labels'] = clipped_labels
            self.btn_slicey.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_coronal_back.png")))
            self.slice_y= 'back'
            vector = [0,-1,0]
            roll_angle = 0
            if hasattr(self.MW,'ButtonsGUI_4D'):
                for i in range(len(self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl)):
                    if i == self.index:
                        clipped_poly_otherMrids[i] = None
                        continue
                    clipped_poly_otherMrids[i] = self.poly_otherMrids[i].clip(normal='-y', origin=(x0, y0, z0))
        else:
            clipped_background = self.background.clip(normal='y', origin=(x0, y0, z0))
            clipped_atlas = self.atlas.clip(normal='y', origin=(x0, y0, z0))
            clipped_region = self.atlas_region.clip(normal='y', origin=(x0, y0, z0))
            clipped_poly = self.points_poly.clip(normal='y', origin=(x0, y0, z0))
            mask = self.points_poly.points[:, 1] <= y0
            clipped_labels = np.array(self.points_poly['Labels'])[mask]
            clipped_poly['Labels'] = clipped_labels
            self.btn_slicey.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_coronal_front.png")))
            self.slice_y= 'front'
            vector = [0,1,0]
            roll_angle = 180
            if hasattr(self.MW,'ButtonsGUI_4D'):
                for i in range(len(self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl)):
                    if i == self.index:
                        clipped_poly_otherMrids[i] = None
                        continue
                    clipped_poly_otherMrids[i] = self.poly_otherMrids[i].clip(normal='y', origin=(x0, y0, z0))

        self.render_clipped(clipped_background, clipped_atlas,clipped_region,clipped_poly,clipped_poly_otherMrids)

        # set camera so that slice is in 2D view
        focal_point = self.plotter.camera.focal_point
        # Preserve viewing direction
        if self.parallel_projection==True:
            self.plotter.disable_parallel_projection()
        distance = 40
        new_pos = np.array(focal_point) + np.array(vector) * distance  # distance controls how close
        self.plotter.set_position(new_pos)
        self.plotter.camera.roll = roll_angle
        if self.parallel_projection==True:
            self.plotter.enable_parallel_projection()



    def slice_vol_z(self,val):
        x0 = (self.coord_x.value()-1)*self.spacing
        y0 = (self.coord_y.value()-1)*self.spacing
        z0 = (self.coord_z.value()-1)*self.spacing
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clipped_poly_otherMrids = {}

        if self.slice_z== 'top':
            clipped_background = self.background.clip(normal='-z', origin=(x0, y0, z0))
            clipped_atlas = self.atlas.clip(normal='-z', origin=(x0, y0, z0))
            clipped_region = self.atlas_region.clip(normal='-z', origin=(x0, y0, z0))
            clipped_poly = self.points_poly.clip(normal='-z', origin=(x0, y0, z0))
            mask = self.points_poly.points[:, 2] >= z0
            clipped_labels = np.array(self.points_poly['Labels'])[mask]
            clipped_poly['Labels'] = clipped_labels
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_axial_bottom.png")))
            self.slice_z= 'bottom'
            vector = [0,0,-1]
            roll_angle = 0
            if hasattr(self.MW,'ButtonsGUI_4D'):
                for i in range(len(self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl)):
                    if i == self.index:
                        clipped_poly_otherMrids[i] = None
                        continue
                    clipped_poly_otherMrids[i] = self.poly_otherMrids[i].clip(normal='-z', origin=(x0, y0, z0))
        else:
            clipped_background = self.background.clip(normal='z', origin=(x0, y0, z0))
            clipped_atlas = self.atlas.clip(normal='z', origin=(x0, y0, z0))
            clipped_region = self.atlas_region.clip(normal='z', origin=(x0, y0, z0))
            clipped_poly = self.points_poly.clip(normal='z', origin=(x0, y0, z0))
            mask = self.points_poly.points[:, 2] <= z0
            clipped_labels = np.array(self.points_poly['Labels'])[mask]
            clipped_poly['Labels'] = clipped_labels
            self.btn_slicez.setIcon(QIcon(os.path.join(base_dir, "Icons", "ephys","slicing_axial_top.png")))
            self.slice_z= 'top'
            vector = [0,0,1]
            roll_angle = 180
            if hasattr(self.MW,'ButtonsGUI_4D'):
                for i in range(len(self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl)):
                    if i == self.index:
                        clipped_poly_otherMrids[i] = None
                        continue
                    clipped_poly_otherMrids[i] = self.poly_otherMrids[i].clip(normal='z', origin=(x0, y0, z0))

        self.render_clipped(clipped_background, clipped_atlas,clipped_region,clipped_poly,clipped_poly_otherMrids)

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

    def no_slicing(self,val):
        self.render_clipped(self.background, self.atlas,self.atlas_region,self.points_poly,self.poly_otherMrids)


    def render_clipped(self,clipped_background, clipped_atlas,clipped_region,clipped_poly,clipped_poly_otherMrids):
        clipped_background = clipped_background.fill_holes(hole_size=1000)
        self.plotter.add_mesh(
            clipped_background,
            color='white',
            opacity=0.2,
            style='surface',  # or 'wireframe'
            line_width=0.5,
            pickable=False,
            name='background',
            reset_camera=False,
            render=False,
        )

        self.plotter.add_mesh(
            clipped_atlas,
            scalars='colors',
            rgb=True,
            show_scalar_bar=False,
            name='atlas',
            style='surface',
            pickable=False,
            opacity=0.1,
            reset_camera=False,
            render=False,
        )
        color = self.cmap.colors[self.old_target_idx]
        self.plotter.add_mesh(
            clipped_region,
            color=color,
            opacity=0.5,
            show_scalar_bar=False,
            name='atlas_region',
            style='surface',
            pickable=False,
            reset_camera=False,
        )

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


        for i,poly_otherMrid in enumerate(clipped_poly_otherMrids):
            self.plotter.add_mesh(
                poly_otherMrid, color='white', line_width=8,
                name=self.MW.ButtonsGUI_4D.totalmrid[i],
                reset_camera=False,render=False,pickable=True
            )


    def fill_table(self,channels,skipped_ch):
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
        self.table_excel.setColumnWidth(0, 20)

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
                if df['ID'][row_idx] in skipped_ch:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                    color = QColor(0.5*255, 0.5*255, 0.5*255) #GREY
                    item.setForeground(color)
                    checkbox_item.setCheckState(Qt.Unchecked)
                    checkbox_item.setFlags(checkbox_item.flags() & ~Qt.ItemIsEnabled)
            #checkbox_item.stateChanged.connect(lambda state, r=row_idx: self.on_channel_toggled(r, state))

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
        if checked:
            #add channel to plot, but keeping the indices the same
            idx = next((self.MW.Ephys.VisEphys.displayed_channels.index(v) for v in self.MW.Ephys.VisEphys.all_channels[:self.MW.Ephys.VisEphys.all_channels.index(channel_number)][::-1] if v in self.MW.Ephys.VisEphys.displayed_channels), None)
            if idx is None:
                self.MW.Ephys.VisEphys.displayed_channels.insert(0, channel_number)
            else:
                self.MW.Ephys.VisEphys.displayed_channels.insert(idx + 1, channel_number)
            self.MW.Ephys.VisEphys.visualize_data(self.MW.Ephys.VisEphys.displayed_channels)
        else:
            #remove channel from plot
            if channel_number in self.MW.Ephys.VisEphys.displayed_channels:
                self.MW.Ephys.VisEphys.displayed_channels.remove(channel_number)
                self.MW.Ephys.VisEphys.visualize_data(self.MW.Ephys.VisEphys.displayed_channels)

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
            #self.skipped_ch()
            idx = next((self.skipped_ch.index(v) for v in self.MW.Ephys.VisEphys.all_channels[:self.MW.Ephys.VisEphys.all_channels.index(channel_number)][::-1] if v in self.skipped_ch), None)
            if idx is None:
                self.skipped_ch.insert(0, channel_number)
            else:
                self.skipped_ch.insert(idx + 1, channel_number)

            self.MW.Ephys.change_xml_file(channel_number,1)
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
            self.skipped_ch.remove(channel_number)
            self.MW.Ephys.change_xml_file(channel_number,0)




    def on_table_click(self,row,column):
        item = self.table_excel.item(row, column)
        if item and not (item.flags() & Qt.ItemIsEnabled):
            return

        self.manually_pick_point(point=[],idx=row)
        if self.electrode_localisation:
            self.table_excel.selectRow(row)
        else:
            self.MW.Ephys.VisEphys.highlight_channel(row)


