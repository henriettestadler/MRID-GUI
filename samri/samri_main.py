# import samri
from samri.samri.pipelines.reposit import bru2bids
from samri.samri.pipelines.extra_functions import get_data_selection
from samri.samri.pipelines.diagnostics import diagnose
from samri.samri.pipelines.preprocess import generic, structural
from samri.samri.pipelines.glm import l1
import bids
import os
from subprocess import call
import samri.data_fetcher as data_fetcher
import sys
import glob
import json

from PySide6 import QtWidgets
from PySide6.QtWidgets import QDialog

class InitSAMRI:
    def __init__(self,MW):
        ## get all data!
        sys.path
        sys.path.append('/Users/mri_registration/.local/bin/Bru2')
        dlg_samri = SAMRI_InputDialog(MW)
        if dlg_samri.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            samri_input = dlg_samri.get_values()
        else:
            return

        base_path= samri_input['base_path'] #"/Users/mri_registration/SAMRI/samri_output/"

        server = samri_input['server']
        password = samri_input['password']
        animal_id = samri_input['animal_id']

        # Enables bru2bids
        bids_flag = samri_input['bids_flag'] #True
        # Enables registering
        register = samri_input['register'] #False

        # Registers post-op images to pre-op images
        presurgery = samri_input['presurgery'] #False
        # Enables elastic registering
        elastic = samri_input['elastic'] #True
        register_key = samri_input['register_key'] #["TurboRARE"]
        num_threads = samri_input['num_threads'] #8
        tasks = samri_input['tasks'] #["coronal"]
        working_session = samri_input['working_session']

        # Sessions to be excluded
        sessions = samri_input['sessions_excluded']

        # Moving image mask
        moving_img_mask_name = samri_input['moving_img_mask_name']
        moving_img_mask_path = os.path.join(base_path, animal_id, "bids", "sub-"+animal_id, "ses-"+working_session,"anat", moving_img_mask_name)

        # Raw data to bids conversion
        raw_base = samri_input['raw_base'] + animal_id #"./samri_bindata/"+ animal_id
        if not os.path.exists(raw_base):
            os.makedirs(raw_base)

        # bids_base = "./samri_output/" + animal_id + interm + session
        bids_base = samri_input['raw_base'] + animal_id #"./samri_output/" + animal_id
        call(['rm','-rf',raw_base+'/.DS_Store'])

        atlas = samri_input['moving_img_mask_name'] + 'WHS_SD_rat_T2star_v1.01.nii.gz' #"/Users/mri_registration/SAMRI/WHS_SD_rat_atlas_v4_pack/WHS_SD_rat_T2star_v1.01.nii.gz"
        atlas_mask= samri_input['moving_img_mask_name'] + 'WHS_SD_v2_brainmask_bin.01.nii.gz' #"/Users/mri_registration/SAMRI/WHS_SD_rat_atlas_v4_pack/WHS_SD_v2_brainmask_bin.nii.gz"

        #A = get_data_selection(raw_base)
        data_fetcher.main(server=server, password=password, local_path=raw_base, animal_id=animal_id)

        return

        if bids_flag:
            # for file in bids_base:
            exclude_sessions = [""]
        if os.path.exists(bids_base):
            ## ADDED THIS; NOT SURE IF VALID?
            if os.path.exists(bids_base+"/bids/sub-"+animal_id):
                for file in os.listdir(bids_base+"/bids/sub-"+animal_id):
                    filename = os.fsdecode(file)
                    if filename.startswith("ses-"):
                        exclude_sessions.append(filename.split("ses-")[-1])

        bru2bids(raw_base,
                #functional_match={"acquisition": ["geEPI"]},
                 # structural_match={"acquisition": ["T2starMapMGE"]},
                structural_match={"acquisition": ["TurboRARE", "UTE","TOF", "T1Flash", "T2TurboRARE", "T2TurboRAREhighRes", "T2MapMSME", "RAREInvRec", "TurboRARE3D", "T2starMapMGE"]},
                out_base=bids_base,
                exclude={"session": exclude_sessions},
                keep_work=True,
                )

        return
        # Run Diagnostics
        # print(bids_base)
        # diagnose(bids_base+"/bids/sub-rTBY38")

        if register:
            structural(bids_base=bids_base,
                   template=atlas,
                   out_base=bids_base+'/results',
                   presurgery=presurgery,
                   structural_match={"acquisition": register_key, "task": tasks, "type": ["anat"]},
                   debug=True,
                   keep_work=True,
                   elastic=elastic,
                   moving_img_mask=moving_img_mask_path,
                   registration_mask=atlas_mask,
                   num_threads=num_threads,
                   # reference_template=reference_template
                   # presurgery_template=presurgery_atlas,
                   exclude={"session": sessions}
                   )




