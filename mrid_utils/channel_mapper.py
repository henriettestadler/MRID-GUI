import numpy as np
from mrid_utils import com
import os
import nibabel as nib

# TODO: HENRIETTE, BELOW MIGHT BE UNNECESSARY FOR YOU, JUST LOADING ATLAS IMAGES AND LABELS, just make sure you have the necessary variables loaded somewhere
#root=""

#
#mask_path=os.path.join(root, "WHS_SD_rat_atlas_v4_pack","WHS_SD_v2_brainmask_bin.nii.gz")
#nii_mask=nib.load(mask_path)
#mask=np.asanyarray(nii_mask.dataobj)

# t2s_path=os.path.join(root, "WHS_SD_rat_atlas_v4_pack","WHS_SD_rat_T2star_v1.01.nii.gz")
# nii_t2s=nib.load(t2s_path)
# t2s=np.asanyarray(nii_t2s.dataobj)

# TODO: HENRIETTE, ABOVE MIGHT BE UNNECESSARY FOR YOU, JUST LOADING ATLAS IMAGES AND LABELS

def map_electrodes_main(fitted_points, mrid_dict, px_size = 25, channel_separation = 50, total_ch = 64):
    """
    Map electrode channels along the best-fit trajectory in MRI space given the mrid_dict
    """
    ## GET: channel_separation and total_ch and ask for ATLAS directory?
    last_ch_dist = com.get_dist_to_deepest_ch(mrid_dict)
    print("Distance from last (deepest) CoM to the deepest channel (um):")
    print(last_ch_dist)

    chs_mapped = 0
    ch_coords = []

    for i in range(len(fitted_points) - 1):
        bottom = fitted_points[-1 * i - 1, :]
        top = fitted_points[-1 * i - 2, :]

        dist = np.linalg.norm(top - bottom) * px_size
        if i == 0 and i != len(fitted_points) - 2:
            print("First (deepest) segment mapping")
            dist = dist + last_ch_dist
            nchannels = np.floor(dist / channel_separation).astype(int)
            if nchannels + chs_mapped < total_ch:
                nchannels = nchannels
            else:
                nchannels = total_ch - chs_mapped

            ch_coords_segment, _ = interpolate_channels(bottom, top, nchannels, offset=last_ch_dist, channel_separation=channel_separation)

        elif i == 0 and i == len(fitted_points) - 2:
            print("Only 2 patterns available, simply linear mapping")
            dist = dist + last_ch_dist
            nchannels = np.floor(dist / channel_separation).astype(int)
            print("Number channels between patterns: ")
            print(nchannels)
            nchannels = total_ch

            ch_coords_segment, _ = interpolate_channels(bottom, top, nchannels, offset=last_ch_dist, channel_separation=channel_separation)

        elif i == len(fitted_points) - 2 and i != 0:
            print("Last segment mapping")
            nchannels = total_ch - chs_mapped
            print("Remaining channels to be mapped: ")
            print(nchannels)
            ch_coords_segment, _ = interpolate_channels(bottom, top, nchannels, offset=0, channel_separation=channel_separation)

        else:
            nchannels = np.floor(dist / channel_separation).astype(int)
            if nchannels + chs_mapped < total_ch:
                nchannels = nchannels
            else:
                nchannels = total_ch - chs_mapped

            ch_coords_segment, _ = interpolate_channels(bottom, top, nchannels, offset=0, channel_separation=channel_separation)

        ch_coords.append(ch_coords_segment)
        print("Number of channels mapped in this segment: ")
        print(nchannels)
        chs_mapped = chs_mapped + nchannels
        print("Total channels mapped: ")
        print(chs_mapped)

    ch_coords = np.vstack(ch_coords)
    print("Mapped channel coordinates: ")
    print(ch_coords)
    # visualize_channelfit(ch_coords, fitted_points)
    return ch_coords


def interpolate_channels(bottom_coord, top_coord, nchannels, offset, channel_separation, px_size=25):
    """
    Interpolate channels with a fixed channel_separation between a bottom_coord (ventral) and a top_coord (dorsal)
    Returns the channel coordinates array
    """
    unitvec = top_coord - bottom_coord
    unitvec = unitvec / np.linalg.norm(unitvec)

    ch_coords = np.zeros((nchannels, 3))

    if offset > 0:
        bottom = bottom_coord - (offset / px_size) * unitvec
    for i in range(nchannels):
        ch_coords[i, :] = np.round(bottom_coord + (i * unitvec * (channel_separation / px_size)))

    return (ch_coords).astype('int'), unitvec


def map_channels_to_atlas(ch_coord, moving_coordinates, fixed_coordinates, savepath):
    """
    Maps channels to anatomical regions given ch_coord in MRI-space, moving_coordinates in MRI-space and fixed_coordinates in atlas space
    """
