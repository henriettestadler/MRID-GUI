import numpy as np
import os
import handlers
import scipy
import roi

def get_relaxation(filename_data, mrid_name, sessionpath, basestructs, te, slice_orientation, r=1, unsupervised=False, savepath=""):
    """
    Calculates the MRID contrast heatmap.
    filename_data: str, the filename of 4D t2*MGE image (without .nii.gz extension)
    sessionpath: mri session path str where the data is stored.
    basestructs: list of str, to define the baseline anatomical structure names
    mrid_name: str, that defines the MRID
    te: [te_0, te_spacing]
    r: integer, radius of sliding window
    unsupervised: boolean flag for unsupervised MRID heatmap analysis
    savepath: directory to save plots.

    Returns and saves;
    heatmaps: np.array with size (num_of_ionp_islands x data.shape[0] x data.shape[1]), that contains MRID contrast heatmap
    heatmap_nii: np.array with same size as segmentation to be saved as nii.gz file.
    img_slice: img_slice along 3rd dimension of data where MRID of interest is visible.
    """

    nii_data, data, segmentation, anat, labelsdf = handlers.get_data(sessionpath, filename_data)

    heatmap_nii = np.zeros_like(segmentation)

    if unsupervised:
        baseline_std = np.zeros((len(basestructs),))
        heatmaps = np.zeros((len(basestructs), 1, segmentation.shape[0], segmentation.shape[1]))
        for j, roi_baseline in enumerate(basestructs):
            roi_areas = labelsdf["Labels"][labelsdf["Anatomical Regions"].str.contains(roi_baseline)]
            roi = roi_baseline
            for i, roi in enumerate(roi_areas):
                heatmaps[j, i, :, :] = segment_relaxation(data, anat, anat, basestructs, labelsdf, roi, te, r=r)

    else:
        ionp_islands = labelsdf["Labels"][labelsdf["Anatomical Regions"].str.contains(mrid_name)]
        heatmaps = np.zeros((len(ionp_islands), segmentation.shape[0], segmentation.shape[1]))

        for i, roi in enumerate(ionp_islands):
            img_slice = np.unique(np.where(segmentation == roi)[-1])[0]
            heatmaps[i] = segment_relaxation(data[:, :, img_slice, :],
                                             segmentation[:, :, img_slice],
                                             anat[:, :, img_slice],
                                             basestructs, labelsdf, roi, te, r=r, savepath=savepath)
            heatmap_nii[:, :, img_slice] = heatmap_nii[:, :, img_slice] + heatmaps[i]


    filename = mrid_name + "-" + slice_orientation + "-heatmap.npy"
    np.save(os.path.join(savepath, filename), heatmaps)

    new_heatmap_filename = filename_data + "-" + mrid_name + "-heatmap.nii.gz"

    # Saving MRID contrast heatmaps as nii.gz files.
    handlers.save_nii(heatmap_nii, nii_data.affine, os.path.join(savepath, new_heatmap_filename))

    return heatmaps, heatmap_nii, img_slice


def segment_relaxation(data, segmentation, anat, basestructs, labelsdf, roi, te, r=2, savepath=""):
    num_echos = data.shape[-1]
    heatmap = np.zeros_like(segmentation)

    for index in np.array(list(zip(*np.where(segmentation == roi)))):
        # meanVals = np.zeros((num_echos,))
        # stdVals = np.zeros((num_echos,))

        if r > 1:
            mask = roi.disk_roi(segmentation, index, r=r)
        else:
            mask = roi.sq_roi(segmentation, index)

        base_seg, struct = roi.argmax_roi_basestruct(mask, basestructs, labelsdf, anat)
        baseline = get_baseline_vals(base_seg, segmentation, data)
        if np.sum(mask * (anat == base_seg)) > 2:
            mask = mask * (anat == base_seg)

        _, meanVals, stdVals = roi.get_echo_vals(data, mask)

        te0, te_spacing = te
        echos = np.arange(te0, np.ceil(te0 + (num_echos - 1) * te_spacing), te_spacing)

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

        # if savepath:
        #     if not os.path.exists(os.path.join(savepath, "Relaxation Curves")):
        #         os.mkdir(os.path.join(savepath, "Relaxation Curves"))
        #
        #     Cbase, t2Base, Abase = paramsBase
        #     Celec, t2elec, Aelec = paramsData
        #     plt.figure()
        #     # plt.title()
        #     plt.errorbar(echos, meanVals, yerr=stdVals, fmt='o', color="blue")
        #     plt.plot(np.linspace(0, 40, 9), monoExp(np.linspace(0, 40, 9), Celec, t2elec, Aelec), color="blue",
        #              linewidth=3)
        #     plt.axvline(x=paramsData[1], color='blue', linestyle='--', linewidth=2)
        #
        #     plt.errorbar(echos, np.mean(baseline, axis=0), yerr=np.std(baseline, axis=0), fmt='o', color="red")
        #     plt.plot(np.linspace(0, 40, 9), monoExp(np.linspace(0, 40, 9), Cbase, t2Base, Abase), color="red",
        #              linewidth=3)
        #     plt.axvline(x=paramsBase[1], color='red', linestyle='--', linewidth=2)
        #
        #     plt.ylabel("Signal a.u.")
        #     plt.xlabel("Time (ms)")
        #     plt.legend(["Electrode echo", "Electrode Decay"])
        #     figname = f"index_{index}_contrast_{diff}-relaxation_curve.pdf"
        #     plt.savefig(os.path.join(savepath, "Relaxation Curves", figname), dpi=1000)
        #
        #     plt.figure()
        #     plt.imshow(data[:, :, 0], cmap='gray', interpolation='nearest')
        #     plt.scatter(index[1], index[0], s=1, c="r", edgecolors='none')
        #     figname = f"index_{index}_contrast_{diff}-image.pdf"
        #     plt.savefig(os.path.join(savepath, "Relaxation Curves", figname), dpi=1000)
        #     # plt.show()
        #     plt.close('all')

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