class SAMRI_InputDialog(QDialog):
    def __init__(self, MW,parent=None):
        super().__init__(parent)
        self.MW = MW
        self.setWindowTitle("SAMRI Configuration")
        self.setMinimumWidth(600)
        self.setMinimumHeight(800)
        main_layout = QtWidgets.QVBoxLayout(self)

        # Scroll area for all fields
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(container)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # --- Fields ---
        self.bru2_path, bru2_widget = self.make_path_row("/Users/mri_registration/.local/bin/Bru2")
        self.base_path, base_widget = self.make_path_row("/Users/mri_registration/SAMRI/samri_output/")
        self.raw_base, rawbase_widget = self.make_path_row("./samri_bindata/")
        self.atlas, atlas_widget = self.make_path_row("/home/neurox/Documents/MRID-GUI/Files/Atlas")
        with open('samri/bruker_info.json') as f:
            bruker_info = json.load(f)
        self.server       = QtWidgets.QLineEdit(bruker_info["server"])
        self.password     = QtWidgets.QLineEdit(bruker_info["password"])
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.animal_id    = QtWidgets.QLineEdit()
        self.working_session   = QtWidgets.QLineEdit()
        self.sessions_excluded = QtWidgets.QLineEdit("")  # comma-separated
        #self.register_key = QtWidgets.QLineEdit("TurboRARE")  # comma-separated
        self.register_key = QtWidgets.QComboBox()
        self.register_key.addItems(["TurboRARE", "UTE", "TOF", "T1Flash", "T2TurboRARE",
                                     "T2TurboRAREhighRes", "T2MapMSME", "RAREInvRec",
                                     "TurboRARE3D", "T2starMapMGE"])

        # Tasks
        self.tasks = QtWidgets.QComboBox()
        self.tasks.addItems(["coronal", "sagittal", "axial"])

        #self.tasks        = QtWidgets.QLineEdit("coronal")    # comma-separated
        self.num_threads  = QtWidgets.QSpinBox()
        self.num_threads.setValue(int(os.cpu_count()-3)) #29
        self.num_threads.setRange(1, int(os.cpu_count()-3)) #29
        self.moving_img_mask_name = QtWidgets.QLineEdit()


        self.bids_flag  = QtWidgets.QCheckBox()
        self.bids_flag.setChecked(True)
        self.register   = QtWidgets.QCheckBox()
        self.register.setChecked(False)
        self.presurgery = QtWidgets.QCheckBox()
        self.presurgery.setChecked(False)
        self.elastic    = QtWidgets.QCheckBox()
        self.elastic.setChecked(True)

        # --- Add to form ---
        form.addRow("Bru2 path:",           bru2_widget)
        form.addRow("Base path:",           base_widget)
        form.addRow("Raw Base:",            rawbase_widget)
        form.addRow("Atlas Files:",         atlas_widget)
        form.addRow("Server:",              self.server)
        form.addRow("Password:",            self.password)
        form.addRow("Animal ID:",           self.animal_id)
        form.addRow("Working session:",     self.working_session)
        form.addRow("Excluded sessions:",   self.sessions_excluded)
        form.addRow("Register key:",        self.register_key)
        form.addRow("Tasks:",               self.tasks)
        form.addRow("Num threads:",         self.num_threads)
        form.addRow("Moving mask:",         self.moving_img_mask_name)
        form.addRow("Enable bids_flag:",    self.bids_flag)
        form.addRow("Register:",            self.register)
        form.addRow("Presurgery:",          self.presurgery)
        form.addRow("Elastic:",             self.elastic)

        # --- OK / Cancel ---
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def make_path_row(self, default_path):
        """Creates a QLineEdit + Browse button in an HBoxLayout."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        line_edit = QtWidgets.QLineEdit(default_path)
        btn = QtWidgets.QPushButton("Browse")
        btn.clicked.connect(lambda: self.browse_path(line_edit))
        layout.addWidget(line_edit)
        layout.addWidget(btn)
        return line_edit, container

    def browse_path(self, line_edit):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder", line_edit.text())
        if path:
            line_edit.setText(path)


    def get_values(self):
        """Call after exec() to retrieve all values."""
        animal_id = self.animal_id.text()
        working_session = self.working_session.text()
        base_path = self.base_path.text()


        return {
            "bru2_path":            self.bru2_path.text(),
            "base_path":            base_path,
            "server":               self.server.text(),
            "password":             self.password.text(),
            "animal_id":            animal_id,
            "working_session":      working_session,
            "sessions_excluded":    [s.strip() for s in self.sessions_excluded.text().split(",")],
            #"register_key":         [k.strip() for k in self.register_key.text().split(",")],
            "register_key":         [self.register_key.currentText()],
            "tasks":                [self.tasks.currentText()],
            "num_threads":          self.num_threads.value(),
            "moving_img_mask_name": self.moving_img_mask_name.text(),
            "bids_flag":            self.bids_flag.isChecked(),
            "register":             self.register.isChecked(),
            "presurgery":           self.presurgery.isChecked(),
            "elastic":              self.elastic.isChecked(),
            "raw_base":             self.raw_base.text(),
            "atlas_folder":         self.atlas.text(),
        }


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dlg = SAMRI_InputDialog()
