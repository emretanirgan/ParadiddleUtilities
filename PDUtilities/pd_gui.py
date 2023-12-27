from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
from PyRLRR.rlrr import RLRR
from midicompanion import MidiCompanion
from mido.messages import Message
from copy import deepcopy
from pathlib import Path
import re
import json
import os

project_dir = os.path.dirname(os.path.realpath(__file__))    
difficulties = ["Easy", "Medium", "Hard", "Expert"]

class MIDICompanion_GUI(QtWidgets.QDialog):
    def __init__(self):
        super(MIDICompanion_GUI, self).__init__()
        self.midicompanion = MidiCompanion()
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

    def _connection_callback(self, connected):
        self.connectButton.setText("Disconnect" if self.midicompanion.connected_to_host else "Connect")
        self.connectionStatusLabel.setText("Connected" if connected else "Disconnected")

# Paradiddle GUI
class PD_GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(PD_GUI, self).__init__()
        self.lastOpenFolder = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
        self.mcGUI = MIDICompanion_GUI()
        self.chartList = [RLRR("")] # Will contain RLRR classes
        self.chartListIndex = 0
        self.setWindowIcon(QIcon(os.path.join(project_dir, "assets", "favicon.ico")))

        # Loads the .ui file
        uic.loadUi(os.path.join(project_dir, "interface/pd_gui_layout.ui"), self)
        

        # MIDI Tab
        self.midiFileButton.clicked.connect(self._select_midi_clicked)
        self.midiTrackComboBox.currentIndexChanged.connect(self._midi_track_index_changed)
        # TODO: We are missing the ghost notes and accent notes buttons

        self.convertButton.clicked.connect(self._convert_button_clicked)
        self.conversionList.addItem(self.chartList[0].metadata.title)
        self.conversionList.setCurrentRow(0)
        self.conversionList.currentItemChanged.connect(self._convert_list_item_change)

        # Menu Bar
        self.midiCompanionAction.triggered.connect(self.mcGUI._midi_companion_clicked)
        self.openSingleChartAction.triggered.connect(self._open_single_chart_clicked)
        self.importSingleChartAction.triggered.connect(self._import_single_chart_clicked)
        self.openManyChartsAction.triggered.connect(self._open_charts_clicked)
        self.importManyChartsAction.triggered.connect(self._import_charts_clicked)
        self.replaceYAMLAction.triggered.connect(self._replace_all_yaml)
        self.replaceDrumsetAction.triggered.connect(self._replace_all_drumset)

        # Audio Tab
        for i in range(5):
            songTrackBtn = getattr(self, ('song' + str(i+1) + 'Button'), None)
            drumTrackBtn = getattr(self, ('drum' + str(i+1) + 'Button'), None)
            if drumTrackBtn:
                drumTrackBtn.clicked.connect(self._select_audio_file_clicked)
            if songTrackBtn:
                songTrackBtn.clicked.connect(self._select_audio_file_clicked)

        self.yamlButton.clicked.connect(self._select_yaml_file_clicked)
        self.drumsetButton.clicked.connect(self._select_drum_set_clicked)
        
        drumset_file = os.path.join(project_dir, "drum_sets", "defaultset.rlrr")
        self.drumsetTextBox.setText(drumset_file)
        self.chartList[self.chartListIndex].options["drumRLRR"] = drumset_file

        midi_yaml = os.path.join(project_dir, 'midi_maps', 'pdtracks_mapping.yaml')
        self.yamlTextBox.setText(midi_yaml)
        self.chartList[self.chartListIndex].options["yamlFilePath"] = midi_yaml

        # Metadata Tab
        self.songNameTextBox.textChanged.connect(self._song_name_change)
        self.charterNameTextBox.textChanged.connect(self._chart_name_text_change)
        self.artistNameTextBox.textChanged.connect(self._artist_name_text_change)
        self.albumNameTextBox.textChanged.connect(self._album_name_text_change)
        self.descriptionTextBox.textChanged.connect(self._description_text_change)
        self.difficultyComboBox.currentTextChanged.connect(self._difficulty_text_changed)
        self.difficultyComboBox.addItems(["Easy", "Medium", "Hard", "Expert"])
        self.complexityComboBox.currentIndexChanged.connect(self._complexity_changed)
        self.complexityComboBox.addItems(["1", "2", "3", "4", "5"])
        
        self.outputButton.clicked.connect(self._set_output_clicked)
        self.coverImageButton.clicked.connect(self._select_cover_image_clicked)


    # LOCAL GUI FUNCTIONS
    def _replace_all_yaml(self):
        midi_yaml = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Map (*.yaml *yml)"))[0]
        if (midi_yaml == ""):
            return
        self.lastOpenFolder = midi_yaml.rsplit('/', 1)[0]
        for chart in self.chartList:
            chart.options["yamlFilePath"] = midi_yaml
        self.yamlTextBox.setText(midi_yaml)
    
    def _replace_all_drumset(self):
        drumset = QFileDialog.getOpenFileName(self, ("Select Drum Set File"), self.lastOpenFolder, ("PD Drum Set Files (*.rlrr)"))[0]
        if (drumset == ""):
            return
        self.lastOpenFolder = drumset.rsplit('/', 1)[0]

        for chart in self.chartList:
            chart.options["drumRLRR"] = drumset
        self.drumsetTextBox.setText(drumset)
    
    def _song_name_change(self):
        if (self.conversionList.currentItem() == None):
            return
        self.chartList[self.chartListIndex].metadata.title = self.songNameTextBox.toPlainText()
        self.conversionList.currentItem().setText(self.songNameTextBox.toPlainText() + ' (' + self.chartList[self.chartListIndex].metadata.difficulty + ')')

    def _chart_name_text_change(self):
        if (self.conversionList.currentItem() == None):
            return
        self.chartList[self.chartListIndex].metadata.creator = self.charterNameTextBox.toPlainText()
    
    def _artist_name_text_change(self):
        if (self.conversionList.currentItem() == None):
            return
        self.chartList[self.chartListIndex].metadata.artist = self.artistNameTextBox.toPlainText()
        
    def _album_name_text_change(self):
        if (self.conversionList.currentItem() == None):
            return
        self.chartList[self.chartListIndex].metadata.album = self.albumNameTextBox.toPlainText()
        
    def _description_text_change(self):
        if (self.conversionList.currentItem() == None):
            return
        self.chartList[self.chartListIndex].metadata.description = self.descriptionTextBox.toPlainText()
        

    def _convert_list_item_change(self):
        self.chartListIndex = self.conversionList.currentRow()
        self._update_gui_with_item()

    def _difficulty_text_changed(self, text):
        self.chartList[self.chartListIndex]._mc.difficulty = text
        self.chartList[self.chartListIndex].metadata.difficulty = text
        if (self.conversionList.currentItem() == None):
                return
        self.conversionList.currentItem().setText(self.songNameTextBox.toPlainText() + ' (' + text + ')')

    def _show_error(self, text):
        errMsg = QtWidgets.QMessageBox()
        errMsg.setIcon(QtWidgets.QMessageBox.Critical)
        errMsg.setWindowTitle("Error has occurred")
        errMsg.setText("Error: Wrong Info")
        errMsg.setInformativeText(text)
        errMsg.exec_()
        return

    def _convert_button_clicked(self):
        self.conversionProgress.setValue(0)
        for i, rlrr in enumerate(self.chartList):
            # Verify that required elements have properties
            rlrr.metadata.complexity = self.complexityComboBox.currentIndex()+1
            songName = self.songNameTextBox.toPlainText() 
            if (songName == ""):
                self._show_error("Row: " + str(i+1) + "\nThis chart needs a song name")
                return
            outputName = rlrr.metadata.artist + ' - ' + rlrr.metadata.title
            outputDir = Path(os.path.join(self.outputTextBox.toPlainText(), re.sub(r'[\\/*?:"<>|]', "", outputName)))
            os.makedirs(outputDir, exist_ok=True)
            if (outputDir == ""):
                self._show_error("Name: " + outputName + "\nDifficulty: " + str(rlrr.metadata.difficulty) + "\nOutput directory not set")
                return
            elif (self.midiFileTextBox.text() == ""):
                self._show_error("Name: " + outputName + "\nDifficulty: " + str(rlrr.metadata.difficulty) + "\nMIDI File couldn't be found")
                return
            elif (self.midiTrackComboBox.currentIndex() == -1):
                self._show_error("Name: " + outputName + "\nDifficulty: " + str(rlrr.metadata.difficulty) + "\nMIDI Track not selected")
                return

            # Run
            res = rlrr.parse_midi(rlrr._mc.midi_file, self.midiTrackComboBox.currentIndex())
            if (res != 0):
                print("Error when parsing MIDI")
                continue
            rlrr.output_rlrr(outputDir)
            rlrr.copy_files(outputDir)
            self.conversionProgress.setValue(int(((i+1)/len(self.chartList))*100))
            

    def _open_single_chart_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Chart to open or dont idgaf you do you boo")
        if (folder == ""):
            return
        self.lastOpenFolder = folder.rsplit('/', 1)[0]
        self.chartList = []

        self._append_chart(folder)
        if (len(self.chartList) > 0):
            self._chartlist_update()

    def _chartlist_update(self):
        # Updates chart list on GUI
        self.conversionList.clear()
        for chart in self.chartList:
            self.conversionList.addItem(chart.metadata.title + ' (' + chart.metadata.difficulty + ')')
        # Needs to index to 0
        self.chartListIndex = 0
        self.conversionList.setCurrentRow(self.chartListIndex)
        self._update_gui_with_item()
        
    def _append_chart(self, folder):
        convertedChart = RLRR(folder)
        filePath = ""
        for file in os.listdir(folder):
            if file.endswith(".mid"):
                filePath = file
                convertedChart._mc.midi_file = os.path.join(folder, filePath)
                break
        if (filePath == ""):
            return
        for diff in difficulties:
            convertedChart.metadata.difficulty = diff
            self.chartList.append(deepcopy(convertedChart))

    def _open_charts_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory that contains multiple charts ...Bruh...")
        #print(folder)
        if (folder == ""):
            return
        self.lastOpenFolder = folder.rsplit('/', 1)[0]
        self.chartList = []
        self._append_charts(folder)
        if (len(self.chartList) > 0):
            self._chartlist_update()

    def _import_single_chart_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Chart Directories ...Bruh...")
        if (folder == ""):
            return
        self.lastOpenFolder = folder.rsplit('/', 1)[0]
        self._append_chart(folder)
        self._chartlist_update()

    def _import_charts_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Chart Directories ...Bruh...")
        if (folder == ""):
            return
        self.lastOpenFolder = folder.rsplit('/', 1)[0]
        self._append_charts(folder)
        self._chartlist_update()

    def _append_charts(self, folder):
        subdirectories = [x.path for x in os.scandir(folder) if os.path.isdir(x)]
        for directory in subdirectories:
            self._append_chart(directory)

    def _update_gui_with_item(self):
        item = self.chartList[self.chartListIndex]

        # Metadata
        self.songNameTextBox.setPlainText(item.metadata.title)
        self.charterNameTextBox.setPlainText(item.metadata.creator)
        self.artistNameTextBox.setPlainText(item.metadata.artist)
        self.albumNameTextBox.setPlainText(item.metadata.album)
        self.coverImageTextBox.setPlainText(item.metadata.coverImagePath)
        self.difficultyComboBox.setCurrentIndex(difficulties.index(item.metadata.difficulty))
        self.complexityComboBox.setCurrentIndex(item.metadata.complexity-1)
        self.descriptionTextBox.setText(item.metadata.description)

        # Audio     
        # Set songTracks
        for i, song in enumerate(item.songTracks):
            sTB = getattr(self, ('song' + str(i+1) + 'TextBox'), None)
            sTB.setText(song)
        # Set drumTracks
        for i, drum in enumerate(item.drumTracks):
            dTB = getattr(self, ('drum' + str(i+1) + 'TextBox'), None)
            dTB.setText(drum)

        # MIDI
        if (os.path.exists(item.metadata.chartDir)):
            for file in os.listdir(item.metadata.chartDir):
                if file.endswith(".mid"):
                    self.midiFileTextBox.setText(file)
                    self._set_midi_track_combo()
                    break
        
        

    def _complexity_changed(self, text):
        if (self.conversionList.currentItem() == None):
            return
        self.chartList[self.chartListIndex].metadata.complexity = int(text)

    def _select_midi_clicked(self):
        self.chartList[self.chartListIndex]._mc.midi_file = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Files (*.mid *.midi *.kar)"))[0]
        # print(midi_file)
        
        if (self.chartList[self.chartListIndex]._mc.midi_file == ""):
            return
        self.lastOpenFolder = self.chartList[self.chartListIndex]._mc.midi_file.rsplit('/', 1)[0]
        self.midiFileTextBox.setText(self.chartList[self.chartListIndex]._mc.midi_file)
        self._set_midi_track_combo()

    def _set_midi_track_combo(self):
        self.midiTrackComboBox.clear()

        self.chartList[self.chartListIndex]._mc.get_tracks()
        (_, default_index) = self.chartList[self.chartListIndex]._mc.get_drum_track()
        self.lastOpenFolder = self.chartList[self.chartListIndex]._mc.midi_file.rsplit('/', 1)[0]
        
        for i, track in enumerate(self.chartList[self.chartListIndex]._mc.midi_tracks):
            isMessage = (isinstance(track[i], Message))
            if (isMessage):
                isMessage = hasattr(track[i], "channel")
            hasName = (hasattr(track, 'name'))
            trackName = "Track "
            channel = "Channel "
            if (hasName):
                trackName += track.name
            if (isMessage):
                channel += str(track[i].channel)

            item_name = trackName + " : " + channel
            self.midiTrackComboBox.addItem(item_name)
        
        self.chartList[self.chartListIndex]._mc.convert_track_index = default_index
        
        self.midiTrackComboBox.setCurrentIndex(default_index)

    def _select_yaml_file_clicked(self):
        midi_yaml = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Map (*.yaml *yml)"))[0]
        if (midi_yaml == ""):
            return
        self.lastOpenFolder = midi_yaml.rsplit('/', 1)[0]
        self.chartList[self.chartListIndex].options["yamlFilePath"] = midi_yaml
        self.yamlTextBox.setText(midi_yaml)
        
    def _set_output_clicked(self):
        output_folder = QFileDialog.getExistingDirectory(self, ("Select Folder"), self.lastOpenFolder)
        if (output_folder == ""):
            return
        self.lastOpenFolder = output_folder
        self.outputTextBox.setPlainText(output_folder)

    def _midi_track_index_changed(self, index):
        self.chartList[self.chartListIndex]._mc.convert_track_index = index

    def _select_drum_set_clicked(self):
        drumset = QFileDialog.getOpenFileName(self, ("Select Drum Set File"), self.lastOpenFolder, ("PD Drum Set Files (*.rlrr)"))[0]
        if (drumset == ""):
            return
        self.lastOpenFolder = drumset.rsplit('/', 1)[0]

        self.chartList[self.chartListIndex].options["drumRLRR"] = drumset
        self.drumsetTextBox.setText(drumset)

    def _select_audio_file_clicked(self):
        sender_name = self.sender().objectName().lower()
        is_drum_track = "drum" in sender_name
        track_index = int(sender_name[4]) - 1
        audio_file = QFileDialog.getOpenFileName(self, ("Select Audio File"), self.lastOpenFolder, ("Audio Files (*.mp3 *.wav *.ogg)"))[0]
        if (audio_file == ""):
            return

        self.lastOpenFolder = audio_file.rsplit('/', 1)[0]
        line_edit = getattr(self, ('drum' if is_drum_track else 'song') + str(track_index+1) + 'TextBox')
        if (is_drum_track):
            self.chartList[self.chartListIndex].drumTracks[track_index] = audio_file
        else:
            self.chartList[self.chartListIndex].songTracks[track_index] = audio_file

        line_edit.setText(audio_file)

    def _select_cover_image_clicked(self):
        image_path = QFileDialog.getOpenFileName(self, ("Select Cover Image"), self.lastOpenFolder, ("Image Files (*.png *.jpg)"))[0]
        if (image_path == ""):
            return

        self.lastOpenFolder = image_path.rsplit('/', 1)[0]
        self.chartList[self.chartListIndex].metadata.coverImagePath = image_path
        self.coverImageTextBox.setPlainText(image_path)
