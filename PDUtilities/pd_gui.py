from packaging import version
from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from midiconvert import MidiConverter
from midicompanion import MidiCompanion
from song_display import SongDisplay_GUI
import mido
import yaml
import json
import os
import requests
import importlib
import time
import threading
import sounddevice
import soundfile

project_dir = os.path.dirname(os.path.realpath(__file__))

# Paradiddle GUI
class PD_GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(PD_GUI, self).__init__()

        check_for_updates()

        self.play_obj = None
        self.mc = MidiConverter()
        self.sd_gui = SongDisplay_GUI(self.mc)
        self.midicompanion = MidiCompanion()
        self.midicompanion.midi_msg_cb = self._midi_msg_callback
        self.midicompanion.connection_cb = self._connection_callback
        # Sets the window icon
        self.setWindowIcon(QIcon(os.path.join(project_dir, "assets", "favicon.ico")))

        # Loads the .ui file
        uic.loadUi(os.path.join(project_dir, "ui_layouts", "pd_gui_layout.ui"), self)
        # self.songCreatorWidget.hide()

        # Load IP address from save json file
        try:
            with open(os.path.join(project_dir, "pdsave.json")) as file:
                pdsave = json.load(file)
                if "ip" in pdsave:
                    self.IPLineEdit.setText(pdsave["ip"])
        except:
            pass

        # Midi Companion Buttons
        self.connectButton.clicked.connect(self._connect_clicked)
        # self.midiInputComboBox.currentIndexChanged.connect(self._midi_input_index_changed)
        self.midiOutputComboBox.currentIndexChanged.connect(self._midi_output_index_changed)
        self.midiInputComboBox.addItems(self.midicompanion.midi_inputs)
        self.midiOutputComboBox.addItems(self.midicompanion.midi_outputs)

        # Connecting the Button's frontend to the Button's backend
        # I.E: Everytime button is clicked, call function
        self.selectMidiButton.clicked.connect(self._select_midi_clicked)
        self.selectMidiMappingButton.clicked.connect(self._select_midi_map_clicked)
        self.selectDrumSetButton.clicked.connect(self._select_drum_set_clicked)
        self.convertButton.clicked.connect(self._convert_clicked)
        self.setOutputButton.clicked.connect(self._set_output_clicked)
        self.selectCoverImageButton.clicked.connect(self._select_cover_image_clicked)

        self.openSongDisplay.triggered.connect(self._open_song_display_clicked)
        # self.songCreatorButton.clicked.connect(self._song_creator_clicked)
        # self.midiCompanionButton.clicked.connect(self._midi_companion_clicked)
        # self.selectDrumTrackButton_1.clicked.connect(self._select_audio_file_clicked)
        # self.calibrationSpinBox.valueChanged.connect(self._calibration_offset_changed)

        # TODO: May not be an issue, but try to see if there is a better way of doing things
        for i in range(5):
            selSongTrackBtn = getattr(self, ('selectSongTrackButton_' + str(i+1)), None)
            selDrumTrackBtn = getattr(self, ('selectDrumTrackButton_' + str(i+1)), None)
            prevSongTrackBtn = getattr(self, ('previewSongTrackButton_' + str(i+1)), None)
            prevDrumTrackBtn = getattr(self, ('previewDrumTrackButton_' + str(i+1)), None)

            if selDrumTrackBtn:
                selDrumTrackBtn.clicked.connect(self._select_audio_file_clicked)
            if selSongTrackBtn:
                selSongTrackBtn.clicked.connect(self._select_audio_file_clicked)
            if prevSongTrackBtn:
                prevSongTrackBtn.clicked.connect(self._preview_audio_file)
            if prevDrumTrackBtn:
                prevDrumTrackBtn.clicked.connect(self._preview_audio_file)
            

        self.midiTrackComboBox.currentIndexChanged.connect(self._midi_track_index_changed)
        self.difficultyComboBox.currentTextChanged.connect(self._difficulty_text_changed)
        self.complexityComboBox.currentTextChanged.connect(self._complexity_text_changed)
        
        # Connect artist name field to update song display title
        self.artistNameLineEdit.textChanged.connect(self._artist_name_changed)

        self.lastOpenFolder = "."

        # Loads the default drum set that many custom songs will utilize
        default_set_file = os.path.join(project_dir, "drum_sets", "defaultset.rlrr")
        self.set_default_set(default_set_file)

        self.show()

    def count_track_notes(self):
        mid = mido.MidiFile(self.mc.midi_file)
        note_count = 0
        for msg in mid.tracks[self.mc.convert_track_index]:
            if msg.type == 'note_on':
                note_count+=1
        return note_count

    def count_all_notes(self):
        mid = mido.MidiFile(self.mc.midi_file)
        note_count = 0
        for i, track in enumerate(mid.tracks):
            for msg in track:
                if msg.type == 'note_on':
                    note_count+=1
        return note_count  

    def closeEvent(self, event):
        if self.midicompanion.connected_to_host:
            self.midicompanion.stopEvent.set()
            self.midicompanion.client_socket.close()

        # Save IP address to json file
        with open(os.path.join(project_dir, "pdsave.json"), "w") as file:
            json.dump({"ip": self.IPLineEdit.text()}, file)

        event.accept()

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
    def _track_song_player(self, audio_path):
        # self.play_obj.play()
        data, fs = soundfile.read(audio_path, dtype="float32")
        sounddevice.play(data[:int(20*fs)], fs)

    def _preview_audio_file(self):
        # Get audio file path
        objName = self.sender().objectName()
        
        if self.play_obj == objName:
            sounddevice.stop()
            self.play_obj = None
            return        
        
        self.play_obj = objName
        indexNum = int(objName[-1])-1
        audio_path = None
        if "Song" in objName:
            audio_path = self.mc.song_tracks[indexNum]
        else:
            audio_path = self.mc.drum_tracks[indexNum]
        
        # Check to see if audio file exists
        if not os.path.exists(audio_path):
            return

        # Play audio file
        thread = threading.Thread(target=self._track_song_player(audio_path))
        thread.start()

    def _open_song_display_clicked(self):
        if not self.mc.midi_file:
            QMessageBox.warning(self, "Warning", "Please select a MIDI file first!")
            return
            
        # Initialize song display with current MIDI file
        self.sd_gui.change_midi(self.mc.midi_file)
        
        # Load all audio tracks from the MIDI converter
        self.sd_gui.load_audio_tracks_from_converter()
            
        self.sd_gui.show()

    def _difficulty_text_changed(self, text):
        self.mc.difficulty = text

    def _complexity_text_changed(self, text):
        self.mc.song_complexity = int(text)

    def _select_midi_clicked(self):
        self.midiTrackComboBox.clear()
        self.mc.midi_file = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Files (*.mid *.midi *.kar)"))[0]
        # print(midi_file)
        if not self.mc.midi_file:  # User cancelled the dialog
            return

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

        self.midiNotesNum.setText(str(self.count_all_notes()))
        self.trackNotesNum.setText(str(self.count_track_notes()))
        
        # Update song display if it's open
        if hasattr(self, 'sd_gui') and self.sd_gui.isVisible():
            self.sd_gui.change_midi(self.mc.midi_file)

    def _select_midi_map_clicked(self):
        midi_yaml = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Map (*.yaml *yml)"))[0]
        if not midi_yaml:  # User cancelled the dialog
            return
        with open(midi_yaml) as file:
            midi_yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
            self.mc.create_midi_map(midi_yaml_dict)
            self.midiMappingLineEdit.setText(midi_yaml.split('/')[-1])
        
        # Update song display with new mapping
        self.sd_gui.change_midi_map(midi_yaml)
        
        self.midiNotesNum.setText(str(self.count_all_notes()))
        self.trackNotesNum.setText(str(self.count_track_notes()))

    def _set_output_clicked(self):
        output_folder = QFileDialog.getExistingDirectory(self, ("Select Folder"), self.lastOpenFolder)
        print(output_folder)
        self.mc.output_rlrr_dir = output_folder

    def _midi_track_index_changed(self, index):
        self.mc.convert_track_index = index
        self.trackNotesNum.setText(str(self.count_track_notes()))

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
        if not self.mc.song_name:
            self.statusLabel.setText('Please proivde a song name!')  #  required
            return
        # TODO check if we need to escape the \n newline characters ('\n' to '\\n')
        self.mc.artist_name = self.artistNameLineEdit.text()
        if not self.mc.artist_name:
            self.statusLabel.setText('Please proivde an artist name!')  # required
            return
        self.statusLabel.setText("Converting...")
        self.statusLabel.repaint()
        self.mc.recording_description = self.descriptionTextEdit.toPlainText()
        self.mc.author_name = self.authorNameLineEdit.text()
        conversion_result_status = self.mc.convert_to_rlrr()
        self.statusLabel.setText(conversion_result_status)

    def _connect_clicked(self):
        if self.midicompanion.connected_to_host:
            self.midicompanion.disconnect_from_host()
        else:
            self.midicompanion.connect_to_host(self.IPLineEdit.text())
        self.connectButton.setText("Disconnect" if self.midicompanion.connected_to_host else "Connect")

    def _midi_input_index_changed(self, index):
        self.midicompanion.midi_input_index = index

    def _midi_output_index_changed(self, index):
        print("index changed to " + str(index))
        self.midicompanion.midi_output_index = index

    def _midi_msg_callback(self, msg):
        self.midiMessageDebugLabel.setText(msg)

    def _connection_callback(self, connected):
        self.midiConnectionStatus.setText("Connected" if connected else "Disconnected")
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

    def _artist_name_changed(self):
        self.sd_gui.update_artist_name(self.artistNameLineEdit.text())

def check_for_updates():
    curVersion = version.parse(importlib.metadata.version("ParadiddleUtilities"))
    try:
        newVersion = version.parse(requests.get("https://api.github.com/repos/emretanirgan/ParadiddleUtilities/releases/latest").json()["tag_name"])
    except requests.exceptions.RequestException as e:
        print(f"Network error checking updates, skipping check: ({e})")
        return

    if newVersion > curVersion:
        widget = QMessageBox()
        widget.setIcon(QMessageBox.Question)
        widget.setWindowTitle("New Update Available")
        widget.setText(f"A new update is available. Would you like to download?\n- New Version: {newVersion}\n- Current Version: {curVersion})")
        widget.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        ret = widget.exec_()

        if ret == widget.Yes:
            import webbrowser
            webbrowser.open("https://www.github.com/emretanirgan/ParadiddleUtilities/releases/latest")
            exit(0)
    
    return