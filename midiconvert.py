from mido import MidiFile
import json
import os

out_dict = {}  
# TODO set up GUI for input midi, input drum set, output recording file names with file dialogs for each

# TODO user should specify drum set file path, if not use default set file
# If this file is not fed in, then use default
# drum_set_file = '/Users/etanirgan/test.json'
drum_set_file = ''

script_dir = os.path.dirname(os.path.realpath(__file__))
default_set_path = "defaultset.json"
default_set_full_path = os.path.join(script_dir, default_set_path)
print(default_set_full_path)

if drum_set_file == '':
    drum_set_file = default_set_full_path
drum_set_dict = None

with open(drum_set_file) as f:
    drum_set_dict = json.load(f)
    print(len(drum_set_dict["DrumLayout"]))

# TODO put in actual default notes
class_to_default_notes = {
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

rhythm_midi_notes = {

}
note_to_drums_map = {}

if drum_set_dict is None:
    for drum_class in class_to_default_notes:
        print(drum_class)
        note_to_drums_map[class_to_default_notes[drum_class]]= [str(drum_class)+"Default"]
else:
    for drum_obj in drum_set_dict["DrumLayout"]:
        note_to_drums_map[class_to_default_notes[drum_obj["Class"]]] = [str(drum_obj["DrumName"])]
    out_dict["DrumLayout"] = drum_set_dict["DrumLayout"]

out_dict["DrumHits"] = []
midi_file_name = 'C:/Users/Emre/Perforce/ParadiddleUtilities/midi_files/notes.mid'
mid = MidiFile(midi_file_name)
print(note_to_drums_map)

tempo = 50000
total_time = 0.0
longest_time = 0.0

#TODO Pick track to convert to rlrr
#TODO need default midi mappings for rhythm game midi format - get difficulties, map from those midi notes
#https://rockband.scorehero.com/forum/viewtopic.php?t=1711
#https://www.scorehero.com/forum/viewtopic.php?t=1179
#TODO convert from .chart
#TODO don't hard code midi and rlrr file paths

for i, track in enumerate(mid.tracks):
    print('Track {}: {}'.format(i, track.name))
    # total_time = 0.0

    for msg in track:
        if msg.is_meta:
            if msg.type == "set_tempo":
                tempo = msg.tempo
            #   print(msg.tempo)
        total_time += msg.time * (60000.0 / (tempo * float(mid.ticks_per_beat)))
        # print(total_time)
        if(total_time > longest_time):
            longest_time = total_time
        # print msg.tempo
        if not msg.is_meta:
            # print(msg.type)
            if msg.type == "note_on":
                # a = 2
                # print("Note " + str(msg.note))
                drum_name = "Test"
                if msg.note in note_to_drums_map:
                    drum_name = note_to_drums_map[msg.note][0]
                    drum_hit = {"DrumName" : drum_name, "Vel" : msg.velocity, "Loc": 1, "Time": '%.3f'%total_time}
                    out_dict["DrumHits"].append(drum_hit)
                #else:
                    #print(msg.note)
                # print(json.dumps(drum_hit))
                # print(msg)
            # print(msg.velocity)
                # print("hello")
            # print(json.dumps({}))
print("Ticks Per Beat " + str(mid.ticks_per_beat) + ", Tempo " + str(tempo))
print("Midi File Length " + str(mid.length))
print("Our totaled file length " + str(longest_time))


# TODO pretty print

with open(script_dir + '/rlrr_files/' + midi_file_name.split('/')[-1].split('.')[0] + '_converted.json', 'w') as outfile:  
    json.dump(out_dict, outfile)

