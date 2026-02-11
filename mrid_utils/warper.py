import SimpleITK as sitk
import os
from mrid_utils import handlers

def heatmap_warp(filename, mrid, savepath, sessionpath, fixed_ind, tx):
    """
    Warps and resamples the contrast heatmap to the whole volume data
    Warps and resamples the segmentation of contrast heatmap to the whole volume data
    """

    fixed_filename = handlers.find_resampled_img(fixed_ind, os.path.join(sessionpath, "anat"))
    fixed_path = os.path.join(sessionpath, "anat", fixed_filename)

    filename = os.path.basename(filename)
    heatmap_filename = ".".join((filename + "-" + mrid + "-heatmap", "nii", "gz"))
    heatmap_path =  os.path.join(savepath, heatmap_filename)

    heatmap_resampled_name = ".".join((filename + "-" + mrid + "-heatmap-warped", "nii", "gz"))
    resampled_path = os.path.join(savepath, heatmap_resampled_name)
    warp(heatmap_path, fixed_path, tx, resampled_path)

    # Warping the segmentation image
    segmentation_filename = ".".join((filename + "-segmentation", "nii", "gz"))
    segmentation_path = os.path.join(sessionpath, "anat", segmentation_filename)
    segmentation_newfilename = ".".join((filename + "-" + mrid + "-heatmap-segmentation-warped", "nii", "gz"))
    segmentation_newpath = os.path.join(savepath, segmentation_newfilename)
    warp(segmentation_path, fixed_path, tx, segmentation_newpath, segmentation=True)

    #Warping 3d volume of 4dvolume

    vol4d_filename = ".".join((filename, "nii", "gz"))
    vol4d_path = os.path.join(sessionpath, "anat", vol4d_filename)
    warp_4dslice_name = ".".join((filename + "-resampled-warped", "nii", "gz"))
    warp_4dslice_path = os.path.join(sessionpath, "anat", warp_4dslice_name)
    if not os.path.exists(warp_4dslice_path):
        print("i am here only once")
        warp(vol4d_path, fixed_path, tx, warp_4dslice_path,vol4d=True)

    return fixed_path


def warp(moving_path, fixed_path, tx, resampled_path, segmentation=False,vol4d=False):
    fixed_img = sitk.ReadImage(fixed_path)
    moving_img = sitk.ReadImage(moving_path)

    nn_interpolator = sitk.sitkNearestNeighbor

    if segmentation:
        resampled_img = sitk.Resample(moving_img, fixed_img, tx, interpolator=nn_interpolator)
    elif vol4d:
        index = [0,0,0,0]
        size = list(moving_img.GetSize())
        size[3]=0
        moving_img = sitk.Extract(moving_img, size, index)
        resampled_img = sitk.Resample(moving_img, fixed_img, tx)
    else:
        resampled_img = sitk.Resample(moving_img, fixed_img, tx)

    sitk.WriteImage(resampled_img, resampled_path)


def create_composite_transform(transformations, anatpath, verbose=False):
    composite = sitk.CompositeTransform(3)

    for i, transform_filename in enumerate(transformations):
        transform_path = os.path.join(anatpath, transform_filename + ".txt")

        if verbose:
            print("Transform applied in " + str(i) + "th order: ")
            print(transform_path)

        tx = sitk.ReadTransform(transform_path)

        # Compose the transforms
        # Transforms are applied in the order they are added
        composite.AddTransform(tx)

    return composite
