import numpy as np
import os
from mrid_utils import handlers,roi
import scipy

def get_relaxation_unsupervised(filename_data, sessionpath, basestructs, slice_orientation, te=[4.0, 4.09], r=1, savepath=""):
    """
    Calculates the MRID contrast heatmap unsupervised, using only the anat regions data.
    filename_data: str, the filename of 4D t2*MGE image (without .nii.gz extension)
    sessionpath: mri session path str where the data is stored.
    basestructs: list of str, to define the baseline anatomical structure names
    te: [te_0, te_spacing]
    r: integer, radius of sliding window
    savepath: directory to save plots.

    Returns and saves;
    heatmaps: np.array with size (num_of_ionp_islands x data.shape[0] x data.shape[1]), that contains MRID contrast heatmap
    heatmap_nii: np.array with same size as segmentation to be saved as nii.gz file.
    img_slice: img_slice along 3rd dimension of data where MRID of interest is visible.
    """
    nii_data, data, anat, labelsdf = handlers.get_anat_data(sessionpath, filename_data)
    heatmap_nii = np.zeros_like(anat)
    nonzero_mask = anat != 0
    nonzero_slices = np.unique(np.where(nonzero_mask)[-1])

    #baseline_std = np.zeros((len(basestructs),))
    heatmaps = np.zeros((len(basestructs), 1, anat.shape[0], anat.shape[1]))
    roi_index = 0 #anatomical regions start at 1
    for j, roi_baseline in enumerate(basestructs):
        roi_index += 1 #labelsdf["Labels"][labelsdf["Anatomical Regions"].str.contains(roi_baseline)]
        img_slice = [s for s in nonzero_slices if np.any(anat[:, :, s] == roi_index)][0]
        heatmaps[0] = segment_relaxation(data[:, :, img_slice, :], anat[:, :, img_slice], anat[:, :, img_slice], basestructs, labelsdf, roi_index, te, r=r,unsupervised=True)
        heatmap_nii[:, :, img_slice] = heatmap_nii[:, :, img_slice] + heatmaps[0]

    return heatmaps, heatmap_nii, img_slice



def get_relaxation(filename_data, mrid_names, sessionpath, basestructs, slice_orientation, te=[4.0, 4.09], r=1, savepath=""):
    """
    Calculates the MRID contrast heatmap.
    filename_data: str, the filename of 4D t2*MGE image (without .nii.gz extension)
    sessionpath: mri session path str where the data is stored.
    basestructs: list of str, to define the baseline anatomical structure names
    mrid_name: str, that defines the MRID
    te: [te_0, te_spacing]
    r: integer, radius of sliding window
    savepath: directory to save plots.

    Returns and saves;
    heatmaps: np.array with size (num_of_ionp_islands x data.shape[0] x data.shape[1]), that contains MRID contrast heatmap
    heatmap_nii: np.array with same size as segmentation to be saved as nii.gz file.
    img_slice: img_slice along 3rd dimension of data where MRID of interest is visible.
    """

    nii_data, data, segmentation, anat, labelsdf = handlers.get_segmentation_data(sessionpath, filename_data)
    segmentation = np.maximum(segmentation, anat)
    heatmap_nii = np.zeros_like(anat)

    for mrid_name in mrid_names:
        ionp_islands = labelsdf["Labels"][labelsdf["Anatomical Regions"].str.contains(mrid_name)]
        heatmaps = np.zeros((len(ionp_islands), segmentation.shape[0], segmentation.shape[1]))

        for i, roi_index in enumerate(ionp_islands):
            print(roi_index)
            img_slice = np.unique(np.where(segmentation == roi_index)[-1])[0]
            heatmaps[i] = segment_relaxation(data[:, :, img_slice, :],
                                             segmentation[:, :, img_slice],
                                             anat[:, :, img_slice],
                                             basestructs, labelsdf, roi_index, te, r=r, savepath=savepath)
            heatmap_nii[:, :, img_slice] = heatmap_nii[:, :, img_slice] + heatmaps[i]


    # Saving MRID contrast heatmaps as nii.gz files.
    new_heatmap_filename = filename_data + "-" + mrid_name + "-heatmap.nii.gz"
    handlers.save_nii(heatmap_nii, nii_data.affine, os.path.join(savepath, new_heatmap_filename))

    filename = filename_data + "-" + mrid_name + "-" + "-heatmap.npy"
    np.save(os.path.join(savepath, filename), heatmaps)

    return heatmaps, heatmap_nii, img_slice

