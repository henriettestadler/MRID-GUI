import os
import nibabel as nib
import pandas as pd
import numpy as np

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

    print("Data shape of MRI data" + str(np.shape(data)))
    print("Data shape of MRID segmentation" + str(np.shape(segmentation)))

    #print("Voxel dimensions: " + str(nii_data.header['pixdim']))
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
