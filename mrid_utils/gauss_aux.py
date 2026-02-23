from mrid_utils import handlers
import os
import numpy as np
import scipy
from mrid_utils import com

def run_gaussian_analysis(filename, savepath, roi_name, orientation, data_volume, labelsdf, px_size=25, verbose=False):
    if px_size == 25:
        heatmap_warped_filename = ".".join((filename + "-" + roi_name + "-heatmap-warped", "nii", "gz"))
        hw_fullpath = os.path.join(savepath, heatmap_warped_filename)
        _, heatmap_warped = handlers.read_data(hw_fullpath)

        segmentation_filename = ".".join((filename + "-" + roi_name + "-heatmap-segmentation-warped", "nii", "gz"))
        sw_fullpath = os.path.join(savepath, segmentation_filename)
        _, segmentation_warped = handlers.read_data(sw_fullpath)

        heatmaps, ind = get_maxproj(heatmap_warped, segmentation_warped, roi_name, labelsdf, orientation=orientation)

        # Picking an image slice from the whole-volume brain image, purely for visualization
        if orientation == "coronal":
            fixed_img = data_volume[:, :, ind[2]]
        elif orientation == "sagittal":
            fixed_img = data_volume[ind[0], :, :]
        elif orientation == "axial":
            fixed_img = data_volume[:, ind[1], :]
    else:
        heatmap_filename = roi_name + "-" + orientation + "-heatmap_r=" + str(1) + "sqr.npy"
        # ".".join((filename+"-"+roi_name+"-heatmap", "nii", "gz"))
        heatmap_path = os.path.join(savepath, heatmap_filename)
        heatmaps = np.load(heatmap_path)
        fixed_img = data_volume[:, :, 0, 0]
        ind = [0, 0, 0]

    gaussian_centers, gaussAmp, gaussSig, popt = find_gaussian_centers(heatmaps, fixed_img,
                                                                       px_size, orientation, verbose)

    print("Gaussian centers", gaussian_centers)
    #make sure the folder exists
    os.makedirs(savepath,exist_ok=True)
    gausscent_filename = "gaussian_centers.npy"
    np.save(os.path.join(savepath, gausscent_filename), gaussian_centers)

    gausscent_filename = "gaussian_amplitudes.npy"
    np.save(os.path.join(savepath, gausscent_filename), gaussAmp)

    gausscent_filename = "gaussian_sigmas.npy"
    np.save(os.path.join(savepath, gausscent_filename), gaussSig)

    return gaussian_centers, heatmaps, ind


def get_maxproj(heatmap_resampled, segmentation_resampled, mrid, labelsdf, orientation):
    """
    Returns the maximum projection of the contrast heatmap volume in given orientation (i.e. axis)
    """
    if orientation == "coronal":
        axis = 2
    elif orientation == "sagittal":
        axis = 0
    elif orientation == "axial":
        axis = 1

    ionp_islands = labelsdf["Labels"][labelsdf["Anatomical Regions"].str.contains(mrid)]

    ind = np.unravel_index(np.argmax(heatmap_resampled, axis=None), heatmap_resampled.shape)
    template = np.max(heatmap_resampled, axis=axis)
    heatmaps = np.zeros((len(ionp_islands), np.shape(template)[0], np.shape(template)[1]))

    for i, island in enumerate(ionp_islands):
        heatmap_isolated = heatmap_resampled * (segmentation_resampled == island * 1)
        heatmaps[i, :, :] = np.max(heatmap_isolated, axis=axis)

    return heatmaps, ind


