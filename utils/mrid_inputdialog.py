from PySide6 import QtWidgets
import sys
from PySide6.QtWidgets import QFileDialog
from file_handling.loadimage_into4D import LoadImage4D
import os

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

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        text = QtWidgets.QPlainTextEdit("Please enter the Anatomical Regions and MRID Tags and Islands. \n"
                                        "After selecting, please activate the Brush and paint the anatomical regions. \n")
        text.setReadOnly(True)
        text.setFixedSize(400, 100)
        main_layout.addWidget(text)

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

        #Or upload labels.txt
        file_layout = QtWidgets.QHBoxLayout()
        self.file_line_edit = QtWidgets.QLineEdit()
        self.file_line_edit.setPlaceholderText("Or select an existing labels.txt file")  # optional
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_line_edit)
        file_layout.addWidget(browse_button)
        main_layout.addLayout(file_layout)


        #buttons
        button_layout = QtWidgets.QHBoxLayout()
        # Add a small text label
        label = QtWidgets.QLabel("Press OK if data is correct and start painting \n"
            "the anatomical regions. Press Done in the \n"
            "bottom right corner once it is done!")
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

    def browse_file(self):
        """
        Opens File Dialog for user to choose labels.txt
        """
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
        self.MW.LoadMRI.LoadImage4D.open_file(file_name,data_view=None)



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
