from PySide6 import QtWidgets
import sys
from PySide6.QtWidgets import QFileDialog
from file_handling.loadimage_into4D import LoadImage4D
import os
from PySide6.QtWidgets import QHBoxLayout,QPushButton,QDialog,QWidget, QCheckBox, QPlainTextEdit
import glob


class MRID_InputDialog(QtWidgets.QDialog):
    """
    A dialog window that allows users to specify anatomical regions and MRID tags (for 4D data).

    Notes
    --------
    - Dynamically adds/removes region and tag input fields based on spin box values.
    - Allows specifying tag names, number of islands, and region names.
    - Returns all inputs in a structured format (num_tags, tags, num_regions, regions).
    """
    def __init__(self, MW, parent=None):
        """
        Initialize the input dialog UI and connect signals.
        """
        super().__init__(parent)
        self.setWindowTitle("Input Values")
        self.setModal(True)
        self.resize(400, 400)
        self.MW = MW
        self.filename = None

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        text = QtWidgets.QPlainTextEdit("Please enter the Anatomical Regions and MRID Tags and Islands. \n"
                                        "After selecting, please activate the Brush and paint the anatomical regions.")
        text.setReadOnly(True)
        text.setFixedSize(400, 100)
        main_layout.addWidget(text)

        #Or upload labels.txt
        if os.path.exists(os.path.join(self.MW.LoadMRI.session_path,"anat","labels.txt")):
            file_layout = QtWidgets.QHBoxLayout()
            self.file_line_edit = QtWidgets.QLineEdit()
            self.file_line_edit.setPlaceholderText("Exisiting labels.txt found")
            file_layout.addWidget(self.file_line_edit)
            main_layout.addLayout(file_layout)
            self.filename=os.path.join(self.MW.LoadMRI.session_path,"anat","labels.txt")
        else:
            file_layout = QtWidgets.QHBoxLayout()
            self.file_line_edit = QtWidgets.QLineEdit()
            self.file_line_edit.setPlaceholderText("No labels.txt file found. Please browse to load and edit an existing Text file")  # optional
            browse_button = QtWidgets.QPushButton("Browse")
            browse_button.clicked.connect(self.browse_file)
            file_layout.addWidget(self.file_line_edit)
            file_layout.addWidget(browse_button)
            main_layout.addLayout(file_layout)

        #regions
        region_group = QtWidgets.QGroupBox("Anatomical Regions")
        region_layout = QtWidgets.QVBoxLayout(region_group)
        main_layout.addWidget(region_group)

        self.spin_num_regions = QtWidgets.QSpinBox()
        self.spin_num_regions.setRange(1, 20)
        self.spin_num_regions.valueChanged.connect(self.update_region_inputs)
        region_layout.addWidget(QtWidgets.QLabel("Number of Regions:"))
        region_layout.addWidget(self.spin_num_regions)

        #tags
        tag_group = QtWidgets.QGroupBox("Tags")
        tag_layout = QtWidgets.QVBoxLayout(tag_group)
        main_layout.addWidget(tag_group)

        self.spin_num_tags = QtWidgets.QSpinBox()
        self.spin_num_tags.setRange(1, 20)
        self.spin_num_tags.valueChanged.connect(self.update_tag_inputs)
        tag_layout.addWidget(QtWidgets.QLabel("Number of Tags:"))
        tag_layout.addWidget(self.spin_num_tags)

        # Container for dynamic tag inputs
        self.tags_container = QtWidgets.QWidget()
        self.tags_layout = QtWidgets.QFormLayout(self.tags_container)
        tag_layout.addWidget(self.tags_container)

        # Container for dynamic region inputs
        self.regions_container = QtWidgets.QWidget()
        self.regions_layout = QtWidgets.QFormLayout(self.regions_container)
        region_layout.addWidget(self.regions_container)

        #buttons
        button_layout = QtWidgets.QHBoxLayout()
        # Add a small text label
        label = QtWidgets.QLabel("Press OK if data is correct and start painting \n"
            "the anatomical regions. Press Done in the \n"
            "bottom left corner once it is done!")
        label.setStyleSheet("font-size: 10pt;")  # Optional: make it smaller
        button_layout.addWidget(label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        # Add the buttons to the same layout
        button_layout.addWidget(buttons)
        # Add the whole layout to your main layout
        main_layout.addLayout(button_layout)

        # Internal tracking
        self.tag_name_edits = []
        self.tag_island_spins = []
        self.region_name_edits = []
        self.old_tag_count = 0
        self.old_region_count = 0

        # Initialize with 1 tag and 1 region
        self.update_tag_inputs(1)
        self.update_region_inputs(1)

        if self.filename:
            self.browse_file()

    def browse_file(self):
        """
        Opens File Dialog for user to choose labels.txt
        """
        if self.filename is not None:
            print(self.filename,flush=True)
            file_name = self.filename
        else:
            file_name, _ = QFileDialog.getOpenFileName(
                None,
                "Open NIfTI File",
                "",
                "Text files (*.txt)"
            )
            #User cancelled
            if not file_name:
                return


        self.file_line_edit.setPlaceholderText(os.path.basename(file_name))

        #only once OK is pressed
        if not hasattr(self.MW.LoadMRI,"LoadImage4D"):
            self.MW.LoadMRI.LoadImage4D = LoadImage4D(self.MW, file_name)
        tag_data,num_regions,regions = self.MW.LoadMRI.LoadImage4D.open_file(file_name,data_view=None)

        self.spin_num_regions.setValue(num_regions)
        self.spin_num_tags.setValue(len(tag_data))

        for nr in range(num_regions):
            self.region_name_edits[nr].setText(str(regions[nr][0]))

        for nt in range(len(tag_data)): #tag_data.append((pure_labels[i],counts_dict[pure_labels[i]]))
            print(self.tag_name_edits,flush=True)
            self.tag_name_edits[nt].setText(str(tag_data[nt][0]))
            self.tag_island_spins[nt].setValue(tag_data[nt][1])


    def update_tag_inputs(self, num_tags:int):
        """
        Create or remove tag inputs dynamically.
        """
        # Add new ones
        if num_tags > self.old_tag_count:
            for i in range(self.old_tag_count, num_tags):
                name_edit = QtWidgets.QLineEdit()
                island_spin = QtWidgets.QSpinBox()
                island_spin.setRange(1, 100)

                row_widget = QtWidgets.QWidget()
                row_layout = QtWidgets.QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.addWidget(QtWidgets.QLabel(f"Tag {i+1} Name:"))
                row_layout.addWidget(name_edit)
                row_layout.addWidget(QtWidgets.QLabel("Islands:"))
                row_layout.addWidget(island_spin)
                self.tags_layout.addRow(row_widget)

                self.tag_name_edits.append(name_edit)
                self.tag_island_spins.append(island_spin)
        else:
            # Remove extras
            for i in range(self.old_tag_count - num_tags):
                last_row = self.tags_layout.rowCount() - 1
                self.tags_layout.removeRow(last_row)
                self.tag_name_edits.pop()
                self.tag_island_spins.pop()

        self.old_tag_count = num_tags
        self.adjustSize()


    def update_region_inputs(self, num_regions:int):
        """
        Create or remove region name inputs dynamically.
        """
        if num_regions > self.old_region_count:
            for i in range(self.old_region_count, num_regions):
                name_edit = QtWidgets.QLineEdit()
                self.regions_layout.addRow(f"Region {i+1} Name:", name_edit)
                self.region_name_edits.append(name_edit)
        else:
            for i in range(self.old_region_count - num_regions):
                last_row = self.regions_layout.rowCount() - 1
                self.regions_layout.removeRow(last_row)
                self.region_name_edits.pop()

        self.old_region_count = num_regions
        self.adjustSize()


    def get_values(self) -> tuple[int, list[tuple[str, int]], int, list[tuple[str, int]]]:
        """
        Return structured data.
        """
        regions = [(r.text(), 1) for r in self.region_name_edits]
        tags = [(name.text(), spin.value()) for name, spin in zip(self.tag_name_edits, self.tag_island_spins)]

        return len(tags), tags, len(regions), regions



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = MRID_InputDialog()
    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        data = dlg.get_values()





class ANAT_InputDialog(QDialog):
    def __init__(self, MW, form_index,parent=None):
        super().__init__(parent)
        self.MW = MW
        self.setWindowTitle("Label anatomical regions")
        #pop-up -> Please paint the anatomical regions as just defined
        # Anat File found
        # Load Anat File
        # Main layout
        self.file_name = {}
        self.file_line_anat = {}
        main_layout = QtWidgets.QVBoxLayout(self)
        if form_index==0:
            text = QtWidgets.QPlainTextEdit("Please use the paint brush to label the anatomical regions. Once you are done, please click NEXT at the bottom left corner of the GUI.")
        elif form_index==1:
            text = QtWidgets.QPlainTextEdit("Please use the paint brush to now label the each island. Once you are done, please click DONE at the bottom left corner of the GUI.")

        text.setReadOnly(True)
        #text.setFixedSize(400, 100)
        main_layout.addWidget(text)
        for data_index in range(len(self.MW.LoadMRI.vtk_widgets[0])):
            data_view = list(self.MW.LoadMRI.vtk_widgets[0].keys())[data_index]
            self.file_name[data_index] = [None,data_view]
            group_box = QtWidgets.QGroupBox(f"View: {data_view}")
            group_layout = QtWidgets.QVBoxLayout(group_box)

            file_name = self.MW.LoadMRI.file_name[data_index][:-7]

            if form_index==0 and os.path.exists(os.path.join(self.MW.LoadMRI.session_path,f"{file_name}-anat.nii.gz")):
                self.file_name[data_index] = [os.path.join(self.MW.LoadMRI.session_path,f"{file_name}-anat.nii.gz"),data_view]
                text = QtWidgets.QPlainTextEdit(f"Anat File with name \n {os.path.basename(self.file_name[data_index][0])} \n found")
                text.setReadOnly(True)
                group_layout.addWidget(text)
            elif form_index==1 and os.path.exists(os.path.join(self.MW.LoadMRI.session_path,f"{file_name}-segmentation.nii.gz")):
                self.file_name[data_index] = [os.path.join(self.MW.LoadMRI.session_path,f"{file_name}-segmentation.nii.gz"),data_view]
                text = QtWidgets.QPlainTextEdit(f"Segmentation File with name \n {os.path.basename(self.file_name[data_index][0])} \n found")
                text.setReadOnly(True)
                group_layout.addWidget(text)
            else:
                if form_index==0:
                    text = QtWidgets.QPlainTextEdit("No anat File found.")
                elif form_index==1:
                    text = QtWidgets.QPlainTextEdit("No segmentation File found.")
                text.setReadOnly(True)
                group_layout.addWidget(text)

                file_layout = QtWidgets.QHBoxLayout()
                self.file_line_anat[data_index] = QtWidgets.QLineEdit()
                if form_index==0:
                    self.file_line_anat[data_index].setPlaceholderText("Please select the anat file, if one exists.")
                elif form_index==1:
                    self.file_line_anat[data_index].setPlaceholderText("Please select the segmentation file, if one exists.")
                browse_button = QtWidgets.QPushButton("Browse")
                browse_button.clicked.connect(lambda val: self.browse_file(data_index,data_view))
                file_layout.addWidget(self.file_line_anat[data_index])
                file_layout.addWidget(browse_button)
                group_layout.addLayout(file_layout)
            main_layout.addWidget(group_box)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_ok = QPushButton("Understood")
        btn_cancel = QPushButton("Cancel")

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        main_layout.addLayout(button_layout)


    def browse_file(self,data_index,data_view):
        """
        Opens File Dialog for user to choose anat-file
        """
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Open NIfTI File",
            self.MW.LoadMRI.session_path,
            "NIfTI files (*.nii.gz)"
        )

        #User cancelled
        if not file_name:
            return
        self.file_name[data_index] = [file_name,data_view]
        self.file_line_anat[data_index].setPlaceholderText(os.path.basename(file_name))


    def get_values(self):
        """
        Return structured data.
        """
        return self.file_name




