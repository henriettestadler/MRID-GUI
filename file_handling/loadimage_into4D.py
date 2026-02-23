# This Python file uses the following encoding: utf-8
import SimpleITK as sITK
import numpy as np
from core.mrid_tags import MRID_tags
from collections import Counter
from gui_utils.paintbrush_gui import PaintbrushGUI

class LoadImage4D:
    def __init__(self,MainWindow, filename):
        """
        Initializes class to add another layer to a 4D data.
        """
        self.MW = MainWindow
        self.LoadMRI = self.MW.LoadMRI
        self.label_file_imported = False


    def open_file(self,filename,data_view):
        """
        Checks which data type the imported file is.
        """
        if data_view is not None:
            keys = list(self.LoadMRI.vtk_widgets[0].keys())
            idx = keys.index(data_view)
        if "-segmentation" in filename:
            self.load_segmentation(filename,data_view,idx)
        elif "-anat" in filename:
            self.load_anat(filename,data_view,idx)
        elif filename.endswith(".txt"):
            self.get_label_names(filename)
            return None
        else:
            print('not yet implemented')

        return sITK.GetArrayFromImage(sITK.ReadImage(filename))


    def load_anat(self,filename,data_view,idx):
        """
        Loads files including "-anat" in filename as anatomical region label mask.
        """
        # Create the actor
        img = sITK.ReadImage(filename)
        img_dir = img.GetDirection()
        img_dir = np.array(img_dir).reshape(3,3)
        img_dir_max = [max(col, key=abs) for col in zip(*img_dir)]
        axes_to_flip = []
        for i in range(3): #Code is built on z being negative
            if (img_dir_max[i] < 0 and i!=2) or (img_dir_max[i] > 0 and i==2):
                axes_to_flip.append(True)
            else:
                axes_to_flip.append(False)
        axes_to_flip[2]=False
        img_flipped = sITK.Flip(img, axes_to_flip, flipAboutOrigin=False)
        vol = sITK.GetArrayFromImage(img_flipped)

        if data_view=='sagittal':
            self.LoadMRI.paintbrush.label_volume[idx] = np.swapaxes(vol, 1, 2)  #transpose and flip in x and y # #
        else:
            self.LoadMRI.paintbrush.label_volume[idx] = vol

        #directly visualizing it
        # Refresh all
        if self.LoadMRI.vol_dim== 3:
            self.LoadMRI.update_slices(0,idx,data_view)
        else:
            for i in 0,1,2:
                self.LoadMRI.update_slices(i,idx,data_view)
        self.LoadMRI.paintbrush.histogram()


    def load_segmentation(self,filename,data_view,idx):
        """
        Loads files including "-segmentation" in filename as segmentation label mask.

        !!!HAS TO BE CHECKED!!!
        """
        img = sITK.ReadImage(filename)
        img_dir = img.GetDirection()
        img_dir = np.array(img_dir).reshape(3,3)
        img_dir_max = [max(col, key=abs) for col in zip(*img_dir)]
        axes_to_flip = []
        for i in range(3): #Code is built on z being negative
            if (img_dir_max[i] < 0 and i!=2) or (img_dir_max[i] > 0 and i==2):
                axes_to_flip.append(True)
            else:
                axes_to_flip.append(False)
        img_flipped = sITK.Flip(img, axes_to_flip, flipAboutOrigin=False)
        vol = sITK.GetArrayFromImage(img_flipped)

        #combine segmentation and anat
        if data_view=='sagittal':
            #self.LoadMRI.paintbrush.label_volume[idx] = np.swapaxes(vol, 1, 2)  #transpose and flip in x and y # #
            self.LoadMRI.paintbrush.label_volume[idx] = np.maximum(self.LoadMRI.paintbrush.label_volume[idx], np.swapaxes(vol, 1, 2))
        else:
            #self.LoadMRI.paintbrush.label_volume[idx] = vol
            self.LoadMRI.paintbrush.label_volume[idx] = np.maximum(self.LoadMRI.paintbrush.label_volume[idx], vol)

        #directly visualizing it
        # Refresh all
        if self.LoadMRI.vol_dim== 3:
            self.LoadMRI.update_slices(0,idx,data_view)
        else:
            for i in 0,1,2:
                self.LoadMRI.update_slices(i,idx,data_view)
        #directly generating supervised heatmap!
        roi_indices = np.unique(vol)
        print(vol)
        self.LoadMRI.mrid_tags.update_heatmap(data_view,idx,roi_indices)



    def get_label_names(self,filename):
        """
        Loads label names in case text file in uploaded.
        """
        labels = []
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Split by tab or spaces
                parts = line.split()
                # The last column is the quoted label name
                if len(parts) >= 8:
                    label = parts[-1].strip('"')
                    labels.append(label)
        labels.pop(0)
        num_regions = 0
        regions = []
        num_tags = 0
        tag_num =0
        tag_data = []
        pure_labels = [l.rstrip("0123456789") for l in labels]
        counts = Counter(pure_labels)
        counts_dict = dict(counts)

        tag_labels = False

        for i, label in enumerate(labels):
            if label.endswith("1"):
                tag_num += counts_dict[pure_labels[i]]
                tag_data.append((pure_labels[i],counts_dict[pure_labels[i]]))
                tag_labels = True
            elif not tag_labels:
                num_regions +=1
                regions.append([label,1])

        if not hasattr(self.LoadMRI, "mrid_tags"):
            self.LoadMRI.mrid_tags = MRID_tags(self.MW,num_tags, tag_data,num_regions,regions)
        else:
            self.LoadMRI.mrid_tags.num_tags = num_tags
            self.LoadMRI.mrid_tags.tag_data = tag_data
            self.LoadMRI.mrid_tags.num_regions = num_regions
            self.LoadMRI.mrid_tags.region_data = regions
        print(self.LoadMRI.mrid_tags.region_data, self.LoadMRI.mrid_tags.tag_data)
        self.LoadMRI.mrid_tags.create_labels()

        #add actors
        self.MW.ui.checkBox_Brush_MRID.setEnabled(True)
        self.LoadMRI.paint = True

        if not hasattr(self.LoadMRI.paintbrush,"size"):
            self.LoadMRI.PaintbrushGUI = PaintbrushGUI(self.MW,False)
        else:
            self.LoadMRI.PaintbrushGUI.paintbrush_gui(self.MW.ui.comboBox_paintOver_Post)
        self.LoadMRI.paintbrush.start_paintbrush()

        #Save file
        self.LoadMRI.tag_file = True
        self.LoadMRI.mrid_tags.heatmap_unsuper= True
        self.MW.ui.pushButton_anatOK.clicked.connect(self.MW.ButtonsGUI_4D.continue_mridtags)

        #change tab
        self.MW.ui.stackedWidget_4D.setCurrentIndex(1)

        self.label_file_imported = True
