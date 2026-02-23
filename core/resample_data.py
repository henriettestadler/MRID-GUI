# This Python file uses the following encoding: utf-8
import SimpleITK as sITK
from PySide6.QtWidgets import QFileDialog
import os
from core.load_MRI_file import LoadMRI

class ResampleData:
    """
    Handles resampling of 3D MRI image data to fixed voxel sizes (100 um or 25 um). Once resampled to 100um, the new resampled image is opened and displayed.
    Based on the ResampleAction function from FSLeyes (open-source software).
    """

    def __init__(self,LoadMRI):
        """ Initialize the ResampleData class. """
        self.LoadMRI = LoadMRI



    def resampling100um(self,index):
        """
            Resample the main MRI image to a z-spacing of 100um).
            Applies padding at the end to avoid black slices after resampling.
        """
        file_name = self.LoadMRI.file_name[index]
        img = sITK.ReadImage(file_name)
        old_size = img.GetSize()

        old_spacing = self.LoadMRI.spacing[index][::-1] #x,y,z
        new_spacing = [old_spacing[0],old_spacing[1],0.1] #x,y,z

        new_size = [
            int(round(osz * ospc / nspc))
            for osz, ospc, nspc in zip(old_size, old_spacing, new_spacing)
        ]

        new_newspacing = [
            old_sz * old_sp / new_sz
            for old_sz, old_sp, new_sz in zip(old_size, old_spacing, new_size)
        ]

        # Get last slice intensities to avoid blackness in the last slides
        last_slice_array = sITK.GetArrayFromImage(img)[-1,:,:]
        edge_value = float(last_slice_array.mean())

        last_slice = img[:, :, -1]

        # Repeat the last slice N times to extend volume
        origin = img.GetOrigin()
        pad_slices = 20  # number of repeated slices
        replicated = [last_slice] * pad_slices
        replicated_stack = sITK.JoinSeries(replicated)

        replicated_stack.SetSpacing((old_spacing[0], old_spacing[1], old_spacing[2]))
        replicated_stack.SetOrigin((origin[0], origin[1], origin[2] + old_spacing[2]*old_size[2]))
        replicated_stack.SetDirection(img.GetDirection())

        image_padded = sITK.Paste(
            sITK.ConstantPad(img, [0, 0, 0], [0, 0, pad_slices], 0),
            replicated_stack,
            replicated_stack.GetSize(),
            destinationIndex=[0, 0, img.GetSize()[2]]
        )

        resampled = sITK.Resample(
            image_padded,
            new_size,
            sITK.Transform(),
            sITK.sitkLinear,
            image_padded.GetOrigin(),
            new_newspacing,
            image_padded.GetDirection(),
            edge_value,
            image_padded.GetPixelID()
        )
        filename_end = 'resampled100um.nii.gz'
        file_name = self.save_as_niigz(resampled,filename_end,index)
        self.file_name100um = file_name

        return file_name


    def resampling25um(self,index):
        """
            Resample the main MRI image sequentially in z, y, and x directions
            to achieve a final voxel size of 25 µm isotropic.
        """
        file_name = self.LoadMRI.file_name[index]
        img = sITK.ReadImage(file_name)
        old_spacing = self.LoadMRI.spacing[index][::-1] #x,y,z

        old_size = img.GetSize()
        # first resample in z
        new_spacing = [old_spacing[0],old_spacing[1],0.025] #x,y,z

        new_size = [
            int(round(osz * ospc / nspc))
            for osz, ospc, nspc in zip(old_size, old_spacing, new_spacing)
        ]

        new_newspacing = [
            old_sz * old_sp / new_sz
            for old_sz, old_sp, new_sz in zip(old_size, old_spacing, new_size)
        ]

        # Get last slice intensities to avoid blackness in the last slides
        last_slice_array = sITK.GetArrayFromImage(img)[-1,:,:]
        edge_value = float(last_slice_array.mean())


        last_slice = img[:, :, -1]

        # Repeat the last slice N times to extend volume
        origin = img.GetOrigin()
        pad_slices = 20 # number of repeated slices
        replicated = [last_slice] * pad_slices
        replicated_stack = sITK.JoinSeries(replicated)
        replicated_stack.SetSpacing((old_spacing[0], old_spacing[1], old_spacing[2]))
        replicated_stack.SetOrigin((origin[0], origin[1], origin[2] + old_spacing[2]*old_size[2]))
        replicated_stack.SetDirection(img.GetDirection())

        image_padded = sITK.Paste(
            sITK.ConstantPad(img, [0, 0, 0], [0, 0, pad_slices], 0),
            replicated_stack,
            replicated_stack.GetSize(),
            destinationIndex=[0, 0, img.GetSize()[2]]
        )

        resampled_z = sITK.Resample(
            image_padded,
            new_size,
            sITK.Transform(),
            sITK.sitkLinear,
            image_padded.GetOrigin(),
            new_newspacing,
            image_padded.GetDirection(),
            edge_value,
            image_padded.GetPixelID()
        )

        # resample in y
        old_spacing = resampled_z.GetSpacing()
        old_size = resampled_z.GetSize()
        new_spacing = [old_spacing[0],0.025,old_spacing[2]] #x,y,z

        new_size = [
            int(round(osz * ospc / nspc))
            for osz, ospc, nspc in zip(old_size, old_spacing, new_spacing)
        ]

        new_newspacing = [
            old_sz * old_sp / new_sz
            for old_sz, old_sp, new_sz in zip(old_size, old_spacing, new_size)
        ]

        # Get last slice intensities to avoid blackness in the last slides
        last_slice_array = sITK.GetArrayFromImage(resampled_z)[:,-1,:]
        edge_value = float(last_slice_array.mean())

        img = resampled_z
        last_slice = img[:, -1:, :]

        ## Repeat the last slice N times to extend volume
        origin = resampled_z.GetOrigin()
        pad_slices = 20  # number of repeated slices
        img_padded = sITK.ConstantPad(
            img,
            padLowerBound=[0, 0, 0],
            padUpperBound=[0, pad_slices, 0],
            constant=0  # temporary, will be overwritten
        )

        last_slice = sITK.Extract(
            img_padded,
            size=[img.GetSize()[0], 1, img.GetSize()[2]],
            index=[0, img.GetSize()[1]-1, 0]
        )

        image_padded = img_padded
        for i in range(pad_slices):
            image_padded = sITK.Paste(
                destinationImage=img_padded,
                sourceImage=last_slice,
                sourceSize=last_slice.GetSize(),
                destinationIndex=[0, img.GetSize()[1]+i, 0]
            )

        resampled_zy = sITK.Resample(
            image_padded,
            new_size,
            sITK.Transform(),
            sITK.sitkLinear,
            image_padded.GetOrigin(),
            new_newspacing,
            image_padded.GetDirection(),
            edge_value,
            image_padded.GetPixelID()
        )

        # resample in x
        old_spacing = resampled_zy.GetSpacing()
        old_size = resampled_zy.GetSize()
        new_spacing = [0.025, old_spacing[1],old_spacing[2]]

        new_size = [
            int(round(osz * ospc / nspc))
            for osz, ospc, nspc in zip(old_size, old_spacing, new_spacing)
        ]

        new_newspacing = [
            old_sz * old_sp / new_sz
            for old_sz, old_sp, new_sz in zip(old_size, old_spacing, new_size)
        ]

        # Get last slice intensities to avoid blackness in the last slides
        last_slice_array = sITK.GetArrayFromImage(resampled_zy)[-1,:,:]
        edge_value = float(last_slice_array.mean())

        img = resampled_zy
        last_slice = img[-1:, :, :]

        ## Repeat the last slice N times to extend volume
        origin = resampled_zy.GetOrigin()
        pad_slices = 20  # number of repeated slices
        img_padded = sITK.ConstantPad(
            img,
            padLowerBound=[0, 0, 0],
            padUpperBound=[pad_slices, 0, 0],
            constant=0  # temporary, will be overwritten
        )

        last_slice = sITK.Extract(
            img_padded,
            size=[1, img.GetSize()[1], img.GetSize()[2]],
            index=[img.GetSize()[0]-1, 0, 0]
        )

        image_padded_x = img_padded
        for i in range(pad_slices):
            image_padded_x = sITK.Paste(
                destinationImage=image_padded_x,
                sourceImage=last_slice,
                sourceSize=last_slice.GetSize(),
                destinationIndex=[img.GetSize()[0]+i,0, 0]
            )

        resampled = sITK.Resample(
            image_padded_x,
            new_size,
            sITK.Transform(),
            sITK.sitkLinear,
            image_padded_x.GetOrigin(),
            new_newspacing,
            image_padded_x.GetDirection(),
            edge_value,
            image_padded_x.GetPixelID()
        )

        filename_end = 'resampled.nii.gz'
        save_path = self.save_as_niigz(resampled,filename_end,index)

        return save_path



    def save_as_niigz(self,image,filename_end:str,index:int):
        """
        Save the current label volume as a NIfTI (.nii.gz) file.
        """

        file_name = self.LoadMRI.file_name[index][:-7]
        default_name = f"{file_name}_{filename_end}" #"label_volume.nii.gz"
        save_path = os.path.join(self.LoadMRI.session_path, default_name)
        sITK.WriteImage(image, save_path)
        return save_path


    def open_as_new_file(self,buttons_gui3d,MW):
        """
            Replace the currently loaded MRI file with the new resampled one.
            Clears old renderers, actors, and measurement lines from the GUI.
        """
        data_index = 0
        self.LoadMRI.file_name[data_index] = self.file_name100um
        img = sITK.ReadImage(self.file_name100um)
        #new volume and spacing
        self.LoadMRI.volume[data_index] = {}
        self.LoadMRI.volume[data_index][0] = sITK.GetArrayFromImage(img)
        self.LoadMRI.volume[data_index][1] = sITK.GetArrayFromImage(img)
        self.LoadMRI.volume[data_index][2] = sITK.GetArrayFromImage(img)
        self.LoadMRI.ref_image = img
        self.LoadMRI.spacing = {}
        self.LoadMRI.spacing[data_index] = []
        self.LoadMRI.spacing[data_index] = img.GetSpacing()[::-1]
        self.LoadMRI.vol_dim = self.LoadMRI.volume[data_index][0].ndim

        self.LoadMRI.is_first_slice = False


        #delete measurement actors
        for view_name, line_actor,line_slice_index,text_actor in self.LoadMRI.measurement_lines:
            renderer = self.LoadMRI.measurement_renderer[view_name]
            renderer.RemoveActor(line_actor)
            text_actor.SetVisibility(0)
        self.LoadMRI.measurement_lines = []

        for idx in self.LoadMRI.minimap.minimap_renderers:
            for vn in self.LoadMRI.minimap.minimap_renderers[idx]:
                self.LoadMRI.minimap.minimap_renderers[idx][vn].RemoveAllViewProps()
            self.LoadMRI.minimap.minimap_renderers[idx] = {}


        for idx in self.LoadMRI.renderers:
            for vn in self.LoadMRI.renderers[idx]:
                self.LoadMRI.renderers[idx][vn].RemoveAllViewProps()
            self.LoadMRI.renderers[idx] = {}
            self.LoadMRI.actors[idx] = {}
            self.LoadMRI.img_vtks[idx] = {}

        #remove old renderers
        for image_index,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
            for view_name, vtk_widget in vtk_widget_image.items():
                ren_win = vtk_widget.GetRenderWindow()
                ren_coll = ren_win.GetRenderers()

                renderers_to_remove = [ren_coll.GetItemAsObject(i) for i in range(ren_coll.GetNumberOfItems())]

                for old_renderer in renderers_to_remove:
                    ren_win.RemoveRenderer(old_renderer)

        #load file again, update cursor
        self.LoadMRI = LoadMRI()
        self.LoadMRI.file_name = {}
        self.LoadMRI.file_name[0]= self.file_name100um

        MW.ui.comboBox_resamplefiles.addItem(os.path.basename(self.file_name100um)) #add to combobox for resampling
        data_view = "coronal" #for 3d data
        buttons_gui3d.popup.close()
        MW.restart_gui(self.file_name100um, data_view)