def find_gaussian_centers(heatmaps, img, px_size, orientation="coronal", verbose=False):
    """
    Fits a 2D Gaussian curve on each IONP island.
    heatmaps: relaxation heatmaps generated from raw MGE images, and resampled to space of interest.
                with size of num_ionp_islands-by-img_rows-by-img_colmns
    img: img to be plotted as base to the analysis
    px_size: size of each pixel
    verbose: boolean to print intermediate results

    Returns;
    The center of the best-fit 2D Gaussian curve, the amplitude and sigma components of the best-fit Gaussian curve
    gaussian_centers: np.array of gaussian center coordinates of each IONP island
    gaussAmp: Amplitude (i.e. contrast intensity) of best-fit gaussian curves
    gaussSig: Sigma component of best-fit gaussian curves along the implantation axis
    popt: best-fit parameters
    """

    num_rows = np.shape(heatmaps)[1]
    num_clms = np.shape(heatmaps)[2]

    y = np.linspace(0, num_rows - 1, num_rows)
    x = np.linspace(0, num_clms - 1, num_clms)
    x, y = np.meshgrid(x, y)

    num_ionp_islands, _, _ = np.shape(heatmaps)
    t2strength = np.zeros((num_ionp_islands,))
    gaussAmp = np.zeros((num_ionp_islands,))
    gaussSig = np.zeros((num_ionp_islands,))
    gaussian_centers = []

    for k in range(num_ionp_islands):
        i, j = np.unravel_index(np.argmax(heatmaps[k, :, :]), (num_rows, num_clms))
        z = heatmaps[k, :, :]
        initial_guess = (45, j, i, 2, 2, 0, 0)
        data_fitted, popt, pcov = fit_2d_gaussian((x, y), z, initial_guess)
        gaussian_centers.append(popt[1:3])
        gauss_x = np.round(popt[1]).astype(int)
        gauss_y = np.round(popt[2]).astype(int)

        t2strength[k] = z[gauss_y, gauss_x]
        gaussAmp[k] = popt[0]
        thetaDeg = (popt[5] % (2 * np.pi)) * 180 / np.pi

        if orientation == "coronal":
            if (45 < thetaDeg < 135) or (225 < thetaDeg < 315):
                gaussSig[k] = popt[4]
            else:
                gaussSig[k] = popt[3]

        elif orientation == "sagittal":
            if (45 < thetaDeg < 135) or (225 < thetaDeg < 315):
                gaussSig[k] = popt[3]
            else:
                gaussSig[k] = popt[4]

        #  VERBOSE
        if verbose:
            print("Shape of the heatmaps data: ")
            print(np.shape(heatmaps))
            print("theta(radians): " + str(popt[5]))
            print("theta: " + str(thetaDeg))
            print("Fitted Gaussian x: ")
            print(gauss_x)
            print("Fitted Gaussian y: ")
            print(gauss_y)
            print(popt[1:3])
            print("sigma: " + str(popt[3:5]))
            print("Legth_sigma: " + str(gaussSig[k]))
            print("len: " + str(gaussSig[k] * 2 * px_size))
            print("amp: " + str(popt[0]))

    gaussian_centers = np.array(gaussian_centers)

    return gaussian_centers, gaussAmp, gaussSig, popt


