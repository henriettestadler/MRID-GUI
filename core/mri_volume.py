# This Python file uses the following encoding: utf-8
from dataclasses import dataclass, field
import numpy as np
import SimpleITK as sitk

@dataclass
class MRIVolume:
    file_path: str
    slices: dict
    array_4d: np.ndarray | None = None
    spacing: tuple = ()
    axes_to_flip: list = field(default_factory=list)
    ref_image: object = None  # sitk.Image
    is_4d: bool = False
    timestamp4D: list = field(default_factory=list)


    @classmethod
    def from_file(cls, file_path: str) -> "MRIVolume":
        image = sitk.ReadImage(file_path)
        array = sitk.GetArrayFromImage(image)

        is_4d = array.ndim == 4
        axes_to_flip = cls._compute_axes_to_flip(image, is_4d)
        spacing = image.GetSpacing()[::-1]
        if is_4d:
            spacing = spacing[1:4]

        array_4d = None
        timestamp4D = []
        if is_4d:
            flipped_volumes = []
            for t in range(image.GetSize()[3]):
                img_flipped = sitk.Flip(image[:, :, :, t], axes_to_flip, flipAboutOrigin=True)
                flipped_volumes.append(sitk.GetArrayFromImage(img_flipped))
            array_4d = np.stack(flipped_volumes)
            timestamp4D = [0, 4, 7] if array_4d.shape[0] > 7 else [0, 2, 5]
            slices = {
                    0: array_4d[timestamp4D[0], :, :, :].copy(),
                    1: array_4d[timestamp4D[1], :, :, :].copy(),
                    2: array_4d[timestamp4D[2], :, :, :].copy(),
                }
        else:
            img_flipped = sitk.Flip(image, axes_to_flip, flipAboutOrigin=False)
            flipped = sitk.GetArrayFromImage(img_flipped)
            slices = {0: flipped, 1: flipped, 2: flipped}


        return cls(
            file_path=file_path,
            slices=slices,
            ref_image=image,
            is_4d=(array.ndim == 4),
            axes_to_flip=axes_to_flip,
            spacing=spacing,
            array_4d=array_4d,
            timestamp4D = timestamp4D,
        )


    @staticmethod
    def _compute_axes_to_flip(image: sitk.Image, is_4d: bool) -> list[bool]:
        img_dir = np.array(image.GetDirection())
        if is_4d:
            img_dir = img_dir.reshape(4, 4)
            img_dir_max = [img_dir[:, i][np.argmax(np.abs(img_dir[:, i]))] for i in range(4)]
            axes = [bool(img_dir_max[i] < 0) for i in range(3)]
        else:
            img_dir = img_dir.reshape(3, 3)
            img_dir_max = [max(col, key=abs) for col in zip(*img_dir)]
            axes = [bool((img_dir_max[i] < 0 and i != 2) or (img_dir_max[i] > 0 and i == 2))
                            for i in range(3)]
        axes[2] = False  # z-axis never flipped
        return axes