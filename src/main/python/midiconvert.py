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
import copy

out_dict = {
    'version' : 0.5,
    'recordingMetadata' : {},
    'audioFileData' : {},
    'instruments' : [],
    'events' : []
}  

# TODO set up GUI for input midi, input drum set, output recording file names with file dialogs for each

# TODO user should specify drum set file path, if not use default set file
# If this file is not fed in, then use default
# drum_set_file = '/Users/etanirgan/test.json'
script_dir = os.path.dirname(os.path.realpath(__file__))
# drum_set_file = ''
drum_set_file = os.path.join(script_dir,'resources','base','drum_sets','defaultset.rlrr')
drum_set_dict = None
midi_file_name = ''
output_rlrr_dir = ''
song_tracks = [""] * 5
drum_tracks = [""] * 4

audio_file_data = {
    'songTracks' : [],
    'drumTracks' : [],
    'calibrationOffset' : 0
}

recording_metadata = {
    'title': '',
    'description': '',
    'coverImagePath': '',
    'artist': '',
    'author': ''
}

song_name = ''
artist_name = ''
cover_image_path = ''
author_name = ''
recording_description = ''
calibration_offset = 0.0


# TODO put in actual default notes
# TODO support for mallet instruments, or instruments that can have a lot of midi notes. might have to specify a range of notes
# for some of them like '48-102' etc
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

# pdtracks_notes = {
#     "BP_HiHat_C"    : 45,
#     "BP_Snare_C"    : 26,
#     "BP_Kick_C"     : 24,
#     "BP_Crash15_C"  : 62,
#     "BP_Crash17_C"  : 67,
#     "BP_FloorTom_C" : 39,
#     "BP_Ride17_C"   : 75,
#     "BP_Tom1_C"     : 35,
#     "BP_Tom2_C"     : 37
# }

pdtracks_notes = {
    24 : {"drum": "BP_Kick_C"},
    26 : {"drum": "BP_Snare_C"},
    30 : {"drum": "BP_Snare_C"},
    43 : {"drum": "BP_HiHat_C"},
    45 : {"drum": "BP_HiHat_C"},
    48 : {"drum": "BP_HiHat_C"},
    35 : {"drum": "BP_Tom1_C"},
    37 : {"drum": "BP_Tom2_C"},
    39 : {"drum": "BP_FloorTom_C"},
    62 : {"drum": "BP_Crash15_C"},
    67 : {"drum": "BP_Crash17_C"},
    75 : {"drum": "BP_Ride17_C"}
}


