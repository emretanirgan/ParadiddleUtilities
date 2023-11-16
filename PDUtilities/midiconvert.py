# Copyright (C) 2020 Emre Tanirgan <emre@paradiddleapp.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from mido import MidiFile, tempo2bpm
from PyQt5.QtWidgets import *
import mido
import json
import os
from shutil import copyfile
import soundfile as sf
import copy

class MidiConverter:
    def __init__(self):
        self.out_dict = {
            'version' : 0.5,
            'recordingMetadata' : {},
            'audioFileData' : {},
            'instruments' : [],
            'events' : []
        }  

        self.difficulty_names = ['Easy', 'Medium', 'Hard', 'Expert']
        self.difficulty = self.difficulty_names[0]

        # TODO: Replace filenames, this is gonna be a python package
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.drum_set_file = os.path.join(script_dir,'drum_sets','defaultset.rlrr')
        self.drum_set_dict = None
        self.midi_file_name = ''
        self.output_rlrr_dir = ''
        self.song_tracks = [""] * 5
        self.drum_tracks = [""] * 4
        self.calibration_offset = 0

        self.midi_lenth = 0
        self.song_length = 0
        self.length = 0

        # MIDI
        self.midi_track_names = []
        self.convert_track_index = 0
        self.note_to_drum_maps = [] # in order of difficulty
        self.toggle_to_drum_maps = [] # example: [{111: Snare, 110: HiHat}, {100: Kick}] 

        self.audio_file_data = {
            'songTracks' : [],
            'drumTracks' : [],
            'calibrationOffset' : 0
        }

        self.recording_metadata = {
            'title': '',
            'description': '',
            'coverImagePath': '',
            'artist': '',
            'creator': '',
            'length': 0,
            'complexity': 1
        }

        self.song_name = ''

        # FIXME: Replace with index of difficulty_names
        self.song_complexity = 1
        self.artist_name = ''
        self.cover_image_path = ''
        self.author_name = ''
        self.recording_description = ''

    # TODO support for drum types with more than 1 hit zone - can map from midi note to
    # a tuple of (drum class, location) instead (or just drum class if we want to use a default location value of 0)

    def analyze_drum_set(self, drum_set_filename):
        self.drum_set_dict = None

        if drum_set_filename == '':
            self.default_set_name = "drum_sets/defaultset.rlrr"
            self.default_set_full_path = os.path.join(self.script_dir, self.default_set_name)
            print(self.default_set_full_path)
            drum_set_filename = self.default_set_full_path
            

        with open(drum_set_filename) as f:
            self.drum_set_dict = json.load(f)
            print("Kit Length: " + str(len(self.drum_set_dict["instruments"])))
            #TODO handle drum layout formats with version 0 and 0.5 here
            # need to go throuh all instruments, see if their midi notes have been changed or set
            # for mallets, need to check the first key index and number of notes?

    # Returns a tuple of the default midi track we want to use in the form of
    # (midi track object, track index)
    def get_default_midi_track(self):
        mid = MidiFile(self.midi_file, clip=True)
        
        self.midi_track_names.clear()

        print('Midi file type: ' + str(mid.type))
        default_index = 0 if mid.type == 0 else (1 if len(mid.tracks) > 1 else 0)
        track_to_convert = mid.tracks[default_index]

        for i, track in enumerate(mid.tracks):
            print('Track {}: {}'.format(i, track.name))
            self.midi_track_names.append(track.name)
            if ("drum" in track.name.lower()): # default to a midi track if it has 'drum' in the name
                track_to_convert = track
                default_index = i
                print("found drum in " + str(track_to_convert) + " " + str(default_index))
        return (track_to_convert, default_index)

    def analyze_midi_file(self):
        self.out_dict["version"] = 0.6
        self.out_dict["instruments"] = []
        self.out_dict["events"] = []
        self.out_dict["bpmEvents"] = []
        mid = MidiFile(self.midi_file, clip=True)

        try:
            # print("Mid length: " + str(mid.length))
            midi_len = mid.length
            if self.length < midi_len:
                self.length = midi_len
        except ValueError:
            print("Invalid midi file type to get length")

        tempo = 500000
        #list of tuples in the form of (total_ticks, total_seconds, new_tempo)
        tempo_events = [(0.0, 0.0, tempo)]
        total_time = 0.0
        total_ticks = 0.0
        longest_time = 0.0
            
        # note_to_drums_map = pdtracks_notes
        diff_index = self.difficulty_names.index(self.difficulty)
        # fall back to highest difficulty map if our difficulty isn't in the map
        # print(note_to_drum_maps)
        note_map = copy.deepcopy(self.note_to_drum_maps[min(len(self.note_to_drum_maps)-1, diff_index)])
        toggle_map = copy.deepcopy(self.toggle_to_drum_maps[min(len(self.toggle_to_drum_maps)-1, diff_index)])

        # print(note_map)
        self.track_to_convert = mid.tracks[self.convert_track_index]
        # print(track_to_convert)

        print("Kit layout again: " + str(self.drum_set_dict["instruments"]))
        # if drum_set_dict is None:
        #     for drum_class in class_to_default_notes:
        #         print(drum_class)
        #         note_to_drums_map[class_to_default_notes[drum_class]]= [str(drum_class)+"Default"]
        # else:
        # TODO for now assume all drums will be in the drum kit file
        kit_instruments = self.drum_set_dict["instruments"]
        for note in note_map:
            for drum in note_map[note]:
                drum_class = drum["drum"]
                print("Drum class: " + drum_class)
                drums = [d for d in kit_instruments if d["class"] == drum_class]
                if(len(drums) > 0):
                    drum["drum"] = drums[0]["name"]
                else:
                    drum["drum"] =  drum_class+"Default"
                    print(drum_class+"Default")
        # print(toggle_map)
        toggle_map_rev = {}
        for toggle in toggle_map:
            drum_class = toggle_map[toggle]
            drums = [d for d in kit_instruments if d["class"] == drum_class]
            if(len(drums) > 0):
                toggle_map[toggle] = drums[0]["name"]
            else:
                toggle_map[toggle] =  drum_class+"Default"
            toggle_map_rev[toggle_map[toggle]] = toggle
        # print('Updated toggle map: ' + str(toggle_map))
        # print('toggle map rev: ' + str(toggle_map_rev))
        self.out_dict["instruments"] = self.drum_set_dict["instruments"]
        # print(note_map)

        # Tempo changes
        tempo_total_ticks = 0
        tempo_total_seconds = 0
        tempo_index = 0
        tempo = 500000
        default_tempo = 500000
        active_toggles = []
        for i, track in enumerate(mid.tracks): 
            for msg in track:
                # print(msg.type + " " + str(msg.time))
                tempo_total_seconds += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
                tempo_total_ticks += msg.time
                if msg.is_meta:
                    if msg.type == "set_tempo":
                        tempo = msg.tempo
                        tempo_events.append((tempo_total_ticks, tempo_total_seconds, msg.tempo))
                        print('Tempo change: ' + str(tempo2bpm(msg.tempo)) + ' time: ' + str(tempo_total_seconds) + ' ticks: ' + str(tempo_total_ticks))
                        self.out_dict["bpmEvents"].append({"bpm" : tempo2bpm(msg.tempo), "time" : tempo_total_seconds})
        if len(tempo_events) == 0:
            tempo_events = [(0.0, 0.0, default_tempo)]
            self.out_dict["bpmEvents"].append({"bpm" : default_tempo, "time" : 0})

        # print("Ticks per beat: " + str(mid.ticks_per_beat))
        # print("Tempo Changes: " + str(tempo_events))
        queued_msgs = []
        total_time = 0
        print('Track len: ' + str(len(self.track_to_convert)))
        for msg in self.track_to_convert:
            if msg.time > 0:
                for queued_msg in queued_msgs:
                    note = queued_msg.note
                    # print('queued')
                    # print(queued_msg.note)
                    toggle_active = False
                    notoggle_hits = []
                    for drum in note_map[note]:
                        drum_name = drum["drum"]
                        drum_hit = {"name" : drum_name, "vel" : queued_msg.velocity, "loc": 0, "time": '%.4f'%total_time}
                        if drum_name in toggle_map_rev and toggle_map_rev[drum_name] in active_toggles:
                            toggle_active = True
                            self.out_dict["events"].append(drum_hit)
                        if drum_name not in toggle_map_rev:
                            notoggle_hits.append(drum_hit)
                    if not toggle_active:
                        for hit in notoggle_hits:
                            self.out_dict["events"].append(hit)
                queued_msgs.clear()

            total_ticks += msg.time
            # print('Total ticks: ' + str(total_ticks) + ' Msg time: ' + str(msg.time))
            while (tempo_index+1 < len(tempo_events)) and (total_ticks > tempo_events[tempo_index+1][0]):
                tempo_index += 1
            tempo = tempo_events[tempo_index][2]
            # print('Tempo: ' + str(tempo))
            # total_time = total_time + mido.tick2second(msg.time, mid.ticks_per_beat, tempo) # old method of computing time, was slightly off
            total_time = tempo_events[tempo_index][1] + mido.tick2second(total_ticks - tempo_events[tempo_index][0], mid.ticks_per_beat, tempo)
            # print(str(msg.type) + " " + str(msg.time) + " total ticks: " + str(total_ticks) + " total time: " + str(total_time))
            if(total_time > longest_time):
                longest_time = total_time
            if not msg.is_meta:
                if msg.type == "note_on":
                    note = msg.note
                    # print(msg.note)
                    #we ignore velocity 0 notes here? 
                    if note in toggle_map:
                        if note not in active_toggles:
                            active_toggles.append(note)
                    if note in note_map and msg.velocity > 0:
                        hits = []
                        has_toggle = False
                        for drum in note_map[note]:
                            # if this drum has to be toggled on by a note, 
                            # check to see if the toggle note is active right now.
                            # might have to go ahead and look at all the other notes
                            # at this tick first before doing this
                            drum_name = drum["drum"]
                            # print(drum_name)
                            if drum_name in toggle_map_rev:
                                has_toggle = True
                                if msg not in queued_msgs:
                                    queued_msgs.append(copy.deepcopy(msg))
                            else:
                                drum_hit = {"name" : drum_name, "vel" : msg.velocity, "loc": 0, "time": '%.4f'%total_time}
                                hits.append(drum_hit)
                            # print(str(drum_hit) + " tempo: " + str(tempo) + " total ticks: " + str(total_ticks))
                        if not has_toggle:
                            for hit in hits:
                                self.out_dict["events"].append(hit)
                if msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    note = msg.note
                    if note in toggle_map:
                        active_toggles.remove(note)
        # print(tempo_index)
        print("Ticks Per Beat " + str(mid.ticks_per_beat) + ", Tempo " + str(tempo) + ", BPM " + '%.2f'%tempo2bpm(tempo))
        print("Midi File Length " + str(mid.length))
        print("Our totaled file length " + str(longest_time))
        # print(out_dict)

    def create_midi_map(self, midi_yaml):
        '''Construct dicts for each difficulty that
        are in the form [note] : {'drum': [drum_class]}
        This makes lookups easier later on when we analyze the midi file.'''
        self.note_to_drum_maps.clear()
        self.toggle_to_drum_maps.clear()
        for diff in self.difficulty_names:
            note_map = {}
            toggle_map = {}
            print(midi_yaml[diff.lower()])
            diff_map = midi_yaml[diff.lower()]
            if not diff_map or len(diff_map) == 0:
                continue
            for drum in diff_map:
                if type(diff_map[drum]) == list:
                    self.extract_midi_notes(note_map, diff_map[drum], drum)
                else:
                    drum_map = diff_map[drum]
                    if 'toggle_note' in drum_map:
                        toggle_map[drum_map['toggle_note']] = 'BP_%s_C' % drum
                    if 'notes' in drum_map:
                        self.extract_midi_notes(note_map, drum_map['notes'], drum)
            self.note_to_drum_maps.append(note_map)
            self.toggle_to_drum_maps.append(toggle_map)

    def extract_midi_notes(self, note_map, note_list, drum_name):
        for note in note_list:
            if type(note) == str:
                note.replace(' ', '')
                if len(note.split('-')) > 1:
                    min_note = int(note.split('-')[0])
                    max_note = int(note.split('-')[1])
                    for range_note in range(min_note, max_note+1):
                        if range_note not in note_map:
                            note_map[range_note] = []
                        note_map[range_note].append({'drum': 'BP_%s_C' % (drum_name)})
                else:
                    try:
                        str_note = int(note)
                        if str_note not in note_map:
                            note_map[str_note] = []
                        note_map[str_note].append({'drum' : 'BP_%s_C' % drum_name})
                    except ValueError:
                        print("Not a valid number!")
            else:
                if note not in note_map:
                    note_map[note] = []
                note_map[note].append({'drum' : 'BP_%s_C' % drum_name})

    def convert_to_rlrr(self):
        print("Converting to rlrr...")
        self.analyze_midi_file()
        # Filter out empty strings from track lists
        flt_drum_tracks = [x for x in self.drum_tracks if x.strip()]
        flt_song_tracks = [x for x in self.song_tracks if x.strip()]

        # use whichever is longer for our overall song length
        last_event_time = 0
        if "events" in self.out_dict and len(self.out_dict["events"]):
            last_event_time = float(self.out_dict["events"][-1]["time"])
        track_to_load = flt_song_tracks[0] if len(flt_song_tracks) else (flt_drum_tracks[0] if len(flt_drum_tracks) else None)        
        length = last_event_time
        if track_to_load:
            try:
                print("Track to load: " + track_to_load)
                track_sf = sf.SoundFile(track_to_load)
                track_len = len(track_sf) / track_sf.samplerate
                print('audio track seconds = {}'.format(track_len))
                length = track_len if last_event_time < track_len else last_event_time
            except Exception as e:
                print("Error loading audio track: " + str(e))
        print("last event time: " + str(last_event_time) + " length: " + str(length))

        short_dtracks = [x.split('/')[-1] for x in flt_drum_tracks]
        short_stracks = [x.split('/')[-1] for x in flt_song_tracks]

        # check the length of one of the audio files vs the last event's timestamp in rlrr

        # audio_file_short = audio_file.split('/')[-1]
        cover_image_short = self.cover_image_path.split('/')[-1]
        self.audio_file_data['songTracks'] = short_stracks
        self.audio_file_data['drumTracks'] = short_dtracks
        self.audio_file_data['calibrationOffset'] = self.calibration_offset
        self.out_dict["audioFileData"] = self.audio_file_data

        self.recording_metadata['title'] = self.song_name
        self.recording_metadata['description'] = self.recording_description
        self.recording_metadata['coverImagePath'] = cover_image_short
        self.recording_metadata['artist'] = self.artist_name
        self.recording_metadata['creator'] = self.author_name
        self.recording_metadata['complexity'] = self.song_complexity
        if self.length > 0:
            self.recording_metadata['length'] = length
        self.out_dict["recordingMetadata"] = self.recording_metadata

        output_folder_path = os.path.join(self.output_rlrr_dir, self.song_name)
        if not os.path.isdir(output_folder_path):
            os.makedirs(output_folder_path)
        
        all_tracks = flt_drum_tracks + flt_song_tracks
        for track in all_tracks:
            copyfile(track, output_folder_path + '/' + track.split('/')[-1])
        if self.cover_image_path:
            copyfile(self.cover_image_path, output_folder_path + '/' + cover_image_short)    
        
        with open(os.path.join(self.output_rlrr_dir,self.song_name) + '/' + self.song_name + '_' + self.difficulty + '.rlrr', 'w') as outfile:  
            json.dump(self.out_dict, outfile, indent=4)
            print("Conversion done!")
            return True