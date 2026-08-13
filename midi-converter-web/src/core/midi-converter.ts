import type { MidiParseResult, MidiTrack } from '../types/midi.types';
import type { MidiMapping, DrumSet, DrumMapping } from '../types/mapping.types';
import type { RLRROutput, RecordingMetadata, BPMEvent, DrumEvent, AudioFileData } from '../types/rlrr.types';
import { MappingProcessor } from './mapping-processor';
import { ToggleStateMachine } from './toggle-state-machine';

export type Difficulty = 'easy' | 'medium' | 'hard' | 'expert';

/**
 * Main MIDI to RLRR converter class.
 * Orchestrates the entire conversion process.
 * Ported from midiconvert.py
 */
export class MidiConverter {
  private static readonly DIFFICULTY_NAMES: Difficulty[] = ['easy', 'medium', 'hard', 'expert'];

  /**
   * Convert MIDI to RLRR format.
   */
  static async convert(
    midiParsed: MidiParseResult,
    mapping: MidiMapping,
    drumSet: DrumSet,
    difficulty: Difficulty,
    metadata: RecordingMetadata,
    trackIndex?: number,
    audioFileData?: AudioFileData
  ): Promise<RLRROutput> {
    // Use provided track index or default
    const selectedTrackIndex = trackIndex ?? midiParsed.defaultTrackIndex;
    const track = midiParsed.tracks[selectedTrackIndex];

    if (!track) {
      throw new Error(`Track ${selectedTrackIndex} not found`);
    }

    // Process mapping
    const mappingProcessor = new MappingProcessor();
    const { noteToInstrument, toggleNotes } = mappingProcessor.createNoteMaps(mapping);

    // Get maps for selected difficulty
    const diffIndex = this.DIFFICULTY_NAMES.indexOf(difficulty);
    const noteMap = this.getNoteMapsForDifficulty(noteToInstrument, diffIndex);
    const toggleMap = this.getToggleMapsForDifficulty(toggleNotes, diffIndex);

    // Resolve drum class names to actual instrument names from drum set
    this.resolveDrumNames(noteMap, toggleMap, drumSet);

    // Convert MIDI notes to drum events
    // Note: @tonejs/midi already converts tick times to seconds, so we don't need tempoEvents/ticksPerBeat here
    const events = this.convertTrackToEvents(track, noteMap, toggleMap);

    // Build BPM events
    const bpmEvents: BPMEvent[] = midiParsed.tempoEvents.map((te) => ({
      bpm: te.bpm,
      time: te.time,
    }));

    // Calculate song length (use metadata length if provided, otherwise use MIDI duration)
    const songLength = metadata.length || midiParsed.duration;

    // Build output
    const output: RLRROutput = {
      version: 0.7,
      authoringTool: 'ParadiddleUtilities WebConverter',
      recordingMetadata: {
        ...metadata,
        length: songLength,
      },
      audioFileData: audioFileData ?? {
        songTracks: [],
        drumTracks: [],
        songPreview: '',
        calibrationOffset: 0,
      },
      instruments: drumSet.instruments,
      events: events,
      bpmEvents: bpmEvents,
    };

    return output;
  }

  /**
   * Convert a MIDI track to drum events.
   * Note times from @tonejs/midi are already in seconds (tempo-adjusted).
   */
  private static convertTrackToEvents(
    track: MidiTrack,
    noteMap: Map<number, DrumMapping[]>,
    toggleMap: Map<number, string>
  ): DrumEvent[] {
    const events: DrumEvent[] = [];
    const toggleSM = new ToggleStateMachine(noteMap, toggleMap);

    // Sort notes by time (they should already be sorted, but just in case)
    const sortedNotes = [...track.notes].sort((a, b) => a.time - b.time);

    let lastTime = -1;

    for (const note of sortedNotes) {
      const time = note.time;

      // Process queued notes when time advances
      if (time > lastTime && lastTime >= 0) {
        const queuedEvents = toggleSM.processQueuedNotes(time);
        events.push(...queuedEvents);
      }

      // Process note on
      const noteOnEvents = toggleSM.processNoteOn(note.note, note.velocity, time);
      events.push(...noteOnEvents);

      lastTime = time;
    }

    // Process any remaining queued notes
    if (toggleSM.hasQueuedNotes()) {
      const finalEvents = toggleSM.processQueuedNotes(lastTime + 0.001);
      events.push(...finalEvents);
    }

    // Sort events by time
    events.sort((a, b) => parseFloat(a.time) - parseFloat(b.time));

    return events;
  }

  /**
   * Resolve drum class names (BP_Kick_C) to actual instrument names from drum set.
   * Python reference: lines 166-187
   */
  private static resolveDrumNames(
    noteMap: Map<number, DrumMapping[]>,
    toggleMap: Map<number, string>,
    drumSet: DrumSet
  ): void {
    const instruments = drumSet.instruments;

    // Resolve note map drum names
    for (const [_note, mappings] of noteMap.entries()) {
      for (const mapping of mappings) {
        const drumClass = mapping.drum;
        const matchingDrums = instruments.filter((d) => d.class === drumClass);

        if (matchingDrums.length > 0) {
          mapping.drum = matchingDrums[0].name;
        } else {
          // Fallback: use class name + "Default"
          mapping.drum = drumClass + 'Default';
          console.warn(`No instrument found for class ${drumClass}, using fallback`);
        }
      }
    }

    // Resolve toggle map drum names
    for (const [toggleNote, drumClass] of toggleMap.entries()) {
      const matchingDrums = instruments.filter((d) => d.class === drumClass);

      if (matchingDrums.length > 0) {
        toggleMap.set(toggleNote, matchingDrums[0].name);
      } else {
        toggleMap.set(toggleNote, drumClass + 'Default');
        console.warn(`No instrument found for class ${drumClass}, using fallback`);
      }
    }
  }

  /**
   * Get note maps for a specific difficulty, with fallback.
   */
  private static getNoteMapsForDifficulty(
    noteMaps: Map<number, DrumMapping[]>[],
    difficultyIndex: number
  ): Map<number, DrumMapping[]> {
    const index = Math.min(difficultyIndex, noteMaps.length - 1);
    const originalMap = noteMaps[index] || new Map();

    // Deep copy to avoid mutations
    const copy = new Map<number, DrumMapping[]>();
    for (const [key, value] of originalMap.entries()) {
      copy.set(key, value.map((v) => ({ ...v })));
    }

    return copy;
  }

  /**
   * Get toggle maps for a specific difficulty, with fallback.
   */
  private static getToggleMapsForDifficulty(
    toggleMaps: Map<number, string>[],
    difficultyIndex: number
  ): Map<number, string> {
    const index = Math.min(difficultyIndex, toggleMaps.length - 1);
    const originalMap = toggleMaps[index] || new Map();

    // Deep copy
    return new Map(originalMap);
  }

  /**
   * Count how many events would be generated.
   */
  static countEvents(
    midiParsed: MidiParseResult,
    _mapping: MidiMapping,
    _difficulty: Difficulty,
    trackIndex?: number
  ): number {
    const selectedTrackIndex = trackIndex ?? midiParsed.defaultTrackIndex;
    const track = midiParsed.tracks[selectedTrackIndex];

    if (!track) {
      return 0;
    }

    // Simple count: number of notes (actual count may vary with toggle logic)
    return track.notes.length;
  }
}
