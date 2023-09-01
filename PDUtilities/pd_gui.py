from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
from midiconvert import MidiConverter
import yaml
import os

project_dir = os.path.dirname(os.path.realpath(__file__))    

# Paradiddle GUI
class PD_GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(PD_GUI, self).__init__()
        self.mc = MidiConverter()
        # Sets the window icon
        self.setWindowIcon(QIcon(os.path.join(project_dir, "assets", "favicon.ico")))

        # Loads the .ui file
        uic.loadUi(os.path.join(project_dir, "pd_gui_layout.ui"), self)
        
        # Connecting the Button's frontend to the Button's backend
        # I.E: Everytime button is clicked, call function
        self.selectMidiButton.clicked.connect(self._select_midi_clicked)
        self.selectMidiMappingButton.clicked.connect(self._select_midi_map_clicked)
        self.selectDrumSetButton.clicked.connect(self._select_drum_set_clicked)
        self.convertButton.clicked.connect(self._convert_clicked)
        self.setOutputButton.clicked.connect(self._set_output_clicked)
        self.selectCoverImageButton.clicked.connect(self._select_cover_image_clicked)
        # self.selectDrumTrackButton_1.clicked.connect(self._select_audio_file_clicked)
        # self.calibrationSpinBox.valueChanged.connect(self._calibration_offset_changed)
        
        
        # TODO: May not be an issue, but try to see if there is a better way of doing things
        for i in range(5):
            songTrackBtn = getattr(self, ('selectSongTrackButton_' + str(i+1)), None)
            drumTrackBtn = getattr(self, ('selectDrumTrackButton_' + str(i+1)), None)
            if drumTrackBtn:
                drumTrackBtn.clicked.connect(self._select_audio_file_clicked)
            if songTrackBtn:
                songTrackBtn.clicked.connect(self._select_audio_file_clicked)
        
        self.midiTrackComboBox.currentIndexChanged.connect(self._midi_track_index_changed)
        self.difficultyComboBox.currentTextChanged.connect(self._difficulty_text_changed)
        self.complexityComboBox.currentTextChanged.connect(self._complexity_text_changed)
        
        self.lastOpenFolder = "."
        
        # Loads the default drum set that many custom songs will utilize 
        default_set_file = os.path.join(project_dir, "drum_sets", "defaultset.rlrr")
        self.set_default_set(default_set_file)
        
        self.show()
 
    def set_default_set(self, default_set):
        self.mc.analyze_drum_set(default_set)
        
        self.mc.output_rlrr_dir = "rlrr_files"

        # Sets the last open folder to drum_sets directory
        self.lastOpenFolder = os.path.dirname(default_set)
         
        midi_yaml = os.path.join(project_dir, 'midi_maps', 'pdtracks_mapping.yaml')
        with open(midi_yaml) as file:
            midi_yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
            self.mc.create_midi_map(midi_yaml_dict)
            self.midiMappingLineEdit.setText(os.path.basename(midi_yaml))

    # LOCAL GUI FUNCTIONS

    def _difficulty_text_changed(self, text):
        self.mc.difficulty = text

    def _complexity_text_changed(self, text):
        self.mc.song_complexity = int(text)

    def _select_midi_clicked(self):
        self.midiTrackComboBox.clear()
        self.mc.midi_file = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Files (*.mid *.midi *.kar)"))[0]
        # print(midi_file)
        
        (default_track, default_index) = self.mc.get_default_midi_track()
        self.lastOpenFolder = self.mc.midi_file.rsplit('/', 1)[0]
        self.midiFileLineEdit.setText(self.mc.midi_file.split('/')[-1])
        for i in range(len(self.mc.midi_track_names)):
            item_name = 'Track ' + str(i) + ': ' + self.mc.midi_track_names[i]
            if i >= (self.midiTrackComboBox.count()):
                self.midiTrackComboBox.addItem(item_name)
            else:
                self.midiTrackComboBox.setItemText(i,item_name)
        self.mc.convert_track_index = default_index
        print("Convert track index: " + str(self.mc.convert_track_index))
        self.midiTrackComboBox.setCurrentIndex(self.mc.convert_track_index)

    def _select_midi_map_clicked(self):
        midi_yaml = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Map (*.yaml *yml)"))[0]
        with open(midi_yaml) as file:
            midi_yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
            self.mc.create_midi_map(midi_yaml_dict)
            self.midiMappingLineEdit.setText(midi_yaml.split('/')[-1])
        
    def _set_output_clicked(self):
        output_folder = QFileDialog.getExistingDirectory(self, ("Select Folder"), self.lastOpenFolder)
        print(output_folder)
        self.mc.output_rlrr_dir = output_folder

    def _midi_track_index_changed(self, index):
        self.mc.convert_track_index = index

    def _select_drum_set_clicked(self):
        self.mc.drum_set_file = QFileDialog.getOpenFileName(self, ("Select Drum Set File"), self.lastOpenFolder, ("PD Drum Set Files (*.rlrr)"))[0]
        print(self.mc.drum_set_file)
        self.mc.analyze_drum_set(self.mc.drum_set_file)
        self.lastOpenFolder = self.mc.drum_set_file.rsplit('/', 1)[0]
        self.drumSetLineEdit.setText(self.mc.drum_set_file.split('/')[-1])

    def _select_audio_file_clicked(self):
        sender_name = self.sender().objectName()
        is_drum_track = "Drum" in sender_name
        track_index = int(sender_name.split('_')[-1]) - 1
        audio_file = QFileDialog.getOpenFileName(self, ("Select Audio File"), self.lastOpenFolder, ("Audio Files (*.mp3 *.wav *.ogg)"))[0]
        print(audio_file)
        if is_drum_track:
            self.mc.drum_tracks[track_index] = audio_file
            print(self.mc.drum_tracks)
        else:
            self.mc.song_tracks[track_index] = audio_file
            print(self.mc.song_tracks)

        self.lastOpenFolder = audio_file.rsplit('/', 1)[0]
        line_edit = getattr(self, ('drum' if is_drum_track else 'song') + 'TrackLineEdit_' + str(track_index+1))
        print(line_edit)
        line_edit.setText(audio_file.split('/')[-1])

    def _select_cover_image_clicked(self):
        self.mc.cover_image_path = QFileDialog.getOpenFileName(self, ("Select Cover Image"), self.lastOpenFolder, ("Image Files (*.png *.jpg)"))[0]
        print(self.mc.cover_image_path)
        self.lastOpenFolder = self.mc.cover_image_path.rsplit('/', 1)[0]
        self.coverImageLineEdit.setText(self.mc.cover_image_path.split('/')[-1])

    def _convert_clicked(self):
        self.mc.song_name = self.songNameLineEdit.text()
        # TODO check if we need to escape the \n newline characters ('\n' to '\\n')
        self.statusLabel.setText("Converting...")
        self.statusLabel.repaint()
        self.mc.recording_description = self.descriptionTextEdit.toPlainText() 
        self.mc.artist_name = self.artistNameLineEdit.text()
        self.mc.author_name = self.authorNameLineEdit.text()
        if self.mc.convert_to_rlrr():
            self.statusLabel.setText("Conversion successful!")

    # def calibration_offset_changed(self):
    #     calibration_offset = self.calibrationSpinBox.value()