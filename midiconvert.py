from mido import MidiFile
from mido import tempo2bpm
import mido
import json
import os

out_dict = {}  
# TODO set up GUI for input midi, input drum set, output recording file names with file dialogs for each

# TODO user should specify drum set file path, if not use default set file
# If this file is not fed in, then use default
# drum_set_file = '/Users/etanirgan/test.json'
drum_set_file = ''

script_dir = os.path.dirname(os.path.realpath(__file__))
default_set_name = "defaultset.json"
default_set_full_path = os.path.join(script_dir, default_set_name)
print(default_set_full_path)

if drum_set_file == '':
    drum_set_file = default_set_full_path
drum_set_dict = None

with open(drum_set_file) as f:
    drum_set_dict = json.load(f)
    print(len(drum_set_dict["DrumLayout"]))

# TODO put in actual default notes
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

out_dict["DrumHits"] = []
midi_file_name = script_dir + '/midi_files/notes.mid'
mid = MidiFile(midi_file_name)

tempo = 500000
#list of tuples in the form of (total_ticks, new_tempo)
tempo_events = [(0.0, tempo)]
total_time = 0.0
total_ticks = 0.0
longest_time = 0.0

#TODO Pick track to convert to rlrr
#TODO need default midi mappings for rhythm game midi format - get difficulties, map from those midi notes
#https://rockband.scorehero.com/forum/viewtopic.php?t=1711
#https://www.scorehero.com/forum/viewtopic.php?t=1179
#TODO convert from .chart
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
                # print(msg.tempo)
                # print("TEMPO")
                # print(msg.time)
                tempo_total_ticks += msg.time
                tempo_events.append((tempo_total_ticks, msg.tempo))

print("Tempo Changes: " + str(tempo_events))
for msg in track_to_convert:
    total_ticks += msg.time
    # print(msg.time)
    while (tempo_index+1 < len(tempo_events)) and (total_ticks > tempo_events[tempo_index+1][0]):
        tempo_index += 1
        print(tempo_index)
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
            #ignore velocity 0 notes here? Seem to be getting a lot of these in the rhythm game midis 
            # print(msg.velocity)
            # print(msg.type)
            if note in note_to_drums_map and msg.velocity > 0:
                drum_name = note_to_drums_map[note][0]
                drum_hit = {"DrumName" : drum_name, "Vel" : msg.velocity, "Loc": 0, "Time": '%.4f'%total_time}
                out_dict["DrumHits"].append(drum_hit)
            #else:
                #print(msg.note)
            # print(json.dumps(drum_hit))
            # print(msg)
print(tempo_index)
print("Ticks Per Beat " + str(mid.ticks_per_beat) + ", Tempo " + str(tempo) + ", BPM " + '%.2f'%tempo2bpm(tempo))
print("Midi File Length " + str(mid.length))
print("Our totaled file length " + str(longest_time))


# TODO pretty print
with open(script_dir + '/rlrr_files/' + midi_file_name.split('/')[-1].split('.')[0] + '_converted.json', 'w') as outfile:  
    json.dump(out_dict, outfile)