def map_channels_to_atlas(ch_coord, moving_coordinates, fixed_coordinates, savepath,atlas,atlaslabelsdf,dwi):
    # Coronal slice to be plotted selector
    # temp_y = 0

    # To find the minima, 16bit gray-scale pixels
    minPixVal = 2e16

    num_channels = len(ch_coord)
    dwi1Dsignal = np.zeros((num_channels,))
    pyrCh = 9999
    regionNames = []
    regionNumbers = []
    # pyrChIdx = 0
    #pyrLyExists = False

    with open(os.path.join(savepath, "channel_atlas_coordinates.txt"), 'w') as f:

        for idx, coord in enumerate(ch_coord):
            #print(idx,coord, ch_coord)
            atlasIdx = ((moving_coordinates[:, 0] == coord[0]) & (moving_coordinates[:, 1] == coord[1]) & (
                        moving_coordinates[:, 2] == coord[2]))
            if fixed_coordinates[atlasIdx].any():
                print("Exact coordinate exists")
            else:
                print("no exact atlas coord")
                atlasIdx = ((moving_coordinates[:, 0] >= coord[0] - 1) & (moving_coordinates[:, 0] <= coord[0] + 1) &
                            (moving_coordinates[:, 1] >= coord[1] - 1) & (moving_coordinates[:, 1] <= coord[1] + 1) &
                            (moving_coordinates[:, 2] >= coord[2] - 1) & (moving_coordinates[:, 2] <= coord[2] + 1)
                            )

            atlasCoord = fixed_coordinates[atlasIdx][0]
            x, y, z = atlasCoord.astype(int)
            label = atlas[x, y, z]
            print('label',label)
            anat_region = atlaslabelsdf["Anatomical Regions"][atlaslabelsdf["Labels"] == label].values[0]
            regionNames.append(anat_region)
            regionNumbers.append(label)

            currPixVal = dwi[x, y, z]
            dwi1Dsignal[idx] = currPixVal
            if anat_region == "Cornu ammonis 1":
                #pyrLyExists = True
                if currPixVal < minPixVal:
                    minPixVal = currPixVal
                    pyrCh = idx
                    # pyrChIdx = idx

            line = "CH:" + str(idx) + " in " + anat_region + ' Segment: ' + str(label) + " atlas coord: " + str(
                atlasCoord) #str(chMap[idx])
            print(line)
            f.write(line)
            f.write('\n')

        # Writing the pyramidal channel
        line = "CH:" + str(pyrCh) + " in pyramidal layer CA1"
        print(line)
        f.write(line)
        f.write('\n')

    # if pyrLyExists:
    #     pixelValues = dwi1Dsignal
    #     pixelValues = (pixelValues - np.min(pixelValues)) / (np.max(pixelValues) - np.min(pixelValues))
    #     plt.figure(figsize=(25, 10))
    #     # Get unique categories and assign each a color
    #     unique_regions = list(set(regionNames))
    #     colors = plt.cm.get_cmap("tab10", len(unique_regions))  # Color map
    #
    #     region_to_color = {region: colors(i) for i, region in enumerate(unique_regions)}
    #
    #     # Plot line segments with color depending on region
    #     for i in range(len(pixelValues) - 1):
    #         region = regionNames[i]
    #         plt.plot([i, i + 1], [pixelValues[i], pixelValues[i + 1]],
    #                  color=region_to_color[region], linewidth=2)
    #
    #     # Optional: Add legend
    #     for region in unique_regions:
    #         plt.plot([], [], color=region_to_color[region], label=region)
    #
    #     plt.axvline(x=pyrChIdx, color='red', linestyle='--', linewidth=2, label='Pyramidal Layer')
    #     plt.xticks(ticks=np.linspace(0, num_channels - 1, num_channels), labels=chMap)
    #     plt.legend(title="Anatomical Region")
    #     plt.xlabel("Channel Index")
    #     plt.ylabel("Pixel Value")
    #     plt.title("Pixel Values by Region")
    #     plt.grid(True)
    #     plt.savefig(os.path.join(savepath, "dwi_1D_cross_section.pdf"), dpi=2000)
    #     plt.show()

    return dwi1Dsignal


def get_mapped_ch(chmap_path, anat_list, num_channels=64, filename="channel_atlas_coordinates.txt"):
    """
    Gets channels in the given list of anatomical regions (anat_list).
    Reads the localization results channel_atlas_coordinates.txt file in chmap_path.
    num_channels per shank (default 64)

    This function can be used together with plot_channels_on_atlas() function below
    """
    ch_coord = np.zeros((num_channels, 3))
    fullpath = os.path.join(chmap_path, filename)
    detected = 0
    with open(fullpath) as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            anat_region = line.split(":")[1].split("in")[-1][1:].split(" Segment")[0]
            for roi in anat_list:
                if anat_region == roi:
                    ch = int(line.split()[0].split(":")[1])
                    # if ch in ch_selected:
                    x, y, z = line.split("[")[1].split("]")[0].split()
                    ch_coord[detected, :] = np.array([x, y, z])
                    detected = detected + 1

    ch_coord = ch_coord[:detected, :]
    ch_coord = ch_coord.astype(int)

    return ch_coord



def plot_channels_on_atlas(savefigname, path, ch_selected):
    """
    Plots given set of channels on atlas images
    """
    # Plotting colormap settings
    my_cmap_gray = cm.get_cmap("gray").copy()
    my_cmap_gray.set_under('black', alpha=0)
    cmap_args_gray = dict(cmap=my_cmap_gray, vmin=1)

    y = np.median(ch_selected[:, 1]).astype(int)

    if "t2s" in savefigname:
        plt.imshow(t2s[:, y, :] * mask[:, y, :], **cmap_args_gray)
    elif "dwi" in savefigname:
        plt.imshow(dwi[:, y, :] * mask[:, y, :], **cmap_args_gray)

    for idx, coord in enumerate(ch_selected):
        x, _, z = coord
        plt.scatter(z, x, s=0.1, c='r')
    #     plt.text(z, x, str(ch_selected[idx]))

    plt.savefig(os.path.join(path, savefigname), dpi=1000)
    plt.show()
    regionNumbers = list(dict.fromkeys(regionNumbers))
    return dwi1Dsignal, regionNumbers
