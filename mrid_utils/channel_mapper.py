import numpy as np
from mrid_utils import com
import os
import matplotlib.pyplot as plt
from mplwidget import MplWidget
from scipy.spatial import cKDTree
import pandas as pd


def map_electrodes_main(fitted_points, mrid_dict, px_size = 25, channel_separation = 50, total_ch = 64):
    """
    Map electrode channels along the best-fit trajectory in MRI space given the mrid_dict
    """
    ## GET: channel_separation and total_ch and ask for ATLAS directory?
    last_ch_dist = com.get_dist_to_deepest_ch(mrid_dict)

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
    #print("Mapped channel coordinates: ")
    #print(ch_coords)
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


def map_channels_to_atlas(ch_coord, fitted_mrid_points,moving_coordinates, fixed_coordinates, savepath,atlas,atlaslabelsdf,dwi,chMap=[]):
    # Coronal slice to be plotted selector
    # temp_y = 0
    # To find the minima, 16bit gray-scale pixels
    minPixVal = 2e16

    num_channels = len(ch_coord)
    dwi1Dsignal = np.zeros((num_channels,))
    pyrCh = 9999
    regionNames = []
    regionNumbers = []
    pyrChIdx = 0
    pyrLyExists = False
    label_to_region = dict(zip(atlaslabelsdf["Labels"],atlaslabelsdf["Anatomical Regions"]))
    tree = cKDTree(moving_coordinates)
    rows = []

    #with open(os.path.join(savepath, "channel_atlas_coordinates.txt"), 'w') as f:

    for idx, coord in enumerate(ch_coord):
        # Query nearest neighbor
        dist, idx_nearest = tree.query(coord)
        atlasCoord = fixed_coordinates[idx_nearest]

        x, y, z = atlasCoord.astype(int)
        label = atlas[x, y, z]
        anat_region = label_to_region[label]
        regionNames.append(anat_region)
        regionNumbers.append(label)
        rows.insert(0, { #.append({
            "Channel ID": idx,
            "Channel": label,
            "Channel Label": anat_region,
            "Atlas x": atlasCoord[0],
            "Atlas y": atlasCoord[1],
            "Atlas z": atlasCoord[2],
        })

        df = pd.DataFrame(rows)
        excel_path = os.path.join(savepath, "channel_atlas_coordinates.xlsx")
        df.to_excel(excel_path, index=False)


        currPixVal = dwi[x, y, z]
        dwi1Dsignal[idx] = currPixVal
        if anat_region == "Cornu ammonis 1":
            pyrLyExists = True
            if currPixVal < minPixVal:
                minPixVal = currPixVal
                pyrChIdx = idx
                #chMap.append(idx)


    atlasCoordinates_pkl = []
    for idx, coord in enumerate(fitted_mrid_points):
        dist, idx_nearest = tree.query(coord)
        atlasCoord = fixed_coordinates[idx_nearest]
        atlasCoordinates_pkl.append(atlasCoord)

    if pyrLyExists:
        pixelValues = dwi1Dsignal
        pixelValues = (pixelValues - np.min(pixelValues)) / (np.max(pixelValues) - np.min(pixelValues))
        plot = MplWidget(dwi=True)
        ax1 = plot.canvas.figure.add_subplot(111)
        #plt.figure(figsize=(25, 10))
        # Get unique categories and assign each a color
        unique_regions = list(set(regionNames))
        colors = plt.cm.get_cmap("tab10", len(unique_regions))  # Color map

        region_to_color = {region: colors(i) for i, region in enumerate(unique_regions)}
        # Plot line segments with color depending on region
        for i in range(len(pixelValues) - 1):
            region = regionNames[i]
            ax1.plot([i, i + 1], [pixelValues[i], pixelValues[i + 1]],
                     color=region_to_color[region], linewidth=2)

        # Optional: Add legend
        for region in unique_regions:
            ax1.plot([], [], color=region_to_color[region], label=region)

        ax1.axvline(x=pyrChIdx, color='red', linestyle='--', linewidth=2, label='Pyramidal Layer')
        ax1.set_xticks(np.linspace(0, num_channels - 1, num_channels))
        ax1.tick_params(axis="x", labelrotation=45)
        if chMap:
            print('chMap',chMap,flush=True)
            ax1.set_xticklabels(chMap)
        ax1.legend(title="Anatomical Region",fontsize=16,title_fontsize=16) #7
        ax1.set_xlabel("Channel Index")
        ax1.set_ylabel("Pixel Value")
        ax1.set_title("Pixel Values by Region")
        ax1.tick_params(axis='both', labelsize=16) #6
        ax1.grid(True)
        plot.canvas.draw()
        plot.canvas.figure.savefig(os.path.join(savepath, "dwi_1D_cross_section.pdf"), dpi=2000)

    return dwi1Dsignal,regionNames,regionNumbers,pyrLyExists,pyrChIdx,atlasCoordinates_pkl