pdtracks_notes_easy = {
    24 : {"drum": "BP_Kick_C"},
    26 : {"drum": "BP_Snare_C"},
    30 : {"drum": "BP_Snare_C"},
    43 : {"drum": "BP_HiHat_C"},
    45 : {"drum": "BP_HiHat_C"},
    48 : {"drum": "BP_HiHat_C"},
    35 : {"drum": "BP_FloorTom_C"},
    37 : {"drum": "BP_FloorTom_C"},
    39 : {"drum": "BP_FloorTom_C"},
    62 : {"drum": "BP_Crash15_C"},
    67 : {"drum": "BP_Crash17_C"},
    75 : {"drum": "BP_Crash15_C"}
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
    global drum_set_dict
    default_set_name = "../resources/base/drum_sets/defaultset.rlrr"
    default_set_full_path = os.path.join(script_dir, default_set_name)
    print(default_set_full_path)

    if drum_set_filename == '':
        drum_set_filename = default_set_full_path
    drum_set_dict = None

    with open(drum_set_filename) as f:
        drum_set_dict = json.load(f)
        print("Kit Length: " + str(len(drum_set_dict["instruments"])))
        #TODO handle drum layout formats with version 0 and 0.5 here
        # need to go throuh all instruments, see if their midi notes have been changed or set
        # for mallets, need to check the first key index and number of notes?

    

def analyze_midi_file():
    global out_dict
    out_dict["version"] = 0.6
    out_dict["instruments"] = []
    out_dict["events"] = []
    out_dict["bpmEvents"] = []
    # midi_file_name = script_dir + '/../resources/base/midi_files/notes.mid'
    mid = MidiFile(midi_file)

    tempo = 500000
    #list of tuples in the form of (total_ticks, total_seconds, new_tempo)
    tempo_events = [(0.0, 0.0, tempo)]
    total_time = 0.0
    total_ticks = 0.0
    longest_time = 0.0

    #TODO Pick track from a GUI (file dialog) to convert to rlrr
    #TODO need default midi mappings for rhythm game midi format - get difficulties, map from those midi notes
    #https://rockband.scorehero.com/forum/viewtopic.php?t=1711
    #https://www.scorehero.com/forum/viewtopic.php?t=1179
    #TODO convert from .chart? eventually
    #TODO don't hard code midi and rlrr file paths

    print('Midi file type: ' + str(mid.type))
    is_rhythm_game_midi = False
    # class_to_default_notes = rlrr_default_notes
    # class_to_default_notes = pdtracks_notes
    convert_track_index = 0 if mid.type == 0 else (1 if len(mid.tracks) > 1 else 0)
    # note_to_drums_map = pdtracks_notes
    note_to_drums_map = copy.deepcopy(pdtracks_notes_easy)
    track_to_convert = mid.tracks[convert_track_index]
    #  TODO pick midi track to convert

    for i, track in enumerate(mid.tracks):
        print('Track {}: {}'.format(i, track.name))
        if (track.name == "PART DRUMS"):
            is_rhythm_game_midi = True
            class_to_default_notes = rhythm_midi_note_to_drums
            track_to_convert = track

    print("Kit layout again: " + str(drum_set_dict["instruments"]))
    # if drum_set_dict is None:
    #     for drum_class in class_to_default_notes:
    #         print(drum_class)
    #         note_to_drums_map[class_to_default_notes[drum_class]]= [str(drum_class)+"Default"]
    # else:
    # TODO for now assume all drums will be in the drum kit file
    kit_instruments = drum_set_dict["instruments"]
    for note in note_to_drums_map:
        drum_class = note_to_drums_map[note]["drum"]
        print("Drum class: " + drum_class)
        drums = [d for d in kit_instruments if d["class"] == drum_class]
        if(len(drums) > 0):
            note_to_drums_map[note]["drum"] = drums[0]["name"]
        else:
            note_to_drums_map[note]["drum"] =  drum_class+"Default"
            print(drum_class+"Default")

    out_dict["instruments"] = drum_set_dict["instruments"]

    print(note_to_drums_map)

    # Tempo changes
    tempo_total_ticks = 0
    tempo_total_seconds = 0
    tempo_index = 0
    tempo = 500000
    default_tempo = 500000
    for i, track in enumerate(mid.tracks): 
        for msg in track:
            if msg.is_meta:
                # print(msg.type)
                if msg.type == "set_tempo":
                    tempo_total_seconds += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
                    tempo = msg.tempo
                    tempo_total_ticks += msg.time
                    tempo_events.append((tempo_total_ticks, tempo_total_seconds, msg.tempo))
                    out_dict["bpmEvents"].append({"bpm" : tempo2bpm(msg.tempo), "time" : tempo_total_seconds})
    if len(tempo_events) == 0:
        tempo_events = [(0.0, 0.0, default_tempo)]
        out_dict["bpmEvents"].append({"bpm" : default_tempo, "time" : 0})


    # print("Ticks per beat: " + str(mid.ticks_per_beat))
    # print("Tempo Changes: " + str(tempo_events))
    for msg in track_to_convert:
        total_ticks += msg.time
        while (tempo_index+1 < len(tempo_events)) and (total_ticks > tempo_events[tempo_index+1][0]):
            tempo_index += 1
        tempo = tempo_events[tempo_index][2]
        # total_time = total_time + mido.tick2second(msg.time, mid.ticks_per_beat, tempo) # old method of computing time, was slightly off
        total_time = tempo_events[tempo_index][1] + mido.tick2second(total_ticks - tempo_events[tempo_index][0], mid.ticks_per_beat, tempo)
        if(total_time > longest_time):
            longest_time = total_time
        if not msg.is_meta:
            if msg.type == "note_on":
                drum_name = "Test"
                note = msg.note
                #TODO are note lengths relevant here? maybe incorporate that when checking total midi file length?
                # if is_rhythm_game_midi:
                    # note = msg.note 
                #ignore velocity 0 notes here? Seem to be getting a lot of these in the rhythm game midis, almost like note off events are showing up here
                if note in note_to_drums_map and msg.velocity > 0:
                    drum_name = note_to_drums_map[note]["drum"]

                    drum_hit = {"name" : drum_name, "vel" : msg.velocity, "loc": 0, "time": '%.4f'%total_time}
                    # print(str(drum_hit) + " tempo: " + str(tempo) + " total ticks: " + str(total_ticks))
                    out_dict["events"].append(drum_hit)
    print(tempo_index)
    print("Ticks Per Beat " + str(mid.ticks_per_beat) + ", Tempo " + str(tempo) + ", BPM " + '%.2f'%tempo2bpm(tempo))
    print("Midi File Length " + str(mid.length))
    print("Our totaled file length " + str(longest_time))
    # print(out_dict)

def convert_to_rlrr():
    print("Converting to rlrr...")
    # Filter out empty strings from track lists
    flt_drum_tracks = [x for x in drum_tracks if x.strip()]
    flt_song_tracks = [x for x in song_tracks if x.strip()]

    short_dtracks = [x.split('/')[-1] for x in flt_drum_tracks]
    short_stracks = [x.split('/')[-1] for x in flt_song_tracks]

    # audio_file_short = audio_file.split('/')[-1]
    cover_image_short = cover_image_path.split('/')[-1]
    audio_file_data['songTracks'] = short_stracks
    audio_file_data['drumTracks'] = short_dtracks
    audio_file_data['calibrationOffset'] = calibration_offset
    out_dict["audioFileData"] = audio_file_data

    recording_metadata['title'] = song_name
    recording_metadata['description'] = recording_description
    recording_metadata['coverImagePath'] = cover_image_short
    recording_metadata['artist'] = artist_name
    recording_metadata['creator'] = author_name
    out_dict["recordingMetadata"] = recording_metadata

    # output_folder_path = script_dir + '/../resources/base/rlrr_files/'+ song_name
    output_folder_path = os.path.join(output_rlrr_dir, song_name)
    if not os.path.isdir(output_folder_path):
        os.makedirs(output_folder_path)
    
    all_tracks = flt_drum_tracks + flt_song_tracks
    for track in all_tracks:
        copyfile(track, output_folder_path + '/' + track.split('/')[-1])
    if cover_image_path:
        copyfile(cover_image_path, output_folder_path + '/' + cover_image_short)    
    
    # with open(script_dir + '/../resources/base/rlrr_files/' + song_name + '/' + song_name + '_converted.rlrr', 'w') as outfile:  
    # with open(script_dir + '/../resources/base/rlrr_files/' + song_name + '/' + song_name + '.rlrr', 'w') as outfile:  
    with open(os.path.join(output_rlrr_dir,song_name) + '/' + song_name + '.rlrr', 'w') as outfile:  
        json.dump(out_dict, outfile, indent=4)
        print("Conversion done!")
        return True
    
 
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_ParadiddleUtilities()
        self.ui.setupUi(self)
        self.ui.selectMidiButton.clicked.connect(self.select_midi_clicked)
        self.ui.selectDrumSetButton.clicked.connect(self.select_drum_set_clicked)
        self.ui.selectDrumTrackButton_1.clicked.connect(self.select_audio_file_clicked)
        self.ui.selectDrumTrackButton_2.clicked.connect(self.select_audio_file_clicked)
        self.ui.selectSongTrackButton_1.clicked.connect(self.select_audio_file_clicked)
        self.ui.convertButton.clicked.connect(self.convert_clicked)
        self.ui.calibrationSpinBox.valueChanged.connect(self.calibration_offset_changed)
        self.ui.selectCoverImageButton.clicked.connect(self.select_cover_image_clicked)
        self.lastOpenFolder = "."
		
    def set_default_set(self, default_set):
        analyze_drum_set(default_set)
        print(os.path.join(os.path.join(os.path.dirname(default_set), '..'), 'rlrr_files'))
        global output_rlrr_dir
        output_rlrr_dir = os.path.join(os.path.join(os.path.dirname(default_set), '..'), 'rlrr_files')
        # output_rlrr_dir = default_set.split('/')
        # self.midi_converter = MidiConverter()

    def select_midi_clicked(self):
        global midi_file
        midi_file = QFileDialog.getOpenFileName(self, ("Select Midi File"), self.lastOpenFolder, ("Midi Files (*.mid *.midi)"))[0]
        print(midi_file)
        analyze_midi_file()
        self.lastOpenFolder = midi_file.rsplit('/', 1)[0]
        self.ui.midiFileLineEdit.setText(midi_file.split('/')[-1])

    def select_drum_set_clicked(self):
        global drum_set_file
        drum_set_file = QFileDialog.getOpenFileName(self, ("Select Drum Set File"), self.lastOpenFolder, ("PD Drum Set Files (*.rlrr)"))[0]
        print(drum_set_file)
        analyze_drum_set(drum_set_file)
        self.lastOpenFolder = drum_set_file.rsplit('/', 1)[0]
        self.ui.drumSetLineEdit.setText(drum_set_file.split('/')[-1])

    def select_audio_file_clicked(self):
        sender_name = self.sender().objectName()
        is_drum_track = "Drum" in sender_name
        track_index = int(sender_name.split('_')[-1]) - 1
        global song_tracks
        global drum_tracks
        audio_file = QFileDialog.getOpenFileName(self, ("Select Audio File"), self.lastOpenFolder, ("Audio Files (*.mp3 *.wav *.ogg)"))[0]
        print(audio_file)
        if is_drum_track:
            drum_tracks[track_index] = audio_file
            print(drum_tracks)
        else:
            song_tracks[track_index] = audio_file
            print(song_tracks)
        self.lastOpenFolder = audio_file.rsplit('/', 1)[0]
        line_edit = getattr(self.ui, ('drum' if is_drum_track else 'song') + 'TrackLineEdit_' + str(track_index+1))
        print(line_edit)
        line_edit.setText(audio_file.split('/')[-1])

    def select_cover_image_clicked(self):
        global cover_image_path
        cover_image_path = QFileDialog.getOpenFileName(self, ("Select Cover Image"), self.lastOpenFolder, ("Image Files (*.png *.jpg)"))[0]
        print(cover_image_path)
        self.lastOpenFolder = cover_image_path.rsplit('/', 1)[0]
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
        if convert_to_rlrr():
            self.ui.statusLabel.setText("Conversion successful!")