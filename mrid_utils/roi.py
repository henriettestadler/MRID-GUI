import skimage
import numpy as np


def disk_roi(img, center, r):
    """
    Disk shaped mask
    """
    disk = skimage.morphology.disk(r)
    x, y = center
    mask = np.zeros_like(img)
    mask[x - r:x + r + 1, y - r:y + r + 1] = disk

    return mask


def sq_roi(img, center, pad=1):
    """
    Square shaped mask
    """
    x, y = center
    mask = np.zeros_like(img)
    mask[x - pad:x + pad + 1, y - pad:y + pad + 1] = 1

    return mask


def get_echo_vals(data, mask):
    """
    collects the pixel values at multiple echotimes within the masked area
    """
    num_echos = data.shape[-1]
    echoVals = np.zeros((num_echos, np.sum(mask).astype(int)))
    meanVals = np.zeros((num_echos,))
    stdVals = np.zeros((num_echos,))

    for echo in range(num_echos):
        img = data[:, :, echo]

        echoVals[echo, :] = np.ndarray.flatten(img[mask > 0])
        meanVals[echo] = np.mean(echoVals[echo, :])
        stdVals[echo] = np.std(echoVals[echo, :])

    return echoVals, meanVals, stdVals


def argmax_roi_basestruct(mask, basestructs, labelsdf, segmentation):
    """
    Finds the baseline anatomical structure of where the pixel is located, based on the argmax overlap area
    """
    overlap = 0
    argmax_value_overlap = 0
    argmax_name_overlap = ""
    for base in basestructs:
        base_seg_list = labelsdf["Labels"][labelsdf["Anatomical Regions"] == base]
        if base_seg_list.any():
            base_seg = base_seg_list.values[0]
            seg_mask = (segmentation == base_seg)
            if np.sum(mask * seg_mask) > overlap:
                overlap = np.sum(mask * seg_mask)
                argmax_value_overlap = base_seg
                argmax_name_overlap = base

    return argmax_value_overlap, argmax_name_overlap

