# This Python file uses the following encoding: utf-8
from dataclasses import dataclass
import os
import numpy as np
import pandas as pd

@dataclass
class MRIDInfo:
    mrid_tags: list[str]
    totalatlasCoordinates_pkl: list[int]
    mrid_idx_xml: int
    mrid: str
    mrid_coordinates: list[int]


    @classmethod
    def from_file(cls, file_path: str,group_idx=0) -> "MRIDInfo":
        session_path = os.path.dirname(os.path.dirname(file_path))
        mrid_idx_xml=group_idx
        mrid_tags,totalatlasCoordinates_pkl,mrid_idx_xml,mrid,mrid_coordinates = cls.get_mrid_tag(session_path,mrid_idx_xml)

        return cls(
            mrid_tags=mrid_tags,
            totalatlasCoordinates_pkl=totalatlasCoordinates_pkl,
            mrid_idx_xml=mrid_idx_xml,
            mrid=mrid,
            mrid_coordinates=mrid_coordinates,
        )


    @staticmethod
    def get_mrid_tag(session_path,mrid_idx_xml):
        mrid_tags = [f.name for f in os.scandir(os.path.join(session_path,"analysed")) if f.is_dir()]

        mrid_coordinates = {}
        for idx, mrid in enumerate(mrid_tags):
            coords = np.load(os.path.join(session_path,"analysed",mrid,"gaussian_centers_3D.npy"))
            print(mrid,flush=True)
            mrid_coordinates[mrid]=coords[0][0]

        #Atlas Coordinate System: RAS -> higher X = more Right
        mrid_coordinates = dict(sorted(mrid_coordinates.items(), key=lambda item: item[1], reverse=True))
        mrid_tags = list(mrid_coordinates.keys())
        # get coordinates, set to 0 by default
        mrid = list(mrid_coordinates.keys())[mrid_idx_xml]  #'trio' #A->0

        totalatlasCoordinates_pkl =  []

        for mrid_tag in mrid_tags:
            points_electrodes_path = os.path.join(os.path.join(session_path,"analysed"),mrid_tag,'channel_atlas_coordinates.xlsx')
            points_data = pd.read_excel(points_electrodes_path,header=0)[['Atlas x','Atlas y','Atlas z']].values
            totalatlasCoordinates_pkl.append([points_data[0],points_data[-1]])

        return mrid_tags,totalatlasCoordinates_pkl,mrid_idx_xml,mrid,mrid_coordinates