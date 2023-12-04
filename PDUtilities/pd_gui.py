from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
from PyRLRR.rlrr import PyRLRR
from PyRLRR.midiconvert import MidiConverter
from midicompanion import MidiCompanion
import yaml
import json
import os

project_dir = os.path.dirname(os.path.realpath(__file__))    

class MIDICompanion_GUI(QtWidgets.QDialog):
    def __init__(self):
        super(MIDICompanion_GUI, self).__init__()
        self.midicompanion = MidiCompanion()
        self.midicompanion.midi_msg_cb = self._midi_msg_callback
        self.midicompanion.connection_cb = self._connection_callback

        uic.loadUi(os.path.join(project_dir, "interface/midi_companion.ui"), self)


        # Load IP address from save json file
        try:
            with open(os.path.join(project_dir, "pdsave.json")) as file:
                pdsave = json.load(file)
                if "ip" in pdsave:
                    self.IPTextBox.setText(pdsave["ip"])
        except:
            pass


        # Midi Companion Buttons
        self.connectButton.clicked.connect(self._connect_clicked)
        # self.midiInputComboBox.currentIndexChanged.connect(self._midi_input_index_changed)
        self.midiOutputComboBox.currentIndexChanged.connect(self._midi_output_index_changed)
        
        #???
        #self.midiInputComboBox.addItems(self.midicompanion.midi_inputs)

        self.midiOutputComboBox.addItems(self.midicompanion.midi_outputs)

    def closeEvent(self, event):
        if self.midicompanion.connected_to_host:
            self.midicompanion.stopEvent.set()
            self.midicompanion.client_socket.close()
        
        # Save IP address to json file
        with open(os.path.join(project_dir, "pdsave.json"), "w") as file:
            json.dump({"ip": self.IPTextBox.text()}, file)

        event.accept()


    def _connect_clicked(self):
        if self.midicompanion.connected_to_host:
            self.midicompanion.disconnect_from_host()
        else:
            self.midicompanion.connect_to_host(self.IPTextBox.text())
        self.connectButton.setText("Disconnect" if self.midicompanion.connected_to_host else "Connect")

    # ???
    def _midi_input_index_changed(self, index):
        self.midicompanion.midi_input_index = index

    def _midi_output_index_changed(self, index):
        print("index changed to " + str(index))
        self.midicompanion.midi_output_index = index

    def _midi_companion_clicked(self):
        self.show()

    def _midi_msg_callback(self, msg):
        self.midiDebugLabel.setText(msg)

    def _connection_callback(self, connected):
        self.connectionStatusLabel.setText("Connected" if connected else "Disconnected")
        # self.connectButton.setText("Disconnect" if connected else "Connect")
        # self.midiInputComboBox.setEnabled(not connected)
        # self.midiOutputComboBox.setEnabled(not connected)
        # self.IPLineEdit.setEnabled(not connected)
        # self.midiCompanionButton.setEnabled(not connected)
        # self.midiCompanionWidget.setEnabled(not connected)
        # self.midiCompanionWidget.hide()
        # self.songCreatorButton.setEnabled(not connected)
        # self.songCreatorWidget.setEnabled(not connected)
        # self.songCreatorWidget.hide()

    # def calibration_offset_changed(self):
    #     calibration_offset = self.calibrationSpinBox.value()


# Paradiddle GUI
class PD_GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(PD_GUI, self).__init__()
        self.mc = MidiConverter()
        self.mcGUI = MIDICompanion_GUI()
        self.setWindowIcon(QIcon(os.path.join(project_dir, "assets", "favicon.ico")))

        # Loads the .ui file
        uic.loadUi(os.path.join(project_dir, "interface/pd_gui_layout.ui"), self)
        
        # Connecting the Button's frontend to the Button's backend
        # I.E: Everytime button is clicked, call function
        self.midiFileButton.clicked.connect(self._select_midi_clicked)
        self.yamlButton.clicked.connect(self._select_midi_map_clicked)

        self.drumsetButton.clicked.connect(self._select_drum_set_clicked)

        self.convertButton.clicked.connect(self._convert_clicked)

        self.outputButton.clicked.connect(self._set_output_clicked)
        self.coverImageButton.clicked.connect(self._select_cover_image_clicked)

        self.midiCompanionAction.triggered.connect(self.mcGUI._midi_companion_clicked)

        for i in range(5):
            songTrackBtn = getattr(self, ('song' + str(i+1) + 'Button'), None)
            drumTrackBtn = getattr(self, ('drum' + str(i+1) + 'Button'), None)
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
            self.yamlTextBox.setText(os.path.basename(midi_yaml))




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

            self.yamlTextBox.setText(midi_yaml.split('/')[-1])
        
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
        self.drumsetTextBox.setText(self.mc.drum_set_file.split('/')[-1])

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
        line_edit = getattr(self, ('drum' if is_drum_track else 'song') + str(track_index+1) + 'TextBox')
        print(line_edit)
        line_edit.setText(audio_file.split('/')[-1])

    def _select_cover_image_clicked(self):
        self.mc.cover_image_path = QFileDialog.getOpenFileName(self, ("Select Cover Image"), self.lastOpenFolder, ("Image Files (*.png *.jpg)"))[0]
        print(self.mc.cover_image_path)
        self.lastOpenFolder = self.mc.cover_image_path.rsplit('/', 1)[0]
        self.coverImageTextBox.setPlainText(self.mc.cover_image_path.split('/')[-1])

    def _convert_clicked(self):
        self.mc.song_name = self.songNameTextBox.text()
        # TODO check if we need to escape the \n newline characters ('\n' to '\\n')

        self.mc.recording_description = self.descriptionTextBox.toPlainText() 
        self.mc.artist_name = self.artistNameTextBox.text()
        self.mc.author_name = self.charterNameTextBox.text()

        # TODO: Fix this
        if self.mc.convert_to_rlrr():
            pass
