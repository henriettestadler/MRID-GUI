# This Python file uses the following encoding: utf-8
from neo.io import NeuroScopeIO
from dataclasses import dataclass
import xml.etree.ElementTree as ET

@dataclass
class EphysRecording:
    file_path: str
    read_data: object
    t_start: float
    t_stop: float
    all_channels: list[int]
    active_channels: list[int]
    dead_channels: list[int]
    xml_path: str


    @classmethod
    def from_file(cls, file_path: str, group_idx:int) -> "EphysRecording":
        all_channels, active_channels, dead_channels,xml_path = cls.open_xml_file(file_path,group_idx)

        read_data,t_start,t_stop = cls.read_dat_data(file_path)

        return cls(
            file_path=file_path,
            #segment=None,
            read_data=read_data,
            all_channels=all_channels,
            active_channels=active_channels,
            dead_channels = dead_channels,
            t_start=t_start,
            t_stop=t_stop,
            xml_path=xml_path,
        )

    @staticmethod
    def read_dat_data(file_path:str):
        reader = NeuroScopeIO(file_path)
        read_data = reader.read_segment(lazy=True)

        t_start = read_data.analogsignals[0].t_start
        t_stop = read_data.analogsignals[0].t_stop

        return read_data,t_start,t_stop


    @staticmethod
    def open_xml_file(file_path:str,group_idx:int):
        xml_path = file_path.replace('.dat', '.xml')
        tree = ET.parse(xml_path)
        root = tree.getroot()
        active_channels = []
        skipped = []
        all_channels = []

        for idx, group in enumerate(root.findall('.//group')):
            if idx != group_idx:
                continue
            for ch in group.findall('channel'):
                ch_id = int(ch.text)
                skip  = int(ch.get('skip', 0))
                if skip == 0:
                    active_channels.append(ch_id)
                else:
                    skipped.append(ch_id)
                all_channels.append(ch_id)
        return all_channels, active_channels, skipped,xml_path