def twoD_Gaussian(xy, amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
    x, y = xy
    xo = float(xo)
    yo = float(yo)
    a = (np.cos(theta) ** 2) / (2 * sigma_x ** 2) + (np.sin(theta) ** 2) / (2 * sigma_y ** 2)
    b = -(np.sin(2 * theta)) / (4 * sigma_x ** 2) + (np.sin(2 * theta)) / (4 * sigma_y ** 2)
    c = (np.sin(theta) ** 2) / (2 * sigma_x ** 2) + (np.cos(theta) ** 2) / (2 * sigma_y ** 2)
    g = offset + amplitude * np.exp(- (a * ((x - xo) ** 2) + 2 * b * (x - xo) * (y - yo)
                                       + c * ((y - yo) ** 2)))
    return g.ravel()


def fit_2d_gaussian(xy, data, initial_guess):
    x, y = xy
    popt, pcov = scipy.optimize.curve_fit(twoD_Gaussian, (x, y), data.ravel(), p0=initial_guess)
    data_fitted = twoD_Gaussian((x, y), *popt)

    return data_fitted, popt, pcov


def combine_gauss_centers_3D(gaussian_centers_coronal, contrast_intensities_coronal,
                              gaussian_centers_sagittal=np.array([]), contrast_intensities_sagittal=np.array([]),
                              gaussian_centers_axial=np.array([]), contrast_intensities_axial=np.array([]),
                                savepath=None):
    """
    Computes a weighted average of all existing Gaussian best-fit curve centers
    (i.e. in different imaging orientations such as coronal and axial).

    """

    num_patterns = 0

    if gaussian_centers_coronal.any():
        num_patterns = len(gaussian_centers_coronal)
        if contrast_intensities_coronal.any():
            coronal_weights = contrast_intensities_coronal
        else:
            coronal_weights = np.ones((num_patterns,))
    else:
        coronal_weights = 0

    if gaussian_centers_sagittal.any():
        num_patterns = len(gaussian_centers_sagittal)
        if contrast_intensities_sagittal.any():
            sagittal_weights = contrast_intensities_sagittal
        else:
            sagittal_weights = np.ones((num_patterns,))
    else:
        sagittal_weights = 0

    if gaussian_centers_axial.any():
        num_patterns = len(gaussian_centers_axial)
        if contrast_intensities_axial.any():
            axial_weights = contrast_intensities_axial
        else:
            axial_weights = np.ones((num_patterns,))
    else:
        axial_weights = 0

    gaussian_centers = np.zeros((num_patterns, 3))

    #  Weighted average of gaussian curve centers
    if gaussian_centers_coronal.any():
        gaussian_centers[:, 0] = gaussian_centers_coronal[:, 1] * coronal_weights
        gaussian_centers[:, 1] = gaussian_centers_coronal[:, 0] * coronal_weights
    if gaussian_centers_sagittal.any():
        gaussian_centers[:, 2] = gaussian_centers_sagittal[:, 0] * sagittal_weights
        gaussian_centers[:, 1] = (gaussian_centers[:, 1] + gaussian_centers_sagittal[:, 1] * sagittal_weights)
    if gaussian_centers_axial.any():
        gaussian_centers[:, 2] = (gaussian_centers[:, 2] + gaussian_centers_axial[:, 0] * axial_weights)
        gaussian_centers[:, 0] = (gaussian_centers[:, 0] + gaussian_centers_axial[:, 1] * axial_weights)

    if gaussian_centers[:, 0].any():
        gaussian_centers[:, 0] = gaussian_centers[:, 0] / (axial_weights + coronal_weights)
    if gaussian_centers[:, 1].any():
        gaussian_centers[:, 1] = gaussian_centers[:, 1] / (sagittal_weights + coronal_weights)
    if gaussian_centers[:, 2].any():
        gaussian_centers[:, 2] = gaussian_centers[:, 2] / (sagittal_weights + axial_weights)

    print("gaussian centers: ",gaussian_centers)
    if savepath:
        filename = "gaussian_centers_3D.npy"
        np.save(os.path.join(savepath, filename), gaussian_centers)

    return gaussian_centers


def get_centomass(mrid_wafer_dimensions, intersegment_lengths):
    """
    mrid_wafer_dimensions: dimension vector of each pattern in mrid (num_patterns-by-3), dorsal-to-ventral, each row represents b,a,h; a=0 for triangular patterns
    intersegment_lengths: inter-pattern(segment) lengths starting from dorsal to ventral patterns
    """
    num_patterns=len(mrid_wafer_dimensions)
    c2c=np.zeros((num_patterns-1,))

    bundle_l=0
    ticks=[bundle_l]
    for i in range(num_patterns-1):
        b,a,h=mrid_wafer_dimensions[i,:]
        b2,a2,h2=mrid_wafer_dimensions[i+1,:]

        if a>0:
            cy=com.get_cy_trapezoid(b,a,h)
        else:
            cy=com.get_cy_triangle(h)

        bundle_l=bundle_l+cy
        ticks.append(bundle_l)

        distCy=h-cy
        bundle_l=bundle_l+distCy
        ticks.append(bundle_l)

        bundle_l=bundle_l+intersegment_lengths[i]
        ticks.append(bundle_l)

        if a2>0:
            cy2=com.get_cy_trapezoid(b2,a2,h2)
#             distCy2=cy2
        else:
            cy2=com.get_cy_triangle(h2)
#             distCy2=cy2
        c2c[i]=distCy + intersegment_lengths[i] + cy2

    b,a,h=mrid_wafer_dimensions[-1,:]
    if a>0:
        cy=com.get_cy_trapezoid(b,a,h)
    else:
        cy=com.get_cy_triangle(h)

    bundle_l=bundle_l+cy
    ticks.append(bundle_l)

    distCy=h-cy
    bundle_l=bundle_l+distCy
    ticks.append(bundle_l)

    return c2c, ticks
