from mrid_utils import handlers
import numpy as np
import math
#import plotly.graph_objects as go
from scipy.optimize import minimize
import channel_mapper

# TODO: Henriette, you can incorporate this main function into your pipeline as you wish. I am only putting it here to show you the flow
def main(mrid, savepath, sessionpath, root, weighted_loss_f="density", bundle_start=0, map_channels_boolean=True):
    """
    Localizes the electrode channels. Takes input;
    filename:
    mrid:
    savepath:
    sessionpath:
    transformation:


    """
    # Pickle file that contains all the design parameters of each MRID tag
    with open(os.path.join(root, 'mrid_library.pkl'), 'rb') as f:
        mrid_dict = pickle.load(f)

    gaussian_centers_coronal, contrast_intensities_coronal, \
    gaussian_centers_sagittal, contrast_intensities_sagittal, \
    gaussian_centers_axial, contrast_intensities_axial, \
    gaussian_sigmas_coronal, gaussian_sigmas_sagittal = handlers.get_gaussian_centers(sessionpath, mrid)

    gaussian_centers_3d = gauss_aux.combine_gauss_centers_3D(gaussian_centers_coronal,
                                                    contrast_intensities_coronal,
                                                    gaussian_centers_sagittal,
                                                    contrast_intensities_sagittal,
                                                    gaussian_centers_axial,
                                                    contrast_intensities_axial,
                                                    savepath)

    fitted_points = register_bundle(gaussian_centers_3d, mrid_dict[mrid], bundle_start, weighted_loss_f=weighted_loss_f,
                                           visualization=True)
    if map_channels_boolean:
        # Mapping the channels to physical coordinate indeces (integers) in MRI space
        ch_coords = channel_mapper.map_electrodes_main(fitted_points, mrid_dict[mrid])
        np.save(os.path.join(sessionpath, "channel_mri_coordinates.npy"), ch_coords[0])

        moving_idx_filename = "moving_img_resampled25um-indeces.npy"
        fixed_idx_filename = "fixed_img-indeces.npy"
        moving_idx_path = os.path.join(sessionpath, "registration", moving_idx_filename)
        fixed_idx_path = os.path.join(sessionpath, "registration", fixed_idx_filename)
        print("Loading the moving coordinates: " + moving_idx_path)
        print("Loading the fixed coordinates: " + fixed_idx_path)
        moving_coordinates = np.load(moving_idx_path)
        fixed_coordinates = np.load(fixed_idx_path)

        # Mapping the channel coordinates to the Atlas space
        dwi1Dsignal = channel_mapper.map_channels_to_atlas(ch_coords, moving_coordinates, fixed_coordinates, savepath=mridpath)
        np.save(os.path.join(sessionpath, "dwi_1D_cross_section_pixel_values.npy"), dwi1Dsignal)

    return


def register_bundle(gaussian_centers_3d, mrid_dict, bundle_start, weighted_loss_f, visualization=False):
    # gaussian_centers_3d = np.load(os.path.join(analysedpath, mrid_type, "3D-gaussian-centers-mrid.npy"))
    mrid_design_dist, mrid_design_points, pattern_lengths, ionp_amount = handlers.get_mrid_dimensions(mrid_dict, bundle_start)
    loss_f_weights = np.ones_like(pattern_lengths)

    if weighted_loss_f == "density":
        loss_f_weights = ionp_amount / pattern_lengths

    elif weighted_loss_f == "length":
        loss_f_weights = pattern_lengths

    elif weighted_loss_f == "iopn_amount":
        loss_f_weights = ionp_amount

    res = pointsetreg(gaussian_centers_3d, mrid_design_dist, loss_f_weights)

    #reg_results = res.x
    #print("Registration resulsts: ")
    #print(reg_results)
    fitted_mrid_points = get_fitted_points(res, mrid_design_dist)

    # filename = "fitted_mrid_points.npy"
    # np.save(os.path.join(analysedpath, mrid_type, filename), fitted_mrid_points)

    return fitted_mrid_points


def pointsetreg(gaussian_centers_3d, pattern_dist, pattern_lengths):
    """
    Registers bundle to the measured Gaussian centers in 3D.
    """
    px_size = 25

    pInit = gaussian_centers_3d[0]
    sph_coord_gaussian_centers = get_spherical_coord(gaussian_centers_3d)
    x_init = np.append(pInit, sph_coord_gaussian_centers[:, 1:].flatten())


    res = minimize(bundle_fit3d_loss, x_init, method='BFGS',
                   args=(gaussian_centers_3d, pattern_dist / px_size, pattern_lengths))

    return res


def get_spherical_coord(cart_coord):
    xyz_list = np.diff(cart_coord, axis=0)
    sph_coord = np.zeros_like(xyz_list)

    for i, xyz in enumerate(xyz_list):
        xy = xyz[0] ** 2 + xyz[1] ** 2
        sph_coord[i, 0] = np.sqrt(xy + xyz[2] ** 2)
        sph_coord[i, 1] = np.arctan2(np.sqrt(xy), xyz[2])  # for elevation angle defined from Z-axis down
        sph_coord[i, 2] = np.arctan2(xyz[1], xyz[0])

    return sph_coord


def bundle_fit3d_loss(x, *args):
    """
    The function to be minimized when registering the point-set
    """

    xfit = x[0]
    yfit = x[1]
    zfit = x[2]

    mriPoints = args[0]
    pattern_dists = args[1]
    pattern_lengths = args[2]
    inverse_lengths = 1 / pattern_lengths
    weights = inverse_lengths / np.sum(inverse_lengths)
    d = []
    for i, mriPoint in enumerate(mriPoints):
        mriX, mriY, mriZ = mriPoint
        if i == 0:
            err_d = np.sqrt((mriX - xfit) ** 2 + (mriY - yfit) ** 2 + (mriZ - zfit) ** 2)
            err_d_weighted = err_d * weights[i]
            d.append(err_d_weighted)
            # d.append(np.sqrt((mriX-xfit)**2 + (mriY-yfit)**2 + (mriZ-zfit)**2))
        else:
            r = pattern_dists[i - 1]
            theta = x[2 * i + 1]
            gamma = x[2 * i + 2]

            xfit = xfit + r * math.sin(theta) * math.cos(gamma)
            yfit = yfit + r * math.sin(theta) * math.sin(gamma)
            zfit = zfit + r * math.cos(theta)

            err_d = np.sqrt((mriX - xfit) ** 2 + (mriY - yfit) ** 2 + (mriZ - zfit) ** 2)
            err_d_weighted = err_d * weights[i]
            d.append(err_d_weighted)
            # d.append(np.sqrt((mriX-xfit)**2 + (mriY-yfit)**2 + (mriZ-zfit)**2))

    d = np.array(d)
    return np.sum(d)

def get_fitted_points(reg_result, pattern_dist):
    """
    Calculates the fitted point coordinates given the registration results and MRID dimensions.
    """
    x = reg_result.x

    p1 = [x[0], x[1], x[2]]
    points = [p1]

    num_points = (len(x) - 3) / 2

    for i in range(int(num_points)):
        theta = x[2 * i + 3]
        gamma = x[2 * i + 4]
        # print(points[i])
        xprev, yprev, zprev = points[i]
        r = pattern_dist[i] / 25

        newX = xprev + r * math.sin(theta) * math.cos(gamma)
        newY = yprev + r * math.sin(theta) * math.sin(gamma)
        newZ = zprev + r * math.cos(theta)

        newP = [newX, newY, newZ]
        points.append(newP)

    points = np.array(points)

    return points
