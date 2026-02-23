# This Python file uses the following encoding: utf-8
from mrid_utils import handlers, gauss_aux, warper, chmap, channel_mapper, point_mapper
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
import numpy as np
from PySide6.QtQuick3D import QQuick3D
from PySide6.QtCore import QObject, Property, Signal, QByteArray


def process_in_parallel(args):
    mrid, mrid_dict, sessionpath, atlas, atlaslabelsdf, dwi_path,t2s_path,mask_path,fixed_coordinates_path, moving_coordinates_path, channel_separation, total_ch = args

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


    fitted_points,regionNames,regionNumbers,df,barcode_r,barcode_d,CA1,dwi1Dsignal,pyrChIdx = chmap.main(
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
        total_ch
    )

    return fitted_points,regionNames,regionNumbers,df,barcode_r,barcode_d, mrid,CA1,dwi1Dsignal,pyrChIdx

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
        self.LoadMRI.renderers[3] = {}


    def get_gaussian_centers(self,transformation_files):
        """
        1. Warping heatmaps, segmentation and 4D volume at first-timestamp
        2. Getting Gaussian Centers or Electrodes
        """
        for idx in range(len(self.LoadMRI.vtk_widgets[0])):
            data_view = list(self.LoadMRI.vtk_widgets[0].keys())[idx]
            self.filename = self.LoadMRI.file_name[idx][:-7]
            roi_names = self.get_roinames(os.path.join(self.sessionpath, "anat", "labels.txt"))
            self.orientation = data_view

            transform_filename = transformation_files[idx]
            # Check if single transformation is provided
            if isinstance(transform_filename, str):
                print("Single transformation file provided")
                transform_path = os.path.join(self.sessionpath, "anat", transform_filename + ".txt")
                print(transform_path)
                tx = sitk.ReadTransform(transform_path)
                #not inversed transformation inverseTransform=False
                fixed_ind = transform_filename.split("-")[-1]
            # Check if multiple transformations are provided
            elif isinstance(transform_filename, list):
                print("Multiple transformation files provided, creating a composite transform")
                tx =  warper.create_composite_transform(transform_filename, os.path.join(self.sessionpath, "anat"))
                fixed_ind = transform_filename[-1].split("-")[-1]
            else:
                print("No valid transformation!")


            for roi_name in roi_names:
                heatmap_filename = ".".join((self.filename + "-" + roi_name + "-heatmap", "nii", "gz"))
                heatmap_path = os.path.join(self.sessionpath, "anat", heatmap_filename)
                if os.path.exists(heatmap_path):
                    #warps and resamples heatmaps
                    savepath = os.path.join(self.LoadMRI.session_path, 'analysed',roi_name,self.orientation)
                    fixed_path = warper.heatmap_warp(self.filename, roi_name, savepath, self.sessionpath, fixed_ind, tx)
                    #save gaussian centers
                    volume3d_resampled = np.asanyarray(nib.load(fixed_path).dataobj)
                    gauss_aux.run_gaussian_analysis(self.filename, savepath, roi_name, self.orientation, volume3d_resampled, self.labelsdf)

    def getCoordinates(self):
        """
        Loads a pickle file with MRID design parameters and the Gaussian centers found in self.get_gaussian_centers

        Finds best-fit to compute final  Gaussian centers and isualizes them in the warped MRI slice.

        """
        roi_names = self.get_roinames(os.path.join(self.sessionpath, "anat", "labels.txt"))
        pklfile_path,atlas,atlaslabelsdf,dwi_path,t2s_path,mask_path,moving_coordinates_path, fixed_coordinates_path,channel_separation, total_ch = self.get_atlas_points()

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

        ## Parallelism
        #args_list = [
        #    (mrid, mrid_dict, self.sessionpath, atlas, atlaslabelsdf,
        #     dwi_path,t2s_path,mask_path,fixed_coordinates_path, moving_coordinates_path,
        #     channel_separation, total_ch)
        #    for mrid in roi_names
        #]

        #with ProcessPoolExecutor() as executor:
        #    futures = [executor.submit(process_in_parallel, args) for args in args_list]

        #    for future in as_completed(futures):
        #        fitted_points,regionNames,regionNumbers,df,barcode_r,barcode_d,mrid,CA1,dwi1Dsignal,pyrChIdx = future.result()
        #        totalregionNumbers.extend(regionNumbers)
        #        totalfitted_points.append(fitted_points)
        #        totaldf.append(df)
        #        totalbarcode_r.append(barcode_r)
        #        totalbarcode_d.append(barcode_d)
        #        totalmrid.append(mrid)
        #        totalCA1.append(CA1)
        #        totaldwi1Dsignal.append(dwi1Dsignal)
        #        totalregionNames.append(regionNames)
        #        totalpyrChIdx.append(pyrChIdx)

        ## For loop
        fixed_coordinates = np.load(fixed_coordinates_path, mmap_mode="r")
        moving_coordinates = np.load(moving_coordinates_path, mmap_mode="r")
        nii_dwi=nib.load(dwi_path)
        dwi=np.asanyarray(nii_dwi.dataobj)
        dwi=dwi[:,:,:,0]
        nii_t2s=nib.load(t2s_path)
        t2s=np.asanyarray(nii_t2s.dataobj)
        nii_mask=nib.load(mask_path)
        mask=np.asanyarray(nii_mask.dataobj)

        for mrid in roi_names: ##different threads for each mrid?
            mrid = mrid.lower()
            savepath = os.path.join(self.sessionpath, 'analysed',mrid)
            fitted_points, regionNames,regionNumbers,df,barcode_r,barcode_d,CA1,dwi1Dsignal,pyrChIdx = chmap.main(mrid_dict,mrid, savepath, self.sessionpath,atlas,atlaslabelsdf,dwi, t2s,mask,fixed_coordinates,moving_coordinates,channel_separation,total_ch)
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

        totalregionNumbers = list(dict.fromkeys(totalregionNumbers))
        totalregionNumbers = list(map(int, totalregionNumbers))

        ## totalregionNumbers and atlas file: WHS_SD_rat_atlas_v4.nii.gz
        ## all regions in totalregionNumbers from WHS_SD_rat_atlas_v4.nii.gz = 1 else 0
        #img = sitk.ReadImage(self.atlas_path)
        #arr = sitk.GetArrayFromImage(img)
        #mask2 = np.isin(arr, totalregionNumbers)
        #arr_filtered = np.where(mask2, arr, 0)
        #out = sitk.GetImageFromArray(arr_filtered)
        #out.CopyInformation(img)
        #save_path = os.path.join(self.sessionpath, "atlas_filtered.nii.gz")
        #sitk.WriteImage(out, save_path)

        ## somehow highlight fitted points
        ## visualize in 3D
        ## QtQuick3D

        #return

        return roi_names,totaldf,totalbarcode_r,totalbarcode_d,totalmrid,totalCA1,totaldwi1Dsignal,totalregionNames,totalpyrChIdx,totalfitted_points

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



    def add_point(self,renderer, x, y,spacing,vol,idx):
        """
        Add point of found electrode Gaussian center to 4D MRI slice.
        """
        x=(x)*spacing[2]
        y=(y)*spacing[1]

        radius = 0.2

        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(x,y,0.2)
        sphere.SetRadius(radius)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, 0, 0)  # red

        renderer.AddActor(actor)

        return actor


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

        if data_view not in self.LoadMRI.renderers[3]:
            #create new renderer
            renderer = vtk.vtkRenderer()
            vtk_widget.GetRenderWindow().AddRenderer(renderer)
            vtk_widget.GetRenderWindow().SetMultiSamples(16)
            renderer.SetUseDepthPeeling(1)
            renderer.SetMaximumNumberOfPeels(200)
            renderer.SetOcclusionRatio(0.05)

            self.LoadMRI.renderers[3][data_view]=renderer
        else:
            renderer = self.LoadMRI.renderers[3][data_view]
            renderer.RemoveAllViewProps()

        if hasattr(self,'actor_4Dwarped'):
            renderer.RemoveActor(self.actor_4Dwarped)

        nonzero_y, nonzero_x = np.nonzero(img_slice)
        #spacing_x, spacing_y = spacing[1], spacing[0]  # careful: VTK x=cols, y=rows

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
        contrast_class = getattr(self.LoadMRI, f"contrastClass_{data_index}")
        contrast_class.lut_vtk[3]=lut

        # make low values (blue end) transparent
        # now build alpha: all zero voxels → alpha = 0
        prop = actor.GetProperty()
        prop.SetLookupTable(lut)
        prop.UseLookupTableScalarRangeOn()

        renderer.AddActor(actor)

        self.LoadMRI.heatmap = True
        self.actor_4Dwarped = actor

        return
        #add minirender, interactor and other stuff
        #scale = camera.GetParallelScale()

        #if 3 not in self.LoadMRI.minimap.minimap_renderers:
        #    self.LoadMRI.minimap.minimap_renderers[3] = {}
        #    self.LoadMRI.minimap.size_rectangle[3] = {}
        #    self.LoadMRI.minimap.zoom_rects[3] = {}
        #    self.LoadMRI.minimap.minimap_actors[3] = {}

        #spacing = self.LoadMRI.spacing[data_index]
        #self.LoadMRI.cursor.add_cursor4image(data_view,data_index,scale,img_vtk) #,spacing)
        #allow interaction
        #interactor = vtk_widget.GetRenderWindow().GetInteractor()
        #interactor.SetInteractorStyle(CustomInteractorStyle(self.LoadMRI.cursor, data_view,3,None,data_index))



    def get_atlas_points(self):
        #pop up asking for the view if 4D data used
        dlg = ChannelVariablesInput(self.MW)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            pklfile, root, channel_separation, total_ch,moving_coordinates_path, fixed_coordinates_path = dlg.get_values()
            #atlas_path=os.path.join(root, "WHS_SD_rat_atlas_v4_pack","WHS_SD_rat_atlas_v4.nii.gz")
            self.atlas_path=os.path.join(root,"WHS_SD_rat_atlas_v4.nii.gz")
            nii_atlas=nib.load(self.atlas_path)
            atlas=np.asanyarray(nii_atlas.dataobj)

            labels_path=os.path.join(root,"WHS_SD_rat_atlas_v4.label") #./atlas_labels.rtf'
            atlaslabelsdf=handlers.read_whs_labels(labels_path)

            dwi_path=os.path.join(root,"WHS_SD_rat_DWI_v1.01.nii.gz")
            t2s_path=os.path.join(root,"WHS_SD_rat_T2star_v1.01.nii.gz")
            mask_path=os.path.join(root,"WHS_SD_v2_brainmask_bin.nii.gz")

            return pklfile,atlas,atlaslabelsdf,dwi_path,t2s_path,mask_path,moving_coordinates_path, fixed_coordinates_path,channel_separation, total_ch

        return None


