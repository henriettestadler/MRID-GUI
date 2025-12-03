# Developing a unified GUI for electrode trajectory planning and MRID-tag based localisation

This repository contains a unified graphical user interface (GUI) for the Neurotechnology Group, a joint lab of UZH and ETH Zurich.

Currently, the GUI focuses on electrode trajectory planning and magnetic resonance identification (MRID)-tag based localisation, but it is planned to expand its functionality in near future.

## MRID-tag localization
MRID-tags are tiny Magnetic Resonance Imaging(MRI)-visible barcodes integrated into electrode bundles, which are implanted inside brains. Precise identification of the implant's tag location and brain region is essential for accurately analysing the experimental data and correctly assigning the recorded neural signals. 

The precise localisation process can be divided into several smaller steps: 
First, pre-surgery 3D data is resampled, and the post-surgery 4D data is registered to the 3D data.
Secondly, label masks are created by the user to highlight the anatomical regions and MRID-tags. These masks are then used to generate contrast heatmaps to eventually find the Gaussian centres of each tag. As final step, the found centres from the MRI scans are best-fit to the real MRID-tag geometry implanted into the animal's brain.



