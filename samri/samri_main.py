# import samri
from samri.pipelines.reposit import bru2bids
from samri.pipelines.extra_functions import get_data_selection
from samri.pipelines.diagnostics import diagnose
from samri.pipelines.preprocess import generic, structural
from samri.pipelines.glm import l1
import bids
import os
from subprocess import call
import data_fetcher
import sys
import glob


sys.path
sys.path.append('/Users/mri_registration/.local/bin/Bru2')
base_path="/Users/mri_registration/SAMRI/samri_output/"

server = ""
password = ""

animal_id = ""

# Enables bru2bids
bids_flag = True
# Enables registering
register = False


# Registers post-op images to pre-op images
presurgery = False
# Enables elastic registering
elastic = True
register_key = ["TurboRARE"]
num_threads = 8
tasks = ["coronal"]
working_session = ""


# Sessions to be excluded
sessions = [""]

# Moving image mask
moving_img_mask_name=""

moving_img_mask_path = os.path.join(base_path, animal_id, "bids", "sub-"+animal_id, "ses-"+working_session,"anat", moving_img_mask_name)



# Raw data to bids conversion
raw_base = "./samri_bindata/"+ animal_id
if not os.path.exists(raw_base):
    os.makedirs(raw_base)

# bids_base = "./samri_output/" + animal_id + interm + session
bids_base = "./samri_output/" + animal_id
call(['rm','-rf',raw_base+'/.DS_Store'])

atlas = "/Users/mri_registration/SAMRI/WHS_SD_rat_atlas_v4_pack/WHS_SD_rat_T2star_v1.01.nii.gz"
atlas_mask="/Users/mri_registration/SAMRI/WHS_SD_rat_atlas_v4_pack/WHS_SD_v2_brainmask_bin.nii.gz"

A = get_data_selection(raw_base)
data_fetcher.main(server=server, password=password, local_path=raw_base, animal_id=animal_id)

if bids_flag:
    # for file in bids_base:
    exclude_sessions = [""]
    if os.path.exists(bids_base):
        print("Checking the existing sessions")
        for file in os.listdir(bids_base+"/bids/sub-"+animal_id):
            filename = os.fsdecode(file)
            if filename.startswith("ses-"):
                exclude_sessions.append(filename.split("ses-")[-1])
    print("Creating bids dataset")
    print("Sessiongs to be excluded:")
    print(exclude_sessions)
    bru2bids(raw_base,
            #functional_match={"acquisition": ["geEPI"]},
             # structural_match={"acquisition": ["T2starMapMGE"]},
            structural_match={"acquisition": ["TurboRARE", "UTE","TOF", "T1Flash", "T2TurboRARE", "T2TurboRAREhighRes", "T2MapMSME", "RAREInvRec", "TurboRARE3D", "T2starMapMGE"]},
            out_base=bids_base,
            exclude={"session": exclude_sessions},
            keep_work=True,
            )


# Run Diagnostics
# print(bids_base)
# diagnose(bids_base+"/bids/sub-rTBY38")


print("sessions to be excluded:\n")
print(sessions)

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