if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = ANAT_InputDialog()
    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        data = dlg.get_values()







class TRANSFORM_InputDialog(QDialog):
    def __init__(self, MW,parent=None):
        super().__init__(parent)
        self.MW = MW
        self.setWindowTitle("Select Transform Files")

        #transformation-ind_8-to-ind_1.txt


        self.transformation_files = {}
        self.file_line_txt = {}
        self.checkbox = {}
        main_layout = QtWidgets.QVBoxLayout(self)

        text = QtWidgets.QPlainTextEdit("Please select the correct transformation files.")

        text.setReadOnly(True)
        #text.setFixedSize(400, 100)
        main_layout.addWidget(text)
        for data_index in range(len(self.MW.LoadMRI.vtk_widgets[0])):
            self.checkbox[data_index] = []
            self.transformation_files[data_index] = []
            data_view = list(self.MW.LoadMRI.vtk_widgets[0].keys())[data_index]

            group_box = QtWidgets.QGroupBox(f"View: {data_view}")
            group_layout = QtWidgets.QVBoxLayout(group_box)

            index = self.MW.LoadMRI.file_name[data_index][:-7].split("ind_")[1]
            pattern = f"*ind_{index}*.txt"

            files = glob.glob(os.path.join(os.path.join(self.MW.LoadMRI.session_path,'anat'), pattern))

            if files == []:
                text = QtWidgets.QPlainTextEdit("No transformation file found.")
                text.setReadOnly(True)
                group_layout.addWidget(text)
            else:
                for file in files:
                    container = QWidget()
                    h_layout = QHBoxLayout(container)  # horizontal layout: checkbox + text
                    h_layout.setContentsMargins(0, 0, 0, 0)
                    # Create the checkbox
                    checkbox = QCheckBox()
                    checkbox.setChecked(False)

                    self.checkbox[data_index].append(checkbox)
                    self.transformation_files[data_index].append(file)

                    # Create the text
                    text = QPlainTextEdit(f"Transformation File \n {os.path.basename(file)} \n found")
                    text.setReadOnly(True)

                    # Add them to the layout
                    h_layout.addWidget(checkbox)
                    h_layout.addWidget(text)

                    # Add container to your group layout
                    group_layout.addWidget(container)
            print(self.transformation_files,flush=True)

            file_layout = QtWidgets.QHBoxLayout()
            self.file_line_txt[data_index] = QtWidgets.QPlainTextEdit()
            self.file_line_txt[data_index].setPlaceholderText("Please select other transformation files, if exist.")
            browse_button = QtWidgets.QPushButton("Browse")
            browse_button.clicked.connect(lambda val: self.browse_file(data_index,data_view))
            file_layout.addWidget(self.file_line_txt[data_index])
            file_layout.addWidget(browse_button)
            group_layout.addLayout(file_layout)
            main_layout.addWidget(group_box)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_ok = QPushButton("All Transformation Files Selected")
        btn_cancel = QPushButton("Cancel")

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        main_layout.addLayout(button_layout)


    def browse_file(self,data_index,data_view):
        """
        Opens File Dialog for user to choose anat-file
        """
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "Please select all transformation files for selected data_view",
            "",
            "Text files (*.txt)"
        )
        if len(files)==1:
            transformation_files = [os.path.splitext(f)[0] for f in files]
            #self.transformation_files[data_index] = transformation_files[0]
            self.transformation_files[data_index].append(transformation_files[0])
        elif files:
            self.transformation_files[data_index].append([os.path.splitext(f)[0] for f in files])
        text = "The following files were selected:\n" + "\n".join(files)
        self.file_line_txt[data_index].setPlainText(text)


    def get_values(self):
        """
        Return structured data.
        """
        #transformation_files
        #checked files
        print(self.checkbox,self.transformation_files,flush=True)
        for data_index in self.checkbox:
            idx = 0
            for checkbox in self.checkbox[data_index]:
                print(checkbox.isChecked(),idx,flush=True)
                if checkbox.isChecked()==False:
                    self.transformation_files[data_index].pop(idx)
                    idx -= 1
                idx+=1

        return self.transformation_files




if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = ANAT_InputDialog()
    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        data = dlg.get_values()