class ChannelVariablesInput(QtWidgets.QDialog):
    """
    A dialog window that allows users to specify anatomical regions and MRID tags (for 4D data).
    """
    def __init__(self, MW, parent=None):
        """
        Initialize the input dialog UI and connect signals.
        """
        super().__init__(parent)
        self.setWindowTitle("Input Values")
        self.setModal(True)
        self.resize(400, 400)
        self.MW = MW

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        text = QtWidgets.QPlainTextEdit("Please enter all variables asked for electrode channels.")
        text.setReadOnly(True)
        text.setFixedSize(400, 100)
        main_layout.addWidget(text)

        #pkl file
        #file_layout = QtWidgets.QHBoxLayout()
        #self.file_line_pkl = QtWidgets.QLineEdit()
        #self.file_line_pkl.setPlaceholderText("Please select the pkl file")
        #browse_button = QtWidgets.QPushButton("Browse")
        #browse_button.clicked.connect(self.browse_file_pkl)
        #file_layout.addWidget(browse_button)
        #main_layout.addLayout(file_layout)

        file_layout = QtWidgets.QHBoxLayout()
        self.file_line_pkl = QtWidgets.QLineEdit()
        self.file_line_pkl.setPlaceholderText("Please select the pkl file")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file_pkl)
        file_layout.addWidget(self.file_line_pkl)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        #ask user for atlas directory to get atlas file and upload matrices
        file_layout = QtWidgets.QHBoxLayout()
        self.file_folder = QtWidgets.QLineEdit()
        self.file_folder.setPlaceholderText("Select the folder, where Atlas data is saved")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_folder)
        file_layout.addWidget(self.file_folder)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        #root = QFileDialog.getExistingDirectory(None, 'Select the folder, where Atlas data is saved:', self.LoadMRI.session_path, QFileDialog.ShowDirsOnly)
        #seledct moving and fixed files!!!

        self.channel_separation = QtWidgets.QSpinBox()
        self.channel_separation.setRange(1, 200)
        main_layout.addWidget(QtWidgets.QLabel("Channel Separation"))
        main_layout.addWidget(self.channel_separation)

        self.total_channels = QtWidgets.QSpinBox()
        self.total_channels.setRange(1, 200)
        main_layout.addWidget(QtWidgets.QLabel("Total Channels"))
        main_layout.addWidget(self.total_channels)

        # upload matrices
        file_layout = QtWidgets.QHBoxLayout()
        self.file_line_fixed = QtWidgets.QLineEdit()
        self.file_line_fixed.setPlaceholderText("Please select the fixed coordinates")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file_fix)
        file_layout.addWidget(self.file_line_fixed)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)

        file_layout = QtWidgets.QHBoxLayout()
        self.file_line_mov = QtWidgets.QLineEdit()
        self.file_line_mov.setPlaceholderText("Please select the moving coordinates")
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file_mov)
        file_layout.addWidget(self.file_line_mov)
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
        self.file_folder.setPlaceholderText(os.path.basename(self.root))


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
        self.file_line_fixed.setPlaceholderText(os.path.basename(file_name))

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
        self.file_line_mov.setPlaceholderText(os.path.basename(file_name))

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
        self.file_line_pkl.setPlaceholderText(os.path.basename(file_name))


    def get_values(self):
        """
        Return structured data.
        """
        channel_separation = self.channel_separation.value()
        total_channels = self.total_channels.value()
        root=self.root
        moving_coordinates=  self.file_name_moving
        fixed_coordinates = self.file_name_fixed
        pklfile = self.file_name_pkl

        return pklfile, root, channel_separation, total_channels,moving_coordinates, fixed_coordinates


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = ChannelVariablesInput()
    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        data = dlg.get_values()



class VolumeProvider(QObject):
    volumeChanged = Signal()

    def __init__(self, nii_path):
        super().__init__()

        # Load NIfTI
        nii = nib.load(nii_path)
        vol = nii.get_fdata()  # (Z, Y, X)

        # Normalize to [0, 1]
        vol = vol.astype(np.float32)
        vol -= vol.min()
        vol /= (vol.max() + 1e-8)

        self._volume = vol
        self._size = (vol.shape[2], vol.shape[1], vol.shape[0])  # X,Y,Z

        # Convert to raw bytes (float32)
        self._bytes = QByteArray(vol.tobytes())

    @Property(QByteArray, notify=volumeChanged)
    def volumeData(self):
        return self._bytes

    @Property(int, constant=True)
    def sizeX(self):
        return self._size[0]

    @Property(int, constant=True)
    def sizeY(self):
        return self._size[1]

    @Property(int, constant=True)
    def sizeZ(self):
        return self._size[2]