def get_relaxation_simultaneously(filename_data, roi_index, sessionpath, basestructs, slice_orientation, segmentation, te=[4.0, 4.09], r=1, savepath=""):
    """
    Calculates the MRID contrast heatmap directly while still painting the MRID tags.
    filename_data: str, the filename of 4D t2*MGE image (without .nii.gz extension)
    sessionpath: mri session path str where the data is stored.
    basestructs: list of str, to define the baseline anatomical structure names
    roi_index: index of roi which was just painted
    te: [te_0, te_spacing]
    r: integer, radius of sliding window
    savepath: directory to save plots.

    Returns and saves;
    heatmaps: np.array with size (num_of_ionp_islands x data.shape[0] x data.shape[1]), that contains MRID contrast heatmap
    heatmap_nii: np.array with same size as segmentation to be saved as nii.gz file.
    img_slice: img_slice along 3rd dimension of data where MRID of interest is visible.
    """

    nii_data, data, anat, labelsdf = handlers.get_anat_data(sessionpath, filename_data)
    heatmap_nii = np.zeros_like(anat)

    heatmap = np.zeros((anat.shape[0], anat.shape[1]))

    #if no voxel is painted in roi_index
    if np.unique(np.where(segmentation == roi_index)).size == 0:
        return heatmap, heatmap_nii, 0

    img_slice = np.unique(np.where(segmentation == roi_index))[0]
    heatmap = segment_relaxation(data[:, :, img_slice, :],
                                 segmentation[img_slice,:, :].T,
                                 anat[:, :, img_slice],
                                 basestructs, labelsdf, roi_index, te, r=r, savepath=savepath)
    heatmap_nii[:, :, img_slice] = heatmap_nii[:, :, img_slice] + heatmap

    return heatmap, heatmap_nii, img_slice


def segment_relaxation(data, segmentation, anat, basestructs, labelsdf, roi_index, te, r=2, savepath="", unsupervised=False):
    num_echos = data.shape[-1]
    heatmap = np.zeros_like(segmentation)

    te0, te_spacing = te
    echos = np.arange(te0, np.ceil(te0 + (num_echos - 1) * te_spacing), te_spacing)
    indices = np.array(list(zip(*np.where(segmentation == roi_index))))

    for index in indices:
        if r > 1:
            mask = roi.disk_roi(segmentation, index, r=r)
        else:
            mask = roi.sq_roi(segmentation, index)
        base_seg, struct = roi.argmax_roi_basestruct(mask, basestructs, labelsdf, anat)
        baseline = get_baseline_vals(base_seg, segmentation, data)
        if np.sum(mask * (anat == base_seg)) > 2:
            mask = mask * (anat == base_seg)
        _, meanVals, stdVals = roi.get_echo_vals(data, mask)

        try:
            paramsBase, paramsData, _, _ = fit_relaxation(meanVals, stdVals, baseline, echos)

            relaxivity_base = 1000 / paramsBase[1]
            relaxivity_roi = 1000 / paramsData[1]
            diff = relaxivity_roi - relaxivity_base
        except:
            diff = 0.1
        if diff < 0:
            diff = 0

        heatmap[index[0], index[1]] = abs(diff)

    return heatmap


def fit_relaxation(meanVals, stdVals, baseline, echos, p0=(50, 30, 0)):
    """
    Calculates the contrast intensity by fitting an exponential decay to mean relaxation values from sliding window (region of interest) and
    baseline anatomical structure.
    """
    paramsBaseline, cvBase = scipy.optimize.curve_fit(exp_decay, echos, np.mean(baseline, axis=0), p0,
                                                  np.std(baseline, axis=0),
                                                  bounds=([-np.inf, -np.inf, 0], [np.inf, np.inf, np.inf]))
    Cbase, t2Base, Abase = paramsBaseline
    p_sigma_base = np.sqrt(np.diag(cvBase))

    if Abase > np.std(baseline, axis=0)[-1]:
        Alower = Abase - np.std(baseline, axis=0)[-1]
    else:
        Alower = 0
    Aupper = Abase + np.std(baseline, axis=0)[-1]

    paramsData, cvData = scipy.optimize.curve_fit(exp_decay, echos, meanVals, paramsBaseline, stdVals, bounds=(
    [Cbase - np.std(baseline, axis=0)[0], -np.inf, Alower], [Cbase + np.std(baseline, axis=0)[0], np.inf, Aupper]))
    Celec, t2elec, Aelec = paramsData
    p_sigma_data = np.sqrt(np.diag(cvData))

    return paramsBaseline, paramsData, p_sigma_base, p_sigma_data

def exp_decay(x, C, t2, A):
    return C * np.exp(-x/t2) + A


def get_baseline_vals(seg, segmentationArr, data):
    """
    img_s: image slice to be analysed
    seg: segmentation id of baseline
    segmentationArr: segmentation np array
    data: mri raw np array

    returns;
    baseline: pixel values for baseline area nparray (len(vals), len(echos))
    """
    #     segmentation=segmentationArr[:,:,img_s]
    if len(data.shape) == 3:
        num_echos = data.shape[-1]
    else:
        num_echos = 0

    if num_echos > 0:
        for echo in range(num_echos):
            #         img=data[:,:,img_s,echo]
            img = data[:, :, echo]
            vals = img[segmentationArr == seg]

            if echo == 0:
                baseline = np.zeros((len(vals), num_echos))
                baseline[:, 0] = vals
            else:
                baseline[:, echo] = vals
    else:
        baseline = data[segmentationArr == seg]

    return baseline
