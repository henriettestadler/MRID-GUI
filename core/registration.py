# This Python file uses the following encoding: utf-8
import SimpleITK as sITK
import os
from picsl_greedy import Greedy3D
import numpy as np

class Registration:
    """
       Perform rigid registration of a moving MRI image to a fixed MRI image.

       This class uses SimpleITK to perform a rigid registration (Euler 3D transform)
       and saves the resulting transform both as a rigid transform and an affine-style transform.

       Parameters
       ----------
       LoadMRI : object
           The main MRI loader object that contains session information,
           paths, and image file selections.
    """
    def __init__(self,LoadMRI,buttonsgui_3d,index):
        """
            Initialize the Registration object and perform rigid registration.
        """
        self.LoadMRI = LoadMRI

        filename = self.LoadMRI.movingimg_filename[index] #self.LoadMRI.combo_Regimgname.itemText(0)
        folder = f"{self.LoadMRI.session_path}/anat"

        file_part = self.LoadMRI.file_name[0].split("ind_")[1]  # e.g., '0-resampled100um.nii'
        number_str = ""
        for c in file_part:
            if c.isdigit():
                number_str += c
            else:
                break  # stop at first non-digit
        self.fixed_ind = int(number_str)
        self.moving_ind = int(filename.split("ind_")[1].split(".")[0])

        self.fixed_image = sITK.ReadImage(self.LoadMRI.file_name[0])
        self.moving_image = sITK.ReadImage(os.path.join(folder, filename))

        if len(self.moving_image.GetSize())==4:
            self.moving_image = self.get3Dimage(self.moving_image)

        coarest_options = [8,4,2,1]
        finest_options = [1,2,4]
        self.coarsest = coarest_options[self.LoadMRI.coarsest_index] #comboBox_coarsest
        self.finest = finest_options[self.LoadMRI.finest_index] #comboBox_finest
        self.rigid_transformation()

        buttonsgui_3d.popup.close()



    def get3Dimage(self,img):
        """
            Extract a single 3D volume from a 4D image.

            Parameters
            ----------
            img : SimpleITK.Image
                A 4D image where the last dimension represents time or frames.
        """
        t_index = 0
        size = list(img.GetSize())
        img3d = sITK.Extract(img, size[:3] + [0], [0, 0, 0, t_index])

        return img3d


    def rigid_transformation(self):
        """
            Perform rigid registration of the moving image to the fixed image.
            1. Rgid trasnformation with NMI
            2. Rigid trasnformation with MI (takes the 1. matrix as initialisation)
        """

        g = Greedy3D()

        m_CoarsestResolutionLevel = self.coarsest
        m_FinestResolutionLevel = self.finest
        iterations_per_level = 100 #100

        # Build the list
        iter_list = []
        for k in range(m_CoarsestResolutionLevel, m_FinestResolutionLevel - 1, -1):
            iter_list.append(str(iterations_per_level))  # or set different numbers per level
        # Join with 'x' to make Greedy string
        n_string = "x".join(iter_list)

        fixed = self.fixed_image
        moving = self.moving_image

        g.execute('-i my_fixed my_moving '
                  '-a -dof 6 -m NMI '
                  f'-n {n_string} '
                  '-V 0 ' #no verbose
                  '-o my_ncc',
                  my_fixed = fixed, my_moving = moving,
                  my_ncc=None)

        g.execute(
            '-i my_fixed my_moving '
            '-a -dof 6 -m MI '
            f'-n {n_string} '
            '-V 0 '
            f'-ia my_ncc '
            '-o my_rigid',
            my_fixed=fixed,
            my_moving=moving,
            my_rigid=None
        )

        mat_rigid = g['my_rigid']

        transform_filename = f"transformation_ind_{self.moving_ind}-to-ind_{self.fixed_ind}.txt"
        output_path = os.path.join(self.LoadMRI.session_path, "anat", transform_filename)

        np.set_printoptions(precision=12, suppress=False)

        RAS2LPS = np.diag([-1, -1, 1, 1])
        mat_end = RAS2LPS @ mat_rigid @ RAS2LPS

        with open(output_path, "w") as f:
            f.write("#Insight Transform File V1.0\n")
            f.write("#Transform 0\n")
            f.write("Transform: MatrixOffsetTransformBase_double_3_3\n")
            f.write("Parameters: ")

            # 9 rotation + 3 translation = 12 parameters
            np.savetxt(f, mat_end[:3, :3].reshape(1, 9), fmt="%.12f", newline=" ")
            f.write(" ")
            np.savetxt(f, mat_end[:3, 3].reshape(1, 3), fmt="%.12f", newline=" ")
            f.write("\nFixedParameters: 0 0 0\n")


        return


