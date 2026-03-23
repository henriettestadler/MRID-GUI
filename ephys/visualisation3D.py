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
import pickle
from sklearn.decomposition import PCA
import matplotlib.colors as mcolors
from vtk import vtkPiecewiseFunction
from PySide6 import QtWidgets
import nibabel as nib


class Visualisation3D:
    def __init__(self,session_path,MW,mrid,electrode_localisation=False,index=None):
        self.electrode_localisation=electrode_localisation
        self.MW = MW
        self.session_path = session_path
        self.ui = MW.ui
        self.enable_picking = False
        self.index = index
        self.norm_vec = None
        self.parallel_projection = True


        self.list_of_good_colors = [(0.224,1.0,0.078),(1.0,0.078,0.576),(0.0,1.0,1.0),(1.0,0.647,0.0),(1.0,1.0,0.0),
            (0.0,0.588,1.0),(1.0,0.196,0.196),(0.749,0.0,1.0),(0.0,1.0,0.588),(1.0,0.392,1.0),(0.392,1.0,1.0),(1.0,0.784,0.0),
            (0.196,1.0,0.784),(1.0,0.314,0.0),(0.706,1.0,0.0),(0.0,0.784,1.0),(1.0,0.0,0.392),(0.588,0.196,1.0),(0.0,1.0,0.314),(1.0,0.627,0.196)
        ]

        ## test
        #self.ui.vtkWidget_ephys.layout()
        #push_btn = QtWidgets.QPushButton("Browse")
        #self.ui.vtkWidget_ephys.layout().addWidget(push_btn)

        #set up layout
        pv.global_theme.background = 'black'
        if electrode_localisation:
            layout = QVBoxLayout(self.ui.vtkWidget_data03) #data_index?
            layout.setContentsMargins(0, 0, 0, 0)
            self.plotter = QtInteractor(self.ui.vtkWidget_data03)

            self.ui.fit_to_zoom_ephys.clicked.connect(self.plotter.reset_camera)
            self.ui.change_perspective_ephys.clicked.connect(self.change_perspective)

            self.ui.spinBox_channelID.setMinimum(0)
            self.combobox = self.ui.comboBox_anatRegion_4d
            self.spinbox = self.ui.spinBox_channelID_4d
            self.coord_x = self.ui.spinBox_x_4d
            self.coord_y = self.ui.spinBox_y_4d
            self.coord_z = self.ui.spinBox_z_4d
            self.comboBox_mrid = self.ui.comboBox_mridTag
            self.comboBox_mrid.setEnabled(False)
        else:
            layout = QVBoxLayout(self.ui.vtkWidget_ephys)
            layout.setContentsMargins(0, 0, 0, 0)
            self.plotter = QtInteractor(self.ui.vtkWidget_ephys)

            self.ui.fit_to_zoom_ephys.clicked.connect(self.plotter.reset_camera)
            self.ui.change_perspective_ephys.clicked.connect(self.change_perspective)
            self.ui.spinBox_channelID.valueChanged.connect(self.channel_changed)
            self.ui.spinBox_channelID.setMinimum(0)
            self.combobox = self.ui.comboBox_anatRegion
            self.spinbox = self.ui.spinBox_channelID
            self.coord_x = self.ui.spinBox_x_ephys
            self.coord_y = self.ui.spinBox_y_ephys
            self.coord_z = self.ui.spinBox_z_ephys
            self.comboBox_mrid = self.ui.comboBox_mridTag

            self.ui.pushButton_slicex.clicked.connect(self.slice_vol_x)
            self.ui.pushButton_slicey.clicked.connect(self.slice_vol_y)
            self.ui.pushButton_slicez.clicked.connect(self.slice_vol_z)
            self.ui.pushButton_reverse.clicked.connect(self.slice_vol_reverse)


        layout.addWidget(self.plotter)


        self.spinbox.valueChanged.connect(self.channel_changed)

        self.visualization_3D(mrid)

        mrid_tags = [f.name for f in os.scandir(os.path.join(self.session_path,"analysed")) if f.is_dir()]
        self.comboBox_mrid.addItems(mrid_tags)
        index = self.comboBox_mrid.findText(mrid)
        if index != -1:
            self.comboBox_mrid.setCurrentIndex(index)



    def visualization_3D(self,mrid):
        filepath = os.path.join(self.session_path,"analysed",'atlas-regions.nii.gz')

        if "atlas" not in self.plotter.actors:
            self.load_atlas(filepath)

        self.update_electrode_points(filepath,mrid)


    def channel_changed(self,index):
        point = self.coords_list[index]
        self.show_coords(point)

    def show_coords(self,point):
        #message box
        print(point,point[0]/self.spacing+1,point[1]/self.spacing+1,point[2]/self.spacing+1,flush=True)
        idx = np.where(np.all(np.isclose(self.coords_list, point, atol=0.025), axis=1))[0]
        if len(idx):
            row = self.points_data.iloc[idx[0]]
            self.coord_x.setValue(point[0]/self.spacing+1)
            self.coord_y.setValue(point[1]/self.spacing+1)
            self.coord_z.setValue(point[2]/self.spacing+1)
            self.spinbox.blockSignals(True)
            self.spinbox.setValue(row['Channel ID'])
            self.spinbox.blockSignals(False)
            index = self.combobox.findText(row['Channel Label'])
            if index != -1:
                self.combobox.setCurrentIndex(index)
            print('am i here before',flush=True)
            self.manually_pick_point(point)


    def delete_volumes(self,mrid):
        self.norm_vec = None
        self.plotter.remove_actor("atlas")
        #self.plotter.remove_actor("background")
        self.visualization_3D(mrid)

    def change_perspective(self):
        if self.parallel_projection==True:
            self.plotter.disable_parallel_projection()
            self.ui.change_perspective_ephys.setText('Change Projection to Parallel')
            self.parallel_projection=False
        else:
            self.plotter.enable_parallel_projection()
            self.ui.change_perspective_ephys.setText('Change Projection to Perspective')
            self.parallel_projection=True
        self.plotter.render()

    def manually_pick_point(self,point,idx=None):
        #index should be passed -> coordinates should be somehow received
        if len(point)==0:
            self.spinbox.setValue(self.points_data.iloc[idx]['Channel ID'])
            index = self.combobox.findText(self.points_data.iloc[idx]['Channel Label'])
            if index != -1:
                self.combobox.setCurrentIndex(index)
            point = self.coords_list[idx]
            self.coord_x.setValue(point[0]/self.spacing+1)
            self.coord_y.setValue(point[1]/self.spacing+1)
            self.coord_z.setValue(point[2]/self.spacing+1)
        else:
            point = np.array(point) #*self.spacing
            idx = np.where((self.coords_list == point).all(axis=1))[0][0]
            index = self.combobox.findText(self.points_data.iloc[idx]['Channel Label'])

        target_idx = self.atlaslabelsdf['IDX'].values[index]
        volomue_thresholded = self.mesh_atlas.threshold(value=[1, 502], scalars='NIFTI').threshold([target_idx - 0.5, target_idx + 0.5], invert=True)
        nifti_vals = np.round(volomue_thresholded.cell_data['NIFTI']).astype(int)
        colors = np.array([self.cmap.colors[int(v)] for v in nifti_vals])
        volomue_thresholded.cell_data['colors']= (colors[:, :3]*255).astype(np.uint8)

        self.plotter.add_mesh(
            volomue_thresholded,
            scalars='colors',
            rgb=True,
            show_scalar_bar=False,
            name='atlas',
            style='points',
            pickable=False,
            point_size=0.02,
        )

        ##REGION MESH
        region_mesh = self.mesh_atlas.threshold([target_idx - 0.5, target_idx + 0.5])
        region_mesh = region_mesh.point_data_to_cell_data()
        cell_nifti_vals = np.round(region_mesh.cell_data['NIFTI']).astype(int)
        region_mesh.cell_data['region'] = cell_nifti_vals.astype(float)
        region_mesh.set_active_scalars('region', preference='cell')
        color = self.cmap.colors[target_idx]
        self.plotter.add_mesh(
            region_mesh,
            color=color,
            opacity=0.5,
            show_scalar_bar=False,
            name='atlas_region',
            style='surface',
            pickable=False,
        )

        if 'picked_point' in self.plotter.actors:
            self.plotter.remove_actor("picked_point", reset_camera=False,render=False)

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
            #mesh = pv.read(filepath)

            #vol_small = mesh.extract_subset(
            #    voi=(0, mesh.dimensions[0]-1,
            #         0, mesh.dimensions[1]-1,
            #         0, mesh.dimensions[2]-1),
            #    rate=(3,3,3),boundary=True ,
            #)
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

        if self.atlaslabelsdf is not None:
            if 'background' not in self.plotter.actors:
                self.add_background(background_mesh_small)  # pass mesh directly
            #rgba = self.atlaslabelsdf[['R', 'G', 'B','A']].values / 255
            max_idx = int(self.atlaslabelsdf['IDX'].max())
            rgba = np.zeros((max_idx + 1, 4))
            idx_colors = 0
            for _, row in self.atlaslabelsdf.iterrows():
                if row['IDX'] in self.unique_vals:
                    rgba[int(row['IDX']), :3] = self.list_of_good_colors[idx_colors] #[row['R']/255, row['G']/255, row['B']/255, row['A']/255]
                    rgba[int(row['IDX']), 3] = 1
                    idx_colors += 1
            #rgba[0, :] = [0, 0, 0, 0]
            self.cmap = ListedColormap(rgba)
            self.combobox.addItems(self.atlaslabelsdf['LABEL'].values)
            self.opacity = np.full(len(self.atlaslabelsdf), 0.5)
            self.opacity[0]=0
            print(self.atlaslabelsdf[self.atlaslabelsdf['IDX'] == 95][['IDX','R','G','B']])
            print(self.cmap.colors[95])
            print(self.cmap.colors[62])
        else:
            self.cmap = "viridis"
            #self.opacity=[0, 0.1, 0.1, 0.1, 0.1, 0.1]

        #self.plotter.add_volume(vol_small, cmap=self.cmap,opacity=self.opacity,show_scalar_bar=False, pickable=False, name="atlas_blablabla",render=False)
        #self.plotter.add_floor('-z')
        self.plotter.add_axes()

        self.mesh_atlas = vol_small




    def update_electrode_points(self,filepath,mrid):
        if "electrode_points" in self.plotter.actors:
            self.plotter.remove_actor("electrode_points")
            self.plotter.remove_actor('electrode_labels')
        else:
            # get self.spacing the first time the function is called
            img = sITK.ReadImage(filepath)
            self.spacing = img.GetSpacing()[0]

        points_electrodes_path = os.path.join(os.path.join(self.session_path,"analysed"),mrid,'channel_atlas_coordinates.xlsx')
        self.points_data = pd.read_excel(points_electrodes_path,header=0)
        self.coords_list = self.points_data.iloc[:, -3:].values*self.spacing
        self.spinbox.setMaximum(len(self.coords_list)-1)

        point_colors = []
        rgb = self.atlaslabelsdf[['R', 'G', 'B']].values / 255
        for label in self.points_data.iloc[:, 1].values:
            idx = np.where(self.atlaslabelsdf['IDX'].values ==label)  # fallback: gray
            base_color = rgb[idx]
            r, g, b = mcolors.to_rgb(base_color)
            comp_color = (1 - r, 1 - g, 1 - b) #complementary_color(base_color)
            point_colors.append(comp_color)

        # Add as simple point cloud
        chMap = np.arange(len(self.coords_list))

        poly = pv.PolyData(np.array(self.coords_list))
        poly['Labels'] = chMap
        poly.point_data['colors'] = point_colors

        self.plotter.add_mesh(
            poly, scalars='colors',
            rgb=True,
            point_size=10,
            name="electrode_points",
            render_points_as_spheres=True,
            render=False,show_scalar_bar=False, reset_camera=False
        )

        self.plotter.add_point_labels(poly, 'Labels', point_size=20, font_size=12,name='electrode_labels')

        if self.enable_picking==False:
            self.plotter.enable_point_picking(callback=self.show_coords,show_message=False,left_clicking=True,color='red',picker='point',show_point=False)
            self.enable_picking = True

        if self.electrode_localisation:
            self.add_pklfile_mrid(mrid)




    def add_background(self,mesh_downsampled):
        background = mesh_downsampled.threshold(value=0.5)
        background = background.extract_surface(algorithm='dataset_surface')
        opacity = np.full(len(self.atlaslabelsdf), 0.15)
        opacity[0]=0
        #for i in unique_vals:
        #    idx = self.atlaslabelsdf.index[self.atlaslabelsdf['IDX'] == i].tolist()
        #    opacity[idx] = 0

        self.plotter.add_mesh(
            background,
            color='white',
            opacity=0.2,
            style='wireframe',  # or 'surface'
            line_width=0.5,
            pickable=False,
            name='background',
            render=False,
        )

        self.background = background

    def add_pklfile_mrid(self,mrid):
        if 'pklfile' in self.plotter.actors:
            self.plotter.remove_actor("pklfile", reset_camera=False)

        atlasCoordinates = self.MW.ButtonsGUI_4D.totalatlasCoordinates_pkl[self.index]

        linepoints = np.array(atlasCoordinates)*self.spacing
        #lines = []
        #for idx in range(len(linepoints)-1):
        #    p1 = linepoints[idx]
        #    p2 = linepoints[idx+1]
        #    lines.append(pv.Line(p1,p2))

        #for i, line in enumerate(lines):
        #    color = [0, 0, 1] if i % 2 == 0 else [1, 0, 0]
        #    line.cell_data['colors'] = np.array([color])

        points = []
        lines_connectivity = []
        colors = []

        for i in range(len(linepoints) - 1):
            p1 = linepoints[i]
            p2 = linepoints[i + 1]
            idx = len(points)
            points.extend([p1, p2])
            lines_connectivity.extend([2, idx, idx + 1])  # 2 = number of points in cell
            colors.append([0, 0, 255] if i % 2 == 0 else [255, 0, 0])

        poly = pv.PolyData()
        poly.points = np.array(points)
        poly.lines = np.array(lines_connectivity)
        poly.cell_data['colors'] = np.array(colors, dtype=np.uint8)
        self.plotter.add_mesh(poly, scalars='colors', rgb=True, line_width=5,name='pklfile')

        self.manually_pick_point(point=[],idx=0)



    def focus_on_point(self, point,index,distance=4):
        """point = [x, y, z]"""
        # Preserve viewing direction
        if self.parallel_projection==True:
            self.plotter.disable_parallel_projection()
        #self.plotter.renderer.GetActiveCamera().SetParallelProjection(False) #.parallel_projection = False

        if self.norm_vec is None:
            self.norm_vec = self.find_best_fit_plane()
        new_pos = np.array(point) + self.norm_vec * distance  # distance controls how close

        self.plotter.camera_position.focal_point = np.array(point)
        self.plotter.set_position(new_pos)
        self.plotter.set_focus(point)

        self.plotter.camera.roll = -90 #aligns with xy-axis at the bottom of render

        if self.parallel_projection==True:
            self.plotter.enable_parallel_projection()
            #self.plotter.camera.parallel_projection = True

        print('highlight channel is being skiped',flush=True)
        print('highlight channel is being skiped',flush=True)
        print('highlight channel is being skiped',flush=True)
        print('highlight channel is being skiped',flush=True)
        print('highlight channel is being skiped',flush=True)

        #if not self.electrode_localisation:
        #    self.MW.Ephys.VisEphys.highlight_channel(index)


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


    def slice_vol_x(self,val,reverse=False):
        x0 = (self.coord_x.value()-1)*self.spacing
        y0 = (self.coord_y.value()-1)*self.spacing
        z0 = (self.coord_z.value()-1)*self.spacing

        if reverse:
            clipped = self.background.clip(normal='-x', origin=(x0, y0, z0))
        else:
            clipped = self.background.clip(normal='x', origin=(x0, y0, z0))
        self.plotter.add_mesh(
            clipped,
            color='white',
            opacity=0.2,
            style='wireframe',  # or 'surface'
            line_width=0.5,
            pickable=False,
            name='background',
            render=False,
        )

        #if reverse:
        #    clipped = self.atlas.clip(normal='-x', origin=(x0, y0, z0))
        #else:
        #    clipped = self.atlas.clip(normal='x', origin=(x0, y0, z0))
        #self.plotter.add_mesh(
        #    clipped,
        #    #color='blue',
        #    opacity=0.2,
        #    #style='wireframe',  # or 'surface'
        #    line_width=0.5,
        #    pickable=False,
        #    name='atlas',
        #    render=False,
        #)

        #self.plotter.add_volume_clip_plane(self.atlas_volume,normal='-x', origin=(x0, y0, z0))
        #self.plotter.plane_widgets[-1].Off()
        #self.plotter.add_volume_clip_plane(self.atlas_region,normal='-x', origin=(x0, y0, z0))
        #self.plotter.plane_widgets[-1].Off()

        self.slice_x= True
        self.slice_y = False
        self.slice_z= False


    def slice_vol_y(self,val,reverse=False):
        x0 = (self.coord_x.value()-1)*self.spacing
        y0 = (self.coord_y.value()-1)*self.spacing
        z0 = (self.coord_z.value()-1)*self.spacing

        if reverse:
            clipped = self.background.clip(normal='-y', origin=(x0, y0, z0))
        else:
            clipped = self.background.clip(normal='y', origin=(x0, y0, z0))
        self.plotter.add_mesh(
            clipped,
            color='white',
            opacity=0.2,
            style='wireframe',  # or 'surface'
            line_width=0.5,
            pickable=False,
            name='background',
            render=False,
        )

        #if reverse:
        #    clipped = self.atlas.clip(normal='-y', origin=(x0, y0, z0))
        #else:
        #    clipped = self.atlas.clip(normal='y', origin=(x0, y0, z0))
        #self.plotter.add_mesh(
        #    clipped,
        #    #color='blue',
        #    opacity=0.2,
        #    #style='wireframe',  # or 'surface'
        #    line_width=0.5,
        #    pickable=False,
        #    name='atlas',
        #    render=False,
        #)

        #self.plotter.add_volume_clip_plane(self.atlas_volume,normal='-y', origin=(x0, y0, z0))
        #self.plotter.plane_widgets[-1].Off()
        #self.plotter.add_volume_clip_plane(self.atlas_region,normal='-y', origin=(x0, y0, z0))
        #self.plotter.plane_widgets[-1].Off()

        self.slice_x= False
        self.slice_y = True
        self.slice_z= False


    def slice_vol_z(self,val,reverse=False):
        x0 = (self.coord_x.value()-1)*self.spacing
        y0 = (self.coord_y.value()-1)*self.spacing
        z0 = (self.coord_z.value()-1)*self.spacing

        if reverse:
            clipped = self.background.clip(normal='-z', origin=(x0, y0, z0))
        else:
            clipped = self.background.clip(normal='z', origin=(x0, y0, z0))
        self.plotter.add_mesh(
            clipped,
            color='white',
            opacity=0.2,
            style='wireframe',  # or 'surface'
            line_width=0.5,
            pickable=False,
            name='background',
            render=False,
        )

        #if reverse:
        #    clipped = self.atlas.clip(normal='-z', origin=(x0, y0, z0))
        #else:
        #    clipped = self.atlas.clip(normal='z', origin=(x0, y0, z0))
#
        #self.plotter.add_mesh(
        #    clipped,
        #    #color='blue',
        #    #opacity=0.2,
        #    #style='wireframe',  # or 'surface'
        #    #line_width=0.5,
        #    #pickable=False,
        #    name='atlas',
        #    #render=False,
        #)
        self.slice_x= False
        self.slice_y = False
        self.slice_z= True
        #self.plotter.add_volume_clip_plane(self.atlas_volume,normal='-z', origin=(x0, y0, z0))
        #self.plotter.plane_widgets[-1].Off()
        #self.plotter.add_volume_clip_plane(self.atlas_region,normal='-z', origin=(x0, y0, z0))
        #self.plotter.plane_widgets[-1].Off()


    def slice_vol_reverse(self,val):
        if self.slice_x:
            self.slice_vol_x(val=None,reverse=True)
        elif self.slice_y:
            self.slice_vol_y(val=None,reverse=True)
        elif self.slice_z:
            self.slice_vol_z(val=None,reverse=True)
