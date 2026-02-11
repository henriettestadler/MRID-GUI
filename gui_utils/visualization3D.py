# This Python file uses the following encoding: utf-8
import numpy as np
import SimpleITK as sitk
from PySide6.QtCore import QObject, Property, Signal, QByteArray
import os

class Visualization3D(QObject):
    volumeChanged = Signal()

    def __init__(self, nifti_path):
        super().__init__()
        img = sitk.ReadImage(nifti_path)
        vol = sitk.GetArrayFromImage(img)  # shape (Z, Y, X)

        #self._vol = vol
        #self._size = (vol.shape[2], vol.shape[1], vol.shape[0])
        #self._bytes = QByteArray(vol.tobytes())

        # Inside your Visualization3D __init__
        vol = vol.astype(np.float32)

        # Robust normalization: clip top 1% to handle outliers
        q_min, q_max = np.percentile(vol, [0.5, 99.5])
        vol = np.clip(vol, q_min, q_max)
        vol = (vol - q_min) / (q_max - q_min + 1e-8)

        # Ensure the memory layout is exactly what OpenGL/Vulkan wants
        self._bytes = QByteArray(np.ascontiguousarray(vol, dtype=np.float32).tobytes())

        # 1. Normalize
        #vol = vol.astype(np.float32)
        #vol -= vol.min()
        #vol /= (vol.max() + 1e-8)

        # 2. IMPORTANT: Match the dimensions QML expects
        # We store the shape so QML knows where one slice ends and the next begins
        self._size = (vol.shape[2], vol.shape[1], vol.shape[0])

        qml_folder = os.path.dirname(os.path.abspath("gui_utils/volumer_viewer.qml"))
        frag_file = os.path.join(qml_folder, "volume.frag")

        print(f"--- PATH CHECK ---")
        print(f"QML Folder: {qml_folder}")
        print(f"Fragment Shader Path: {frag_file}")
        print(f"Does .frag exist? {' YES' if os.path.exists(frag_file) else ' NO - MOVE THE FILE HERE'}")
        print(f"------------------")

        # 3. Force "C-Contiguous" memory (Point 2)
        # This ensures the bytes are laid out perfectly in order for the GPU
        #self._bytes = QByteArray(np.ascontiguousarray(vol, dtype=np.float32).tobytes())

    @Property(QByteArray, notify=volumeChanged)
    def volumeData(self):
        return self._bytes

    @Property(int, constant=True)
    def sizeX(self):
        return self._size[0]

    @Property(int, constant=True)
    def sizeY(self):
        return self._size[1]

    @Property(int, constant=True)
    def sizeZ(self):
        return self._size[2]


#self.volume_provider = Visualization3D(save_path)
#self.vtkWidget_data13.engine.rootContext().setContextProperty("VolumeProvider", self.volume_provider)
#self.vtkWidget_data13.engine.load("volume_viewer.qml")
