# This Python file uses the following encoding: utf-8
from mrid_utils import handlers, gauss_aux, warper, chmap
import numpy as np
import nibabel as nib
import os
import pickle
from PySide6.QtWidgets import QFileDialog
import vtk
import SimpleITK as sitk
from vtk.util import numpy_support
from PySide6 import QtWidgets
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed


def process_in_parallel(args):
    mrid, mrid_dict, sessionpath, atlas, atlaslabelsdf, dwi_path,t2s_path,mask_path,fixed_coordinates_path, moving_coordinates_path, channel_separation, total_ch,chMap_file = args

    mrid = mrid.lower()
    savepath = os.path.join(sessionpath, 'analysed',mrid)

    # Memory-mapped loading
    fixed_coordinates = np.load(fixed_coordinates_path, mmap_mode="r")
    moving_coordinates = np.load(moving_coordinates_path, mmap_mode="r")
    nii_dwi=nib.load(dwi_path)
    dwi=np.asanyarray(nii_dwi.dataobj)
    dwi=dwi[:,:,:,0]
    nii_t2s=nib.load(t2s_path)
    t2s=np.asanyarray(nii_t2s.dataobj)
    nii_mask=nib.load(mask_path)
    mask=np.asanyarray(nii_mask.dataobj)


    fitted_points,regionNames,regionNumbers,df,barcode_r,barcode_d,CA1,dwi1Dsignal,pyrChIdx,chMap,atlasCoordinates_pkl = chmap.main(
        mrid_dict,
        mrid,
        savepath,
        sessionpath,
        atlas,
        atlaslabelsdf,
        dwi,
        t2s,
        mask,
        fixed_coordinates,
        moving_coordinates,
        channel_separation,
        total_ch,
        chMap_file
    )

    return fitted_points,regionNames,regionNumbers,df,barcode_r,barcode_d, mrid,CA1,dwi1Dsignal,pyrChIdx,chMap,atlasCoordinates_pkl

