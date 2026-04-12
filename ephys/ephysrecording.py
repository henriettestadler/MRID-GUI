# This Python file uses the following encoding: utf-8
from neo.io import NeuroScopeIO
from dataclasses import dataclass
import xml.etree.ElementTree as ET

@dataclass
class EphysRecording:
    file_path: str
    read_data: NeuroScopeIO
    #segment: neo.Segment        # lazy-loaded
    #channels: list[int]         # from XML
    t_start: float
    t_stop: float
    all_channels: list[int]
    active_channels: list[int]
    dead_channels: list[int]


    @classmethod
    def from_file(cls, file_path: str) -> "EphysRecording":
        all_channels, active_channels, dead_channels = cls.open_xml_file(file_path)

        reader = NeuroScopeIO(file_path)
        read_data = reader.read_segment(lazy=True)

        t_start = read_data.analogsignals[0].t_start
        t_stop = read_data.analogsignals[0].t_stop

        return cls(
            file_path=file_path,
            #segment=None,
            read_data=read_data,
            all_channels=all_channels,
            active_channels=active_channels,
            dead_channels = dead_channels,
            t_start=t_start,
            t_stop=t_stop,
        )



    @staticmethod
    def open_xml_file(filename):
        xml_path = filename.replace('.dat', '.xml')
        tree = ET.parse(xml_path)
        root = tree.getroot()
        active_channels = {}
        skipped = {}
        all_channels= {}

        for group_idx, group in enumerate(root.findall('.//group')):
            active_channels[group_idx] = []
            skipped[group_idx] = []
            all_channels[group_idx] = []
            for ch in group.findall('channel'):
                ch_id = int(ch.text)
                skip  = int(ch.get('skip', 0))
                if skip == 0:
                    active_channels[group_idx].append(ch_id)
                else:
                    skipped[group_idx].append(ch_id)
                all_channels[group_idx].append(ch_id)
        return all_channels, active_channels, skipped
