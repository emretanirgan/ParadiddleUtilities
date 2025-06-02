from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import os

project_dir = os.path.dirname(os.path.realpath(__file__))

class SongDisplay_GUI(QtWidgets.QDockWidget):
    def __init__(self, midi_converter=None):
        super(SongDisplay_GUI, self).__init__()
        
        self.setWindowIcon(QIcon(os.path.join(project_dir, "assets", "favicon.ico")))
        uic.loadUi(os.path.join(project_dir, "ui_layouts", "song_display_layout.ui"), self)

    def _playState_changed(self):
        pass

    def _curSongPos_changed(self):
        pass

    def change_midi(self, song_path):
        pass
    
    def change_midi_map(self, midi_map_path):
        pass

    def change_drumset(self, drumset_path):
        pass

    def change_midi_track(self, midi_track):
        pass