class ElectrodeLoc:
    """
    Class for Electrode Localisation and visualizing the found points on MRI image in 4th image.
    """
    def __init__(self,LoadMRI,MW):
        """
        Initialize the ElectrodeLoc object with a reference to LoadMRI.
        """
        self.LoadMRI = LoadMRI
        self.MW = MW
        self.savepath =  os.path.join(LoadMRI.session_path,"analysed")
        self.sessionpath = LoadMRI.session_path
        self.labelsdf = handlers.read_labels(os.path.join(self.sessionpath, "anat", "labels.txt"))


    def get_gaussian_centers(self,transformation_files):
        """
        1. Warping heatmaps, segmentation and 4D volume at first-timestamp
        2. Getting Gaussian Centers or Electrodes
        """
        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
            self.filename = os.path.basename(self.LoadMRI.volumes[idx].file_path[:-7])
            roi_names = self.get_roinames(os.path.join(self.sessionpath, "anat", "labels.txt"))
            self.orientation = data_view

            transform_filename = transformation_files[idx]

            # Check if single transformation is provided
            if isinstance(transform_filename, str):
                transform_path = transform_filename #os.path.join(self.sessionpath, "anat", transform_filename + ".txt")
                tx = sitk.ReadTransform(transform_path)
                #not inversed transformation inverseTransform=False
                fixed_ind = transform_filename.split("-")[-1].rsplit(".", 1)[0]
            # Check if multiple transformations are provided
            elif isinstance(transform_filename, list):
                tx =  warper.create_composite_transform(transform_filename, os.path.join(self.sessionpath, "anat"))
                fixed_ind = transform_filename[-1].split("-")[-1].rsplit(".", 1)[0]
            else:
                print("No valid transformation!")

            self.progress.setValue(int(10+(idx+1)/len(self.LoadMRI.vtk_widgets[0])*20))

            for roi_name in roi_names:
                heatmap_filename = ".".join((self.filename + "-" + roi_name + "-heatmap", "nii", "gz"))
                heatmap_path = os.path.join(self.sessionpath, "analysed", roi_name,data_view,heatmap_filename)
                if os.path.exists(heatmap_path):
                    #warps and resamples heatmaps
                    savepath = os.path.join(self.LoadMRI.session_path, 'analysed',roi_name,data_view)
                    fixed_path = warper.heatmap_warp(self.filename, roi_name, savepath, self.sessionpath, fixed_ind, tx)
                    self.progress.setValue(int(10+(idx+1)/len(self.LoadMRI.vtk_widgets[0])*60))
                    #save gaussian centers
                    volume3d_resampled = np.asanyarray(nib.load(fixed_path).dataobj)
                    gauss_aux.run_gaussian_analysis(self.filename, savepath, roi_name, data_view, volume3d_resampled, self.labelsdf)

            self.progress.setValue(int(10+(idx+1)/len(self.LoadMRI.vtk_widgets[0])*90))


    def getCoordinates(self):
        """
        Loads a pickle file with MRID design parameters and the Gaussian centers found in self.get_gaussian_centers

        Finds best-fit to compute final  Gaussian centers and isualizes them in the warped MRI slice.

        """
        roi_names = self.get_roinames(os.path.join(self.sessionpath, "anat", "labels.txt"))
        result = self.get_atlas_points(roi_names)
        if result is None:
            return None
        else:
            pklfile_path,atlas,atlaslabelsdf,dwi_path,t2s_path,mask_path,moving_coordinates_path, fixed_coordinates_path,channel_separation, total_ch,chMap_file = result
        self.LoadMRI.ElectrodeLoc.groupBox_progressGUI.setVisible(True)

        with open(pklfile_path, 'rb') as f:
            mrid_dict = pickle.load(f)

        totalregionNumbers = []
        totalmrid = []
        totaldf = []
        totalbarcode_d = []
        totalbarcode_r = []
        totalfitted_points = []
        totalCA1 =  []
        totaldwi1Dsignal = []
        totalregionNames= []
        totalpyrChIdx= []
        totalchMap = []
        totalatlasCoordinates_pkl = []

        ## Parallelism
        self.progress.setValue(20)

        #over all tags ->
        args_list = [
            (mrid, mrid_dict, self.sessionpath, atlas, atlaslabelsdf,
             dwi_path,t2s_path,mask_path,fixed_coordinates_path, moving_coordinates_path,
             channel_separation, total_ch,chMap_file)
            for mrid in roi_names
        ]

        print('chMap_file',chMap_file,flush=True)

        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(process_in_parallel, args) for args in args_list]
            i=1

            for future in as_completed(futures):
                self.progress.setValue(int(20+i/len(roi_names)*50))
                fitted_points,regionNames,regionNumbers,df,barcode_r,barcode_d,mrid,CA1,dwi1Dsignal,pyrChIdx,chMap,atlasCoordinates_pkl = future.result()
                totalregionNumbers.extend(regionNumbers)
                totalfitted_points.append(fitted_points)
                totaldf.append(df)
                totalbarcode_r.append(barcode_r)
                totalbarcode_d.append(barcode_d)
                totalmrid.append(mrid)
                totalCA1.append(CA1)
                totaldwi1Dsignal.append(dwi1Dsignal)
                totalregionNames.append(regionNames)
                totalpyrChIdx.append(pyrChIdx)
                totalchMap.append(chMap)
                totalatlasCoordinates_pkl.append(atlasCoordinates_pkl)
                i+=1

        self.progress.setValue(80)

        totalregionNumbers = list(dict.fromkeys(totalregionNumbers))
        totalregionNumbers = list(map(int, totalregionNumbers))

        # "/home/neurox/Documents/MRID-GUI/Files/Atlas/WHS_SD_rat_atlas_v4.nii.gz"
        file_with_regions = self.atlas_path
        atlas_image = sitk.ReadImage(file_with_regions)
        volume = sitk.GetArrayFromImage(atlas_image)
        volume[~np.isin(volume,totalregionNumbers)]=0

        label_image = sitk.GetImageFromArray(volume)
        label_image.CopyInformation(atlas_image)

        # Suggest a default name (for example, based on the original file name)
        save_path = os.path.join(self.savepath,'atlas-regions.nii.gz')
        sitk.WriteImage(label_image, save_path)

        self.add_point(fitted_points)
        self.progress.setValue(100)


        return roi_names,totaldf,totalbarcode_r,totalbarcode_d,totalmrid,totalCA1,totaldwi1Dsignal,totalregionNames,totalpyrChIdx,totalfitted_points,totalchMap,totalatlasCoordinates_pkl

    def get_roinames(self,filename):
        """
        Read ROI names from a label file.
        """
        labels = []
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Split by tab or spaces
                parts = line.split()
                # The last column is the quoted label name
                if len(parts) >= 8:
                    label = parts[-1].strip('"')
                    labels.append(label)
        labels.pop(0)

        roi_names = []
        pure_labels = [l.rstrip("0123456789") for l in labels]

        for i, label in enumerate(labels):
            if label.endswith("1"):
                roi_names.append((pure_labels[i]))

        return roi_names



    def add_point(self,fitted_points):
        """
        Add point of found electrode Gaussian center to 4D MRI slice.
        """
        for data_index in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[data_index]
            renderer = self.LoadMRI.renderers[0][data_view]
            #
            filename = self.LoadMRI.volumes[data_index].file_path[0:self.LoadMRI.volumes[data_index].file_path.find('.')]
            filename_4d_warped = ".".join((filename + "-resampled-warped", "nii", "gz"))
            filename_4d_warped_path = os.path.join(self.savepath, filename_4d_warped)
            img_4d= sitk.ReadImage(filename_4d_warped_path)
            vol = sitk.GetArrayFromImage(img_4d)
            if data_view=='sagittal':
                img_slice = np.fliplr(vol[:,:,round(fitted_points[0][0])].T)
            else:
                img_slice = vol[int(fitted_points[0][2]),:,:]
            spacing_4d = img_4d.GetSpacing() #xyz # #
            spacing = self.LoadMRI.volumes[data_index].spacing

            self.visualize_4Dwarpedslice(img_slice,spacing_4d,data_index,data_view)

            for idx in range(len(fitted_points)):
                if data_view=='sagittal':
                    x = self.LoadMRI.volumes[data_index].slices[0].shape[0]-1-fitted_points[idx][2]
                    y = fitted_points[idx][1]
                    spacing = np.array(spacing)
                    spacing[2] = spacing[0]
                else:
                    x = fitted_points[idx][0]
                    y = fitted_points[idx][1]

                print(x,y,spacing,flush=True)
                x=(x)*spacing_4d[2]
                y=(y)*spacing_4d[1]
                print(x,y,spacing_4d,flush=True)
                radius = 0.2

                sphere = vtk.vtkSphereSource()

                sphere.SetCenter(x,y,0.2) #0.2
                sphere.SetRadius(radius)

                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(sphere.GetOutputPort())

                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.GetProperty().SetColor(1, 0, 0)  # red

                renderer.AddActor(actor)

            renderer.GetRenderWindow().Render()

                #return actor

    def visualize_4Dwarpedslice(self, img_slice,spacing,data_index,data_view):
            """
                Visualize a single slice of the first timestamp to then add the found electrode locations.

                Parameters
                ----------
                img_slice : ndarray
                    2D numpy array representing the heatmap slice to display.
                reset_camera : bool
                    Whether to reset the camera to focus on the heatmap area.
            """
            # add to vtkwidgets for rendering and zooming
            vtk_widget = self.LoadMRI.vtk_widgets[3][data_view]
            vtk_data = numpy_support.numpy_to_vtk(img_slice.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
            h, w = img_slice.shape
            spacing = (spacing[2], spacing[1], 1)

            #renderer,img_vtk = self.open_mainimage(vtk_widget,vtk_data, spacing,w,h)
            img_vtk = vtk.vtkImageData()
            img_vtk.SetDimensions(w, h, 1)  # VTK expects width x height x depth
            img_vtk.SetSpacing(spacing)
            img_vtk.GetPointData().SetScalars(vtk_data)

            #create new renderer
            renderer = self.LoadMRI.renderers[0][data_view]
            #remove original image
            renderer.RemoveActor(self.LoadMRI.actors[0][data_view])

            nonzero_y, nonzero_x = np.nonzero(img_slice)
            spacing_x, spacing_y = spacing[1], spacing[0]  # careful: VTK x=cols, y=rows
            if len(nonzero_x) == 0 or len(nonzero_y) == 0:
                ny, nx = np.nonzero(self.LoadMRI.paintbrush.label_volume[self.LoadMRI.slice_indices[0],:,:])
                # Get pixel bounds
                x_min, x_max = nx.min(), nx.max()
                y_min, y_max = ny.min(), ny.max()

                # Convert pixel coordinates to world coordinates
                self.center_x = (x_min + x_max) / 2 * spacing_x
                self.center_y = (y_min + y_max) / 2 * spacing_y
                self.width = (x_max - x_min) * spacing_x
                self.height = (y_max - y_min) * spacing_y

            else:
                # Get pixel bounds
                x_min, x_max = nonzero_x.min()-1, nonzero_x.max()+1
                y_min, y_max = nonzero_y.min()-1, nonzero_y.max()+1

                # Convert pixel coordinates to world coordinates
                self.center_x = (x_min + x_max) / 2 * spacing_x
                self.center_y = (y_min + y_max) / 2 * spacing_y
                self.width = (x_max - x_min) * spacing_x
                self.height = (y_max - y_min) * spacing_y

            camera_base = self.LoadMRI.renderers[0][data_view].GetActiveCamera()
            fp = camera_base.GetFocalPoint()
            pos = camera_base.GetPosition()

            camera = renderer.GetActiveCamera()
            camera.SetFocalPoint(self.center_x, self.center_y, fp[2])
            camera.SetPosition(self.center_x, self.center_y, pos[2])  # small offset in z
            camera.ParallelProjectionOn()
            camera.SetParallelScale(max(self.width, self.height)/2)

            # Add image to actor to then be added to renderer
            actor = vtk.vtkImageActor()
            scalar = img_vtk.GetScalarRange()
            actor.GetProperty().SetColorWindow(scalar[1])
            actor.GetProperty().SetColorLevel(scalar[1]/2)

            actor.SetInputData(img_vtk)
            actor.Modified()
            actor.GetProperty().SetInterpolationTypeToNearest() #Linear()
            actor.GetProperty().SetOpacity(1)

            vmin, vmax = np.percentile(vtk_data, [0,100])
            lut = vtk.vtkLookupTable()
            lut.SetTableRange(vmin, vmax)
            lut.SetValueRange(0.0, 1.0)
            lut.SetSaturationRange(0.0, 0.0)
            lut.Build()
            contrast_class = self.LoadMRI.contrast[data_index]
            contrast_class.lut_vtk[3]=lut

            # make low values (blue end) transparent
            # now build alpha: all zero voxels → alpha = 0
            prop = actor.GetProperty()
            prop.SetLookupTable(lut)
            prop.UseLookupTableScalarRangeOn()

            renderer.AddActor(actor)

            self.LoadMRI.heatmap = True
            self.actor_heatmap = actor

            vtk_widget.GetRenderWindow().Render()


    def get_atlas_points(self,roi_names):
        #pop up asking for the view if 4D data used
        dlg = ChannelVariablesInput(self.MW,roi_names)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            pklfile, root, channel_separation, total_ch,moving_coordinates_path, fixed_coordinates_path,chMap_file = dlg.get_values()
            self.atlas_path=os.path.join(root,"WHS_SD_rat_atlas_v4.nii.gz")
            nii_atlas=nib.load(self.atlas_path)
            atlas=np.asanyarray(nii_atlas.dataobj)

            labels_path=os.path.join(root,"WHS_SD_rat_atlas_v4.label") #./atlas_labels.rtf'
            atlaslabelsdf=handlers.read_whs_labels(labels_path)

            dwi_path=os.path.join(root,"WHS_SD_rat_DWI_v1.01.nii.gz")
            t2s_path=os.path.join(root,"WHS_SD_rat_T2star_v1.01.nii.gz")
            mask_path=os.path.join(root,"WHS_SD_v2_brainmask_bin.nii.gz")

            return pklfile,atlas,atlaslabelsdf,dwi_path,t2s_path,mask_path,moving_coordinates_path, fixed_coordinates_path,channel_separation, total_ch,chMap_file

        return None


class ChannelVariablesInput(QtWidgets.QDialog):
    """
    A dialog window that allows users to specify anatomical regions and MRID tags (for 4D data).
    """
    def __init__(self, MW, roi_names,parent=None):
        """
        Initialize the input dialog UI and connect signals.
        """
        super().__init__(parent)
        self.setWindowTitle("Input Values")
        self.setModal(True)
        self.resize(500, 500)
        self.MW = MW
        self.roi_names = roi_names
        gui_dir = os.path.join(os.path.dirname(os.path.dirname((__file__))), "Files")

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        text = QtWidgets.QPlainTextEdit("Please enter all variables asked for electrode channels.")
        text.setReadOnly(True)
        #text.setFixedSize(400, 100)
        main_layout.addWidget(text)

        file_layout = QtWidgets.QHBoxLayout()
        self.file_line_pkl = QtWidgets.QTextEdit()

        self.file_name_pkl = os.path.join(gui_dir,'mrid_library.pkl')
        self.file_line_pkl.setText(f"File found: {self.file_name_pkl} \n Please select another pkl file if requested")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file_pkl)
        file_layout.addWidget(self.file_line_pkl)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        #ask user for atlas directory to get atlas file and upload matrices
        file_layout = QtWidgets.QHBoxLayout()
        self.file_folder = QtWidgets.QTextEdit()
        self.root = os.path.join(gui_dir,'Atlas')
        self.file_folder.setText(f"Folder found: {self.root} \n Select another folder, where Atlas data is saved if requested")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_folder)
        file_layout.addWidget(self.file_folder)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        #root = QFileDialog.getExistingDirectory(None, 'Select the folder, where Atlas data is saved:', self.LoadMRI.session_path, QFileDialog.ShowDirsOnly)
        #seledct moving and fixed files!!!

        self.channel_separation = QtWidgets.QSpinBox()
        self.channel_separation.setRange(1, 200)
        self.channel_separation.setValue(50)
        main_layout.addWidget(QtWidgets.QLabel("Channel Separation [um]"))
        main_layout.addWidget(self.channel_separation)

        self.total_channels = {}
        group_box = QtWidgets.QGroupBox("Total Channels [per tag]")
        group_layout = QtWidgets.QVBoxLayout(group_box)
        for roi in self.roi_names:
            self.total_channels[roi] = QtWidgets.QSpinBox()
            self.total_channels[roi].setRange(1, 200)
            self.total_channels[roi].setValue(64)
            group_layout.addWidget(QtWidgets.QLabel(f"{roi.capitalize()}"))
            group_layout.addWidget(self.total_channels[roi])

        main_layout.addWidget(group_box)

        # upload matrices
        file_layout = QtWidgets.QHBoxLayout()
        self.file_line_fixed = QtWidgets.QTextEdit()
        if os.path.exists(os.path.join(self.MW.LoadMRI.session_path, 'registration','fixed_img-indeces.npy')):
            self.file_name_fixed = os.path.join(self.MW.LoadMRI.session_path, 'registration','fixed_img-indeces.npy')
            self.file_line_fixed.setText(f"File found: {self.file_name_fixed} \n Select another file if requested")
        else:
            self.file_line_fixed.setText("Please select the fixed coordinates. No such file found.")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file_fix)
        file_layout.addWidget(self.file_line_fixed)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        file_layout = QtWidgets.QHBoxLayout()
        self.file_line_mov = QtWidgets.QTextEdit()
        if os.path.exists(os.path.join(self.MW.LoadMRI.session_path, 'registration','moving_img_resampled25um-indeces.npy')):
            self.file_name_moving = os.path.join(self.MW.LoadMRI.session_path, 'registration','moving_img_resampled25um-indeces.npy')
            self.file_line_mov.setText(f"File found: {self.file_name_moving} \n Select another file if requested")
        else:
            self.file_line_mov.setText("Please select the moving coordinates. No such file found.")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file_mov)
        file_layout.addWidget(self.file_line_mov)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        file_layout = QtWidgets.QHBoxLayout()
        self.file_chMap = None
        self.chMap_file_line = QtWidgets.QTextEdit()
        self.chMap_file_line.setText("If exists, please upload chMap file. \n Otherwise channels are named sequentially, starting at 1.")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file_chMap)
        file_layout.addWidget(self.chMap_file_line)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        #buttons
        button_layout = QtWidgets.QHBoxLayout()
        # Add a small text label
        label = QtWidgets.QLabel("Press OK if data is correct")
        label.setStyleSheet("font-size: 10pt;")  # Optional: make it smaller
        button_layout.addWidget(label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        # Add the buttons to the same layout
        button_layout.addWidget(buttons)
        # Add the whole layout to your main layout
        main_layout.addLayout(button_layout)

    def browse_folder(self):
        """
        Opens File Dialog for user to choose labels.txt
        """
        self.root = QFileDialog.getExistingDirectory(
            None,
            'Select the folder, where Atlas data is saved:',
            self.MW.LoadMRI.session_path,
            QFileDialog.ShowDirsOnly)
        #User cancelled
        if not self.root:
            return
        self.file_folder.setText(os.path.basename(self.root))


    def browse_file_chMap(self):
        """
        Opens File Dialog for user to choose labels.txt
        """
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            self.MW.LoadMRI.session_path,
            "NPY files (*.npy)"
        )

        #User cancelled
        if not file_name:
            return
        self.file_chMap = file_name
        self.chMap_file_line.setText(os.path.basename(file_name))


    def browse_file_fix(self):
        """
        Opens File Dialog for user to choose labels.txt
        """
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            self.MW.LoadMRI.session_path,
            "NPY files (*.npy)"
        )

        #User cancelled
        if not file_name:
            return
        self.file_name_fixed = file_name
        self.file_line_fixed.setText(os.path.basename(file_name))

    def browse_file_mov(self):
        """
        Opens File Dialog for user to choose labels.txt
        """
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            self.MW.LoadMRI.session_path,
            "NPY files (*.npy)"
        )

        #User cancelled
        if not file_name:
            return
        self.file_name_moving = file_name
        self.file_line_mov.setText(os.path.basename(file_name))

    def browse_file_pkl(self):
        # Pickle file that contains all the design parameters of each MRID tag
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Please select pkl file",
            self.MW.LoadMRI.session_path,
            "PKL files (*.pkl)"
        )
        #User cancelled
        if not file_name:
            return
        self.file_name_pkl = file_name
        self.file_line_pkl.setText(os.path.basename(file_name))


    def get_values(self):
        """
        Return structured data.
        """
        channel_separation = self.channel_separation.value()
        total_channels = []
        for roi in self.roi_names:
            total_channels.append(self.total_channels[roi].value())
        root=self.root
        moving_coordinates=  self.file_name_moving
        fixed_coordinates = self.file_name_fixed
        pklfile = self.file_name_pkl
        chMap_file = self.file_chMap

        return pklfile, root, channel_separation, total_channels,moving_coordinates, fixed_coordinates,chMap_file


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = ChannelVariablesInput()
    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        data = dlg.get_values()
