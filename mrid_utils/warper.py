import SimpleITK as sitk
import os
import handlers

def heatmap_warp(filename, mrid, savepath, sessionpath, transform_filename, inverseTransform=False):
    """
    Warps and resamples the contrast heatmap to the whole volume data
    Warps and resamples the segmentation of contrast heatmap to the whole volume data
    """
    # Check if single transformation is provided
    if isinstance(transform_filename, str):
        print("Single transformation file provided")
        transform_path = os.path.join(sessionpath, "anat", transform_filename + ".txt")
        tx = sitk.ReadTransform(transform_path)
        if inverseTransform:
            print("Transformation matrix will be inverted")
            tx = tx.GetInverse()
            fixed_ind = transform_filename.split("-")[1]
        else:
            fixed_ind = transform_filename.split("-")[-1]

    # Check if multiple transformations are provided
    elif isinstance(transform_filename, list):
        print("Multiple transformation files provided, creating a composite transform")
        tx = create_composite_transform(transform_filename, os.path.join(sessionpath, "anat"))
        fixed_ind = transform_filename[-1].split("-")[-1]

    else:
        print("No valid transformation!")

        heatmap_filename = ".".join((filename + "-" + mrid + "-heatmap", "nii", "gz"))
        heatmap_path = os.path.join(savepath, heatmap_filename)

        heatmap_resampled_name = ".".join((filename + "-" + mrid + "-heatmap-warped", "nii", "gz"))
        resampled_path = os.path.join(savepath, heatmap_resampled_name)


    fixed_filename = handlers.find_resampled_img(fixed_ind, os.path.join(sessionpath, "anat"))
    fixed_path = os.path.join(sessionpath, "anat", fixed_filename)
    warp(heatmap_path, fixed_path, tx, resampled_path)
    # Warping the segmentation image
    segmentation_filename = ".".join((filename + "-segmentation", "nii", "gz"))
    segmentation_path = os.path.join(sessionpath, "anat", segmentation_filename)

    segmentation_newfilename = ".".join((filename + "-" + mrid + "-heatmap-segmentation-warped", "nii", "gz"))
    segmentation_newpath = os.path.join(savepath, segmentation_newfilename)

    warp(segmentation_path, fixed_path, tx, segmentation_newpath, segmentation=True)

    return fixed_path


def warp(moving_path, fixed_path, tx, resampled_path, segmentation=False):
    fixed_img = sitk.ReadImage(fixed_path)
    moving_img = sitk.ReadImage(moving_path)

    nn_interpolator = sitk.sitkNearestNeighbor

    if segmentation:
        resampled_img = sitk.Resample(moving_img, fixed_img, tx, interpolator=nn_interpolator)
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