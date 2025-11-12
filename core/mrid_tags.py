# This Python file uses the following encoding: utf-8
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFileDialog
import os
import SimpleITK as sITK
from PySide6.QtCore import QObject, Signal


class MRID_tags(QObject):
    """
    Class to manage MRI tags, labels, and saving functionality.
    Handles label creation, text file generation, and NIfTI saving.
    """
    fileSaved = Signal(str)  # define the signal — emits the saved file path

    def __init__(self,load_mri:object,num_tags:int, tag_data: list[tuple[str, int]],num_regions:int,regions: list[tuple[str, int]]):
        """Initialize MRID_tags."""
        super().__init__()
        self.load_mri = load_mri
        self.tag_data = tag_data
        self.num_tags = num_tags
        self.num_regions = num_regions
        self.region_data = regions


    def create_labels(self):
        """
        Generate labels for anatomical regions and tags.
        Sets up colors for paintbrush, paintover, and histogram.
        """
        #predefined colors
        colors_predefined = ["red", "lime", "blue", "yellow", "aqua", "magenta", "PapayaWhip", "MediumBlue", "Peru", "Tan",
                            "MediumAquaMarine", "navy", "olive", "salmon", "chocolate","gold","orange","coral","navy","violet"]

        total_islands = sum([self.tag_data[i][1] for i in range(self.num_tags)])

        if total_islands > len(colors_predefined):
            #more colors have to be defined
            num_colors_needed = total_islands - len(colors_predefined)
            colors_predefined.extend([QColor.fromHsv(int(360/num_colors_needed * i), 255, 200).name() for i in range(num_colors_needed)])

        label_names = []
        label_text = []
        index = 0
        self.VIS_MSH = {}
        self.VIS_MSH[0] = [0,0]

        for name, count in self.region_data:
            for i in range(count):
                label_names.append(f"{name}") #anatomical regions
                label_text.append(colors_predefined[index])
                index += 1
                self.VIS_MSH[index] = [1, 1]

        for name, count in self.tag_data:
            for i in range(count):
                label_names.append(f"{name}{i+1}") #tags and islands
                label_text.append(colors_predefined[index])
                index += 1
                self.VIS_MSH[index] = [1, 1]

        # Active Labels
        self.load_mri.paintbrush.color_combobox = ["white"]
        self.load_mri.paintbrush.color_combobox.extend(label_text)
        self.load_mri.paintbrush.labels_combobox = ["Clear Labels"]
        self.load_mri.paintbrush.labels_combobox.extend(label_names)

        #paintover
        self.load_mri.paintbrush.color_paintover = ["black", "white"]
        self.load_mri.paintbrush.color_paintover.extend(label_text)
        self.load_mri.paintbrush.labels_paintover = ["All Labels","Clear Label"]
        self.load_mri.paintbrush.labels_paintover.extend(label_names)

        #Histogram
        self.load_mri.paintbrush.color_histogram = label_text
        self.load_mri.paintbrush.labels_histogram = label_names

        self.load_mri.paintbrush.RGBA = {}
        self.load_mri.paintbrush.RGBA[0] = [0,0,0,0]
        self.load_mri.paintbrush.RGB_table = []
        self.load_mri.paintbrush.RGB_table= [(0,0,0,0)]
        for i,color in enumerate(self.load_mri.paintbrush.color_combobox):
            if i == 0:
                continue
            if isinstance(color, str) and color.startswith("#"):
                qcolor = QColor(color)
                self.load_mri.paintbrush.RGBA[i] = qcolor.getRgb()
                r, g, b, a = qcolor.getRgb()
                self.load_mri.paintbrush.RGB_table.append([r/255,g/255,b/255,0.3]) #self.Load_MRI.paintbrush.labelOccupancy
            else:
                qcolor = QColor(color)
                r, g, b, a = qcolor.getRgb()
                self.load_mri.paintbrush.RGBA[i] = qcolor.getRgb()
                self.load_mri.paintbrush.RGB_table.append((r/255,g/255,b/255,0.3)) #self.Load_MRI.paintbrush.labelOccupancy


    def generate_textfile(self):
        """
        Save each tag and its color to a tab-separated text file.
        """

        # Folder path
        folder = "text_file"
        # Make sure the folder exists
        os.makedirs(folder, exist_ok=True)
        # Full path to save the file
        filename = os.path.join(folder, "labels.txt")
        label_names = self.load_mri.paintbrush.labels_combobox

        RGBA = self.load_mri.paintbrush.RGBA

        with open(filename, "w", encoding="utf-8") as f:
            #Write header
            f.write("###########################\n")
            f.write("# Label Description File \n")
            f.write("# File Format: \n")
            f.write("# IDX -R- -G- -B- -A-- VIS MSH LABEL \n")
            f.write("# Fields: \n")
            f.write("# IDX: Zero-based index \n")
            f.write("# -R-: Red color component (0..255) \n")
            f.write("# -G-: Green color component (0..255) \n")
            f.write("# -B-: Blue color component (0..255) \n")
            f.write("# -A--: Label transparency (0..1) \n")
            f.write("# VIS: Label visibility (0 or 1) \n")
            f.write("# MSH: Label mesh visibility (0 or 1) \n")
            f.write("# LABEL: Label description \n")
            f.write("###########################\n")

            for i,label in enumerate(label_names):
                f.write(f'{i}\t{RGBA[i][0]}\t{RGBA[i][1]}\t{RGBA[i][2]}\t{int(RGBA[i][3]/255)}\t{self.VIS_MSH[i][0]}\t{self.VIS_MSH[i][1]}\t"{label}"\n')

    def save_as_niigz(self):
        """
        Save the current label volume as a NIfTI (.nii.gz) file.
        Prompts the user for location and name. Copies image metadata from the original MRI.
        Emits:
            fileSaved(str): The path to the saved file.
        """

        # Convert your NumPy label array back to a SimpleITK image
        label_image = sITK.GetImageFromArray(self.load_mri.paintbrush.label_volume)
        size = list(self.load_mri.paintbrush.label_volume.shape[::-1]) + [0]  # Extract 1 time frame
        reference_image = sITK.Extract(
            self.load_mri.image[0],
            size=size,
            index=[0, 0, 0, 0]  # take time=0 frame
        )
        label_image.CopyInformation(reference_image)

        # Suggest a default name (for example, based on the original file name)
        if self.load_mri.tag_file:
            file_name = self.load_mri.file_name[0][:-7]
            default_name = f"{file_name}-anat.nii.gz" #"label_volume.nii.gz"
            self.load_mri.tag_file = False
        else:
            file_name = self.load_mri.file_name[0][:-7]
            default_name = f"{file_name}-segmentation.nii.gz"


        if hasattr(self, "file_name"):
            # if you stored the original filename somewhere
            base = os.path.splitext(os.path.basename(self.file_name))[0]
            default_name = f"{base}_label.nii.gz"

        # Ask user where to save, showing the default name
        save_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Label Volume",
            default_name,                  # 👈 default filename shown here
            "NIfTI files (*.nii.gz)"
        )

        if not save_path:
            return

        # Ensure the filename ends with .nii.gz
        if not save_path.lower().endswith(".nii.gz"):
            save_path += ".nii.gz"

        sITK.WriteImage(label_image, save_path)

        self.fileSaved.emit(save_path)  # emit the signal

