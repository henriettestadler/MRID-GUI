# This Python file uses the following encoding: utf-8
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtCore import QUrl
import subprocess
import json
from PySide6.QtWidgets import QStyle

class VideoPlayer:
    def __init__(self,MW,filename):
        self.MW = MW
        self.MW.ui.stackedWidget_video.setCurrentIndex(0)

        self.get_frame_rate(filename)
        self.MW.ui.spinBox_frame.valueChanged.connect(self.seek_frame)
        self.MW.ui.pushButton_videoPlay.clicked.connect(self.play_pause)

        self.player = QMediaPlayer()
        self.player.setSource(QUrl.fromLocalFile(filename))
        self.player.play()
        self.currently_play = True
        self.player.setVideoOutput(self.MW.ui.widget_video)

    def get_frame_rate(self,filename):
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", filename],
            capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        stream = info["streams"][0]
        num, den = stream["r_frame_rate"].split("/")
        self.frame_rate = int(num) / int(den)
        self.MW.ui.spinBox_frame.setMaximum(int(stream["nb_frames"])) #total frames

    def play_pause(self):
        if self.currently_play:
            self.player.pause()
            self.currently_play = False
            icon = self.MW.style().standardIcon(QStyle.SP_MediaPause)
            self.MW.ui.pushButton_videoPlay.setIcon(icon)
        else:
            self.player.play()
            self.currently_play = True
            icon = self.MW.style().standardIcon(QStyle.SP_MediaPlay)
            self.MW.ui.pushButton_videoPlay.setIcon(icon)



    def seek_frame(self, frame):
        ms = int((frame / self.frame_rate) * 1000)
        self.player.setPosition(ms)
