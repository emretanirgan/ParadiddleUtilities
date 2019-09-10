from mido import MidiFile
from mido import tempo2bpm
from PyQt5.QtWidgets import *
import mido
import json
import os
from PyQt5 import QtWidgets
from ParadiddleUtilities import *
import sys
from shutil import copyfile

out_dict = {}  
# TODO set up GUI for input midi, input drum set, output recording file names with file dialogs for each

# TODO user should specify drum set file path, if not use default set file
# If this file is not fed in, then use default
# drum_set_file = '/Users/etanirgan/test.json'
drum_set_file = ''
drum_set_dict = None
midi_file_name = ''
audio_file = ''

audio_file_data = {
    'Path' : '',
    'CalibrationOffset' : 0
}

recording_metadata = {
    'Title': '',
    'Description': '',
    'CoverImagePath': '',
    'Artist': '',
    'Author': ''
}

song_name = ''
artist_name = ''
cover_image_path = ''
author_name = ''
recording_description = ''
calibration_offset = 0.0

script_dir = os.path.dirname(os.path.realpath(__file__))

# TODO put in actual default notes
# TODO support for drum types with more than 1 hit zone - can map from midi note to
# a tuple of (drum class, location) instead (or just drum class if we want to use a default location value of 0)
class_to_default_notes = {}
rlrr_default_notes = {
    "BP_HiHat_C"    : 60,
    "BP_Snare_C"    : 57,
    "BP_Kick_C"     : 56,
    "BP_Crash15_C"  : 42,
    "BP_Crash17_C"  : 43,
    "BP_FloorTom_C" : 44,
    "BP_Ride17_C"   : 45,
    "BP_Ride20_C"   : 47,
    "BP_Tom1_C"     : 48,
    "BP_Tom2_C"     : 49
}

# red, (Snare Drum)
# yellow, (Hi-Hat)
# blue, (Tom-Tom)
# green (Crash Cymbols).
# The kick pedal is colored orange (Bass Drum).
# 60: guitar note GREEN, easy (C) 
# 61: guitar note RED, easy (C#) 
# 62: guitar note YELLOW, easy (D) 
# 63: guitar note BLUE, easy (D#) 
# 64: guitar note ORANGE, easy (E) 
# 67: star power group, easy (G) 
# 69: player 1 section, easy (A) 
# 70: player 2 section, easy (A#) 
# 72: guitar note GREEN, medium (C) 
# 73: guitar note RED, medium (C#) 
# 74: guitar note YELLOW, medium (D) 
# 75: guitar note BLUE, medium (D#) 
# 76: guitar note ORANGE, medium (E) and so on (60 + difficulty*12)
rhythm_midi_note_to_drums = {
    "BP_Kick_C"     : 96,
    "BP_Snare_C"    : 97,
    "BP_HiHat_C"    : 98,
    "BP_Tom1_C"     : 99,
    "BP_Crash15_C"  : 100
}

note_to_drums_map = {}

def analyze_drum_set(drum_set_filename):
    default_set_name = "../resources/base/drum_sets/defaultset.rlrr"
    default_set_full_path = os.path.join(script_dir, default_set_name)
    print(default_set_full_path)

    if drum_set_filename == '':
        drum_set_filename = default_set_full_path
    drum_set_dict = None

    with open(drum_set_filename) as f:
        drum_set_dict = json.load(f)
        print(len(drum_set_dict["DrumLayout"]))

    

def analyze_midi_file():
    out_dict["DrumHits"] = []
    midi_file_name = script_dir + '/../resources/base/midi_files/notes.mid'
    mid = MidiFile(midi_file_name)

    tempo = 500000
    #list of tuples in the form of (total_ticks, new_tempo)
    tempo_events = [(0.0, tempo)]
    total_time = 0.0
    total_ticks = 0.0
    longest_time = 0.0

    #TODO Pick track from a GUI (file dialog) to convert to rlrr
    #TODO need default midi mappings for rhythm game midi format - get difficulties, map from those midi notes
    #https://rockband.scorehero.com/forum/viewtopic.php?t=1711
    #https://www.scorehero.com/forum/viewtopic.php?t=1179
    #TODO convert from .chart? eventually
    #TODO don't hard code midi and rlrr file paths

    is_rhythm_game_midi = False
    class_to_default_notes = rlrr_default_notes
    track_to_convert = mid.tracks[0]

    for i, track in enumerate(mid.tracks):
        print('Track {}: {}'.format(i, track.name))
        if (track.name == "PART DRUMS"):
            is_rhythm_game_midi = True
            class_to_default_notes = rhythm_midi_note_to_drums
            track_to_convert = track

    if drum_set_dict is None:
        for drum_class in class_to_default_notes:
            print(drum_class)
            note_to_drums_map[class_to_default_notes[drum_class]]= [str(drum_class)+"Default"]
    else:
        for drum_obj in drum_set_dict["DrumLayout"]:
            if drum_obj["Class"] in class_to_default_notes:
                note_to_drums_map[class_to_default_notes[drum_obj["Class"]]] = [str(drum_obj["DrumName"])]
        out_dict["DrumLayout"] = drum_set_dict["DrumLayout"] 

    print(note_to_drums_map)
    tempo_total_ticks = 0
    tempo_index = 0

    for i, track in enumerate(mid.tracks): 
        for msg in track:
            if msg.is_meta:
                if msg.type == "set_tempo":
                    tempo = msg.tempo
                    tempo_total_ticks += msg.time
                    tempo_events.append((tempo_total_ticks, msg.tempo))

    print("Tempo Changes: " + str(tempo_events))
    for msg in track_to_convert:
        total_ticks += msg.time
        while (tempo_index+1 < len(tempo_events)) and (total_ticks > tempo_events[tempo_index+1][0]):
            tempo_index += 1
        tempo = tempo_events[tempo_index][1]
        # total_time = total_ticks * (tempo / (1000000.0 * mid.ticks_per_beat))
        total_time = total_time + mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
        if(total_time > longest_time):
            longest_time = total_time
        if not msg.is_meta:
            if msg.type == "note_on":
                drum_name = "Test"
                note = msg.note
                # if is_rhythm_game_midi:
                    # note = msg.note 
                #ignore velocity 0 notes here? Seem to be getting a lot of these in the rhythm game midis, almost like note off events are showing up here
                if note in note_to_drums_map and msg.velocity > 0:
                    drum_name = note_to_drums_map[note][0]
                    drum_hit = {"DrumName" : drum_name, "Vel" : msg.velocity, "Loc": 0, "Time": '%.4f'%total_time}
                    out_dict["DrumHits"].append(drum_hit)
    print(tempo_index)
    print("Ticks Per Beat " + str(mid.ticks_per_beat) + ", Tempo " + str(tempo) + ", BPM " + '%.2f'%tempo2bpm(tempo))
    print("Midi File Length " + str(mid.length))
    print("Our totaled file length " + str(longest_time))

