import numpy as np
from mrid_utils import com

def gen_barcode_mrid(patternLengths, c2c_dists, barcode_length=4500):
    '''
    Generates the MRID-barcode
    Takes input as;
    patternLengths: length of bars in barcode
    c2c_dists: Center-to-center distances of each bar in barcode
    barcode_length: (default 4500), arbitrary length for barcode. 1 index == 1 micrometer
    Returns;
    barcode: reconstructed barcode array
    ticks: ticks showing the location of each bar in barcode
    tickLabels: labels array for ticks
    '''
    barcode = np.ones((1000, barcode_length))

    a = np.sum(c2c_dists)
    b = patternLengths[-1] / 2
    c = patternLengths[0] / 2
    l = int(barcode_length - (a + b + c))
    ticks = [l]

    for i, bar in enumerate(patternLengths):
        if i == 0:
            barInt = np.round(bar).astype(int)
            barcode[:, l:l + barInt] = 0
            ticks.append(l + barInt / 2)
            ticks.append(l + barInt)
            l = l + np.round(bar / 2).astype(int) + np.round(c2c_dists[i]).astype(int)
        else:
            barInt = np.round(bar / 2).astype(int)
            barcode[:, l - barInt:l + barInt] = 0
            ticks.append(int(l - barInt))
            ticks.append(l)
            ticks.append(l + barInt)
            if i < len(c2c_dists):
                l = l + np.round(c2c_dists[i]).astype(int)

    ticks = np.array(ticks)
    tickLabels = (ticks - int(barcode_length - (a + b + c))).astype(int)

    return barcode, ticks, tickLabels

def barcode_probability(ref_barcodes, test_array, mrid_dict, sigma=None):
    """
    Compute similarity probabilities between reconstructed MRI-barcode and reference MRI-barcodes from designs
    using Manhattan distance based similarities and Gaussian weighting.
    If sigma is not provided, it is estimated from pairwise distances among reference arrays.

    Parameters
    ----------
    reference_arrays : list or array-like
        List of 1D numpy arrays (all same length).
    test_array : np.ndarray
        1D numpy array of same length as reference arrays.
    sigma : float, optional
        Spread parameter controlling how sharply probabilities decay with distance.
        If None, sigma is estimated from the spread of reference arrays.

    Returns
    -------
    probs : np.ndarray
        Probabilities indicating similarity of test_array to each reference array.
    similarities : np.ndarray
        Raw normalized similarities test_array and each reference array.
    sigma : float
        The sigma value used (estimated or provided).
    """
    reference_arrays = []
    for mrid in ref_barcodes:
        c2c = com.get_centomass(mrid_dict[mrid]["dimensions"], mrid_dict[mrid]["intersegment_distances"])[0]
        barcode, _, _ = gen_barcode_mrid(mrid_dict[mrid]["dimensions"][:, -1], c2c)
        reference_arrays.append(barcode[0, :])

    reference_arrays = np.array(reference_arrays)
    n_refs = len(reference_arrays)

    # --- Estimate sigma from reference arrays if not provided ---
    if sigma is None:
        # Compute all pairwise normalized Manhattan distances between reference arrays
        dists = []
        for i in range(n_refs):
            for j in range(i + 1, n_refs):
                # d = np.linalg.norm(reference_arrays[i] - reference_arrays[j])
                d = np.sum(reference_arrays[i] == reference_arrays[j]) / len(reference_arrays[i])
                dists.append(d)
        dists = np.array(dists)

        sigma = np.std(dists)

    # --- Compute squared distances between test and reference arrays ---
    # squared_distances = np.array([np.sum((ref - test_array) ** 2) for ref in reference_arrays])
    similarities = np.array([np.sum(ref == test_array) / len(test_array) for ref in reference_arrays])

    # --- Gaussian weighting ---
    weights = np.exp(similarities / (2 * sigma ** 2))
    probs = weights / np.sum(weights)

    return probs, similarities, sigma
