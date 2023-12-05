from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
from PyRLRR.rlrr import RLRR
from PyRLRR.midiconvert import MidiConverter, Difficulties
from midicompanion import MidiCompanion
from mido import MidiFile
from mido.messages import Message
import yaml
import json
import os

project_dir = os.path.dirname(os.path.realpath(__file__))    

class MIDICompanion_GUI(QtWidgets.QDialog):
    def __init__(self):
        super(MIDICompanion_GUI, self).__init__()
        self.midicompanion = MidiCompanion()
        # TODO: Figure out what these are
        self.midicompanion.midi_msg_cb = self._midi_msg_callback
        self.midicompanion.connection_cb = self._connection_callback

        uic.loadUi(os.path.join(project_dir, "interface/midi_companion.ui"), self)


        # TODO: Place this within PyRLRR
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
        
        #???
        # self.midiInputComboBox.currentIndexChanged.connect(self._midi_input_index_changed)
        
        self.midiOutputComboBox.currentIndexChanged.connect(self._midi_output_index_changed)
        
        #???
        #self.midiInputComboBox.addItems(self.midicompanion.midi_inputs)

        self.midiOutputComboBox.addItems(self.midicompanion.midi_outputs)

    def closeEvent(self, event):
        if self.midicompanion.connected_to_host:
            self.midicompanion.stopEvent.set()
            self.midicompanion.client_socket.close()
        
        # TODO: Replace with PyRLRR Function for MIDICompanion
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
    # def _midi_input_index_changed(self, index):
    #     self.midicompanion.midi_input_index = index

    def _midi_output_index_changed(self, index):
        # print("index changed to " + str(index))
        self.midicompanion.midi_output_index = index

    def _midi_companion_clicked(self):
        self.show()

    def _midi_msg_callback(self, msg):
        self.midiDebugLabel.setText(msg)


    # TODO: Either remove this or add loading text for when it's still connecting
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
        self.lastOpenFolder = "."

        # TODO: Do we need this
        self.mc = MidiConverter()

        self.mcGUI = MIDICompanion_GUI()
        self.chartDirs = []
        self.setWindowIcon(QIcon(os.path.join(project_dir, "assets", "favicon.ico")))

        # Loads the .ui file
        uic.loadUi(os.path.join(project_dir, "interface/pd_gui_layout.ui"), self)
        

        # MIDI Tab
        self.midiFileButton.clicked.connect(self._select_midi_clicked)
        self.midiTrackComboBox.currentIndexChanged.connect(self._midi_track_index_changed)
        # TODO: We are missing the ghost notes and accent notes buttons

        self.convertButton.clicked.connect(self._convert_button_clicked)
        # We are missing the functionality for the chart list


        # Menu Bar
        self.midiCompanionAction.triggered.connect(self.mcGUI._midi_companion_clicked)
        self.openChartAction.triggered.connect(self._open_charts_clicked)
        self.importChartAction.triggered.connect(self._import_charts_clicked)

        # Audio Tab
        for i in range(5):
            songTrackBtn = getattr(self, ('song' + str(i+1) + 'Button'), None)
            drumTrackBtn = getattr(self, ('drum' + str(i+1) + 'Button'), None)
            if drumTrackBtn:
                drumTrackBtn.clicked.connect(self._select_audio_file_clicked)
            if songTrackBtn:
                songTrackBtn.clicked.connect(self._select_audio_file_clicked)

        self.yamlButton.clicked.connect(self._select_midi_map_clicked)
        self.drumsetButton.clicked.connect(self._select_drum_set_clicked)

        # Metadata Tab
        self.difficultyComboBox.currentTextChanged.connect(self._difficulty_text_changed)
        self.difficultyComboBox.addItems(["Easy", "Medium", "Hard", "Expert"])
        self.complexityComboBox.currentTextChanged.connect(self._complexity_text_changed)
        self.complexityComboBox.addItems(["1", "2", "3", "4", "5"])
        
        self.outputButton.clicked.connect(self._set_output_clicked)
        self.coverImageButton.clicked.connect(self._select_cover_image_clicked)
        
        # Loads the default drum set that many custom songs will utilize 
        # TODO: Why tf does the drum has an arg but the yaml doesn't??
        default_set_file = os.path.join(project_dir, "drum_sets", "defaultset.rlrr")
        self.set_default_set(default_set_file)
        
        # TODO: Should we put this within main??
        self.show()
 
    def set_default_set(self, default_set):
        # TODO: We dont need this before conversion
        self.mc.analyze_drum_set(default_set)
        
        # TODO: We either don't need this or PyRLRR should contain this
        self.mc.output_rlrr_dir = "rlrr_files"

        self.lastOpenFolder = os.path.dirname(default_set)
         
        # TODO: We don't need this before conversion
        midi_yaml = os.path.join(project_dir, 'midi_maps', 'pdtracks_mapping.yaml')
        with open(midi_yaml) as file:
            midi_yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
            self.mc.create_midi_map(midi_yaml_dict)

        # TODO: Drumset textbox doesn't have setText function in here
        
        self.yamlTextBox.setText(os.path.basename(midi_yaml))




    # LOCAL GUI FUNCTIONS
    def _difficulty_text_changed(self, text):
        self.mc.difficulty = text

    def _convert_button_clicked(self):
        pass
    
    # FIXME: This is a mess
    def _open_charts_clicked(self):
        self.chartDirs = []
        
        folder = QFileDialog.getExistingDirectory(self, "Select Chart Directories ...Bruh...")
        subdirectories = [x.path for x in os.scandir(folder) if os.path.isdir(x)]
        for directory in subdirectories:
            baseDir = os.path.basename(directory)
            convertedChart = RLRR(directory)
            filePath = ""
            for file in os.listdir(directory):
                if file.endswith(".mid"):
                    filePath = file
                    break
            if (filePath == ""):
                continue
            
            outputDir = os.path.join(os.getcwd(), baseDir)
            for comp in Difficulties:
                convertedChart.metadata.complexity = comp.value
                convertedChart.parse_midi(os.path.join(directory, filePath))
                # Add to editable list
            self.chartDirs.append(directory)
        
        # Update everything!!!!
        pass
    
    # FIXME: This is a mess
    def _import_charts_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Chart Directories ...Bruh...")
        subdirectories = [x.path for x in os.scandir(folder) if os.path.isdir(x)]
        for directory in subdirectories:
            baseDir = os.path.basename(directory)
            convertedChart = RLRR(directory)
            filePath = ""
            for file in os.listdir(directory):
                if file.endswith(".mid"):
                    filePath = file
                    break
            if (filePath == ""):
                continue
            
            outputDir = os.path.join(os.getcwd(), baseDir)
            for comp in Difficulties:
                convertedChart.metadata.complexity = comp.value
                convertedChart.parse_midi(os.path.join(directory, filePath))
                # Add to editable list
            self.chartDirs.append(directory)
        
        # Update everything!!!!

    # TODO: What???
    # So other things can have different indexes, but this needs different text?
    def _complexity_text_changed(self, text):
        self.mc.song_complexity = int(text)

    def _select_midi_clicked(self):
        self.mc.midi_file = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Files (*.mid *.midi *.kar)"))[0]
        # print(midi_file)
        
        if (self.mc.midi_file == ""):
            return
        self.midiTrackComboBox.clear()

        self.mc.get_tracks()
        (default_track, default_index) = self.mc.get_drum_track()
        self.lastOpenFolder = self.mc.midi_file.rsplit('/', 1)[0]
        self.midiFileTextBox.setText(self.mc.midi_file.split('/')[-1])
        
        for track in self.mc.tracks:
            item_name = 'Track ' + str(track)
            self.midiTrackComboBox.addItem(item_name)
        
        # TODO: Do we need this right now?
        self.mc.convert_track_index = default_index
        
        self.midiTrackComboBox.setCurrentIndex(self.mc.convert_track_index)

    # TODO: rename this or the QtUI File
    def _select_midi_map_clicked(self):
        midi_yaml = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Map (*.yaml *yml)"))[0]
        
        # TODO: Okay no, I absolutely know this doesn't need to be here before conversion.
        with open(midi_yaml) as file:
            midi_yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
            self.mc.create_midi_map(midi_yaml_dict)

        self.yamlTextBox.setText(midi_yaml.split('/')[-1])
        
    def _set_output_clicked(self):
        output_folder = QFileDialog.getExistingDirectory(self, ("Select Folder"), self.lastOpenFolder)
        #print(output_folder)
        # TODO: So we set lastOpenFolder in other functions but not this one?

        # TODO: Do we need to do this before conversion?
        self.mc.output_rlrr_dir = output_folder
        self.outputTextBox.setPlainText(output_folder)

    def _midi_track_index_changed(self, index):
        self.mc.convert_track_index = index

    def _select_drum_set_clicked(self):
        self.mc.drum_set_file = QFileDialog.getOpenFileName(self, ("Select Drum Set File"), self.lastOpenFolder, ("PD Drum Set Files (*.rlrr)"))[0]
        #print(self.mc.drum_set_file)

        # TODO: We don't need this until conversion?
        self.mc.analyze_drum_set(self.mc.drum_set_file)
        self.lastOpenFolder = self.mc.drum_set_file.rsplit('/', 1)[0]
        # TODO: Do we need to split this?
        self.drumsetTextBox.setText(self.mc.drum_set_file.split('/')[-1])

    def _select_audio_file_clicked(self):
        sender_name = self.sender().objectName().lower()
        is_drum_track = "drum" in sender_name
        track_index = int(sender_name[4]) - 1
        audio_file = QFileDialog.getOpenFileName(self, ("Select Audio File"), self.lastOpenFolder, ("Audio Files (*.mp3 *.wav *.ogg)"))[0]
        #print(audio_file)

        if is_drum_track:
            self.mc.drum_tracks[track_index] = audio_file
            #print(self.mc.drum_tracks)
        else:
            self.mc.song_tracks[track_index] = audio_file
            #print(self.mc.song_tracks)

        self.lastOpenFolder = audio_file.rsplit('/', 1)[0]
        line_edit = getattr(self, ('drum' if is_drum_track else 'song') + str(track_index+1) + 'TextBox')
        #print(line_edit)
        line_edit.setText(audio_file.split('/')[-1])

    def _select_cover_image_clicked(self):
        self.mc.cover_image_path = QFileDialog.getOpenFileName(self, ("Select Cover Image"), self.lastOpenFolder, ("Image Files (*.png *.jpg)"))[0]
        #print(self.mc.cover_image_path)
        self.lastOpenFolder = self.mc.cover_image_path.rsplit('/', 1)[0]

        # TODO: Why are we splitting this?
        self.coverImageTextBox.setPlainText(self.mc.cover_image_path.split('/')[-1])