def convert_to_rlrr():
    print("Converting to rlrr...")
    audio_file_short = audio_file.split('/')[-1]
    cover_image_short = cover_image_path.split('/')[-1]
    audio_file_data['Path'] = audio_file_short
    audio_file_data['CalibrationOffset'] = calibration_offset
    out_dict["AudioFileData"] = audio_file_data

    recording_metadata['Title'] = song_name
    recording_metadata['Description'] = recording_description
    recording_metadata['CoverImagePath'] = cover_image_short
    recording_metadata['Artist'] = artist_name
    recording_metadata['Author'] = author_name
    out_dict["RecordingMetadata"] = recording_metadata

    output_folder_path = script_dir + '/../resources/base/rlrr_files/'+ song_name
    os.mkdir(output_folder_path)
    copyfile(audio_file, output_folder_path + '/' + audio_file_short)
    copyfile(cover_image_path, output_folder_path + '/' + cover_image_short)    
    with open(script_dir + '/../resources/base/rlrr_files/' + song_name + '/' + midi_file_name.split('/')[-1].split('.')[0] + '_converted.json', 'w') as outfile:  
        json.dump(out_dict, outfile, indent=4)
    print("Conversion done!")
 
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_ParadiddleUtilities()
        self.ui.setupUi(self)
        self.ui.selectMidiButton.clicked.connect(self.select_midi_clicked)
        self.ui.selectDrumSetButton.clicked.connect(self.select_drum_set_clicked)
        self.ui.selectAudioFileButton.clicked.connect(self.select_audio_file_clicked)
        self.ui.convertButton.clicked.connect(self.convert_clicked)
        self.ui.calibrationSpinBox.valueChanged.connect(self.calibration_offset_changed)
        self.ui.selectCoverImageButton.clicked.connect(self.select_cover_image_clicked)
		
        analyze_drum_set('')
        # self.midi_converter = MidiConverter()

    def select_midi_clicked(self):
        global midi_file
        midi_file = QFileDialog.getOpenFileName(self, ("Select Midi File"), ".", ("Midi Files (*.mid *.midi)"))[0]
        print(midi_file)
        analyze_midi_file()
        self.ui.midiFileLineEdit.setText(midi_file.split('/')[-1])

    def select_drum_set_clicked(self):
        global drum_set_file
        drum_set_file = QFileDialog.getOpenFileName(self, ("Select Drum Set File"), ".", ("PD Drum Set Files (*.rlrr)"))[0]
        print(drum_set_file)
        analyze_drum_set(drum_set_file)
        self.ui.drumSetLineEdit.setText(drum_set_file.split('/')[-1])

    def select_audio_file_clicked(self):
        global audio_file
        audio_file = QFileDialog.getOpenFileName(self, ("Select Audio File"), ".", ("Audio Files (*.mp3 *.wav *.ogg)"))[0]
        print(audio_file)
        self.ui.audioFileLineEdit.setText(audio_file.split('/')[-1])

    def select_cover_image_clicked(self):
        global cover_image_path
        cover_image_path = QFileDialog.getOpenFileName(self, ("Select Cover Image"), ".", ("Image Files (*.png *.jpg)"))[0]
        print(cover_image_path)
        self.ui.coverImageLineEdit.setText(cover_image_path.split('/')[-1])

    def calibration_offset_changed(self):
        global calibration_offset
        calibration_offset = self.ui.calibrationSpinBox.value()
        # print(self.ui.calibrationSpinBox.value())

    def convert_clicked(self):
        global song_name, recording_description, artist_name, author_name
        song_name = self.ui.songNameLineEdit.text()
        # TODO check if we need to escape the \n newline characters ('\n' to '\\n')
        recording_description = self.ui.descriptionTextEdit.toPlainText() 
        artist_name = self.ui.artistNameLineEdit.text()
        author_name = self.ui.authorNameLineEdit.text()
        convert_to_rlrr()