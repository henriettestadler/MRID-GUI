import os
import nibabel as nib
import pandas as pd
import numpy as np
from mrid_utils import com


def get_anat_data(sessionpath, filename_data):
    """
    Gets the raw data together with MRID anatomical segmentation
    filename_data: filename of the raw T2*Map MGE data
    img_slice: image slice of interest

    returns;
    data: 4D T2*MGE data np.array
    anat: np.array for anatomical segmentation
    labelsdf: pandas.df, metadata for segmentation

    """
    anatpath = os.path.join(sessionpath, "anat")
    filename_data_full = ".".join((filename_data, "nii", "gz"))
    filename_anat = ".".join((filename_data + "-anat", "nii", "gz"))

    nii_data, data = read_data(os.path.join(anatpath, filename_data_full))
    _, anat = read_data(os.path.join(anatpath, filename_anat))

    labelsdf = read_labels(os.path.join(sessionpath, "anat", "labels.txt"))

    print("Data shape of anatomy segmentation" + str(np.shape(anat)))
    print("Data shape of MRI data" + str(np.shape(data)))

    return nii_data, data, anat, labelsdf

def get_segmentation_data(sessionpath, filename_data):
    """
    Gets the raw data together with MRID segmentation segmentation
    filename_data: filename of the raw T2*Map MGE data
    img_slice: image slice of interest

    returns;
    data: 4D T2*MGE data np.array
    segmentation: np.array for IONP island segmentation
    labelsdf: pandas.df, metadata for segmentation

    """
    anatpath = os.path.join(sessionpath, "anat")
    filename_data_full = ".".join((filename_data, "nii", "gz"))
    filename_segmentation = ".".join((filename_data + "-segmentation", "nii", "gz"))
    filename_anat = ".".join((filename_data + "-anat", "nii", "gz"))

    nii_data, data = read_data(os.path.join(anatpath, filename_data_full))
    _, segmentation = read_data(os.path.join(anatpath, filename_segmentation))
    _, anat = read_data(os.path.join(anatpath, filename_anat))

    labelsdf = read_labels(os.path.join(sessionpath, "anat", "labels.txt"))

    #print("Data shape of MRI data" + str(np.shape(data)))
    #print("Data shape of MRID segmentation" + str(np.shape(segmentation)))

    return nii_data, data, segmentation, anat, labelsdf

def read_data(path):
    """
    Reads data from nii.gz file
    inputs;
    path: path to the file
    returns;
    nii: nii object
    data: mri volume as np array
    """
    nii = nib.load(path)
    data = np.asanyarray(nii.dataobj)

    return nii, data

def save_nii(data, affine, path2save, header=None):
    nii2save=nib.Nifti1Image(data, affine, header=header)
    nib.save(nii2save, path2save)

def read_labels(labels_path):
    """
    Reading SimpleITK-Snap generated labels
    """
    labels = []
    anats = []
    with open(labels_path) as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if i > 14:
                if i == 7:
                    anat = ' '.join(line.split('\\cf')[1].split()[8:])
                    anats.append(anat.split("\"")[1])
                    labels.append(int(line.split('\\cf')[1].split()[0]))
                else:
                    anat = ' '.join(line.split()[7:])
                    anats.append(anat.split("\"")[1])
                    labels.append(int(line.split()[0]))

    df = pd.DataFrame()
    df["Labels"] = labels
    df["Anatomical Regions"] = anats
    return df

def find_resampled_img(ind, path):
    """
    Finds the 25um isovoxel resampled whole-volume image
    """
    filename = find_ind_data(ind, path)
    #print(ind, path, filename)
    filename = ".".join(((filename[0].split(".")[0]+"_resampled", "nii", "gz")))
    #print("Fixed image for the warping: "+filename)
    return filename

def find_ind_data(ind,path):
    filename=[f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) and ind+".nii.gz" in f]
    return filename

def get_gaussian_centers(sessionpath, mrid):
    analysedpath = os.path.join(sessionpath, "analysed")
    if os.path.exists(analysedpath):
        mridpath = os.path.join(analysedpath, mrid)

        # Coronal gaussian centers
        orient = "coronal"
        orientpath = os.path.join(mridpath, orient)
        if os.path.exists(orientpath):
            gaussian_centers_coronal = np.load(os.path.join(orientpath, "gaussian_centers.npy"))
            gaussian_sigmas_coronal = np.load(os.path.join(orientpath, "gaussian_sigmas.npy"))

            #print("Coronal sliced gaussian centers exist: ")
            #print(gaussian_centers_coronal)
            try:
                contrast_intensities_coronal = np.load(
                    os.path.join(orientpath, "contrast_intensities_fixedROI.npy"))
                #print("Coronal contrast intensities: ")
                #print(contrast_intensities_coronal)
            except:
                #print("No fixed ROI contrast intensity available for Coronal slice: ")
                contrast_intensities_coronal = np.array([])
        else:
            gaussian_centers_coronal = []
            gaussian_sigmas_coronal = []

        # Sagittal gaussian centers
        orient = "sagittal"
        orientpath = os.path.join(mridpath, orient)
        if os.path.exists(orientpath):
            gaussian_centers_sagittal = np.load(os.path.join(orientpath, "gaussian_centers.npy"))
            gaussian_sigmas_sagittal = np.load(os.path.join(orientpath, "gaussian_sigmas.npy"))

            #print("Sagittal sliced gaussian centers exist: ")
            #print(gaussian_centers_sagittal)
            try:
                contrast_intensities_sagittal = np.load(
                    os.path.join(orientpath, "contrast_intensities_fixedROI.npy"))
                #print("Sagittal contrast intensities: ")
                #print(contrast_intensities_sagittal)
            except:
                #print("No fixed ROI contrast intensity available for Coronal slice: ")
                contrast_intensities_sagittal = np.array([])
        else: #MAYBE DELETE
            gaussian_centers_sagittal = np.array([])
            gaussian_sigmas_sagittal = np.array([])
            contrast_intensities_sagittal = np.array([])

        # Axial gaussian centers
        orient = "axial"
        orientpath = os.path.join(mridpath, orient)
        if os.path.exists(orientpath):
            gaussian_centers_axial = np.load(os.path.join(orientpath, "gaussian_centers.npy"))
            #print("Axially sliced gaussian centers exist: ")
            #print(gaussian_centers_axial)
            try:
                contrast_intensities_axial = np.load(
                    os.path.join(orientpath, "contrast_intensities_fixedROI.npy"))
            except:
                contrast_intensities_axial = np.array([])
        else:
            gaussian_centers_axial = np.array([])
            gaussian_sigmas_axial = np.array([])
            contrast_intensities_axial = np.array([])

    return gaussian_centers_coronal, contrast_intensities_coronal, \
        gaussian_centers_sagittal, contrast_intensities_sagittal, \
        gaussian_centers_axial, contrast_intensities_axial,\
        gaussian_sigmas_coronal, gaussian_sigmas_sagittal


def get_mrid_dimensions(mrid_dict, bundle_start):
    pattern_dimensions = mrid_dict["dimensions"][bundle_start:, :]
    pattern_intersegment = mrid_dict["intersegment_distances"][bundle_start:]
    ionp_amount = mrid_dict["ionp_amount"][bundle_start:]
    pattern_lengths = pattern_dimensions[:, -1]
    pattern_dist, pattern_points = com.get_centomass(pattern_dimensions, pattern_intersegment)

    return pattern_dist, pattern_points, pattern_lengths, ionp_amount
