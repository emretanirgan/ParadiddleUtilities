import { parse } from 'yaml';
import type {
  MidiMapping,
  ToggleNoteMapping,
  DrumMapping,
} from '../types/mapping.types';

/**
 * Processes MIDI mapping YAML files and converts them to efficient lookup structures.
 * Ported from midiconvert.py lines 346-393
 */
export class MappingProcessor {
  /**
   * Parse YAML content into MidiMapping structure.
   */
  parseYAML(yamlContent: string): MidiMapping {
    const parsed = parse(yamlContent) as any;

    return {
      easy: parsed.easy || {},
      medium: parsed.medium || {},
      hard: parsed.hard || {},
      expert: parsed.expert || {},
    };
  }

  /**
   * Create note-to-drum and toggle note lookup maps for all difficulties.
   * Returns array indexed by difficulty: [easy, medium, hard, expert]
   */
  createNoteMaps(mapping: MidiMapping): {
    noteToInstrument: Map<number, DrumMapping[]>[];
    toggleNotes: Map<number, string>[];
  } {
    const difficulties: (keyof MidiMapping)[] = ['easy', 'medium', 'hard', 'expert'];
    const noteToInstrument: Map<number, DrumMapping[]>[] = [];
    const toggleNotes: Map<number, string>[] = [];

    for (const difficulty of difficulties) {
      const diffMap = mapping[difficulty];
      const noteMap = new Map<number, DrumMapping[]>();
      const toggleMap = new Map<number, string>();

      if (!diffMap || Object.keys(diffMap).length === 0) {
        // Empty mapping for this difficulty
        noteToInstrument.push(noteMap);
        toggleNotes.push(toggleMap);
        continue;
      }

      // Process each drum in the difficulty mapping
      for (const drumName in diffMap) {
        const drumData = diffMap[drumName];

        if (Array.isArray(drumData)) {
          // Simple array of notes: [42, 46] or ["42-46"]
          this.extractMidiNotes(noteMap, drumData, drumName);
        } else if (typeof drumData === 'object') {
          // Toggle note mapping: { notes: [...], toggle_note: 110 }
          const toggleNoteMapping = drumData as ToggleNoteMapping;

          if (toggleNoteMapping.toggle_note !== undefined) {
            toggleMap.set(toggleNoteMapping.toggle_note, `BP_${drumName}_C`);
          }

          if (toggleNoteMapping.notes) {
            this.extractMidiNotes(noteMap, toggleNoteMapping.notes, drumName);
          }
        }
      }

      noteToInstrument.push(noteMap);
      toggleNotes.push(toggleMap);
    }

    return { noteToInstrument, toggleNotes };
  }

  /**
   * Extract MIDI notes from a note list and add them to the note map.
   * Handles:
   * - Individual notes: 42, 46
   * - Note ranges: "42-46" (expands to [42, 43, 44, 45, 46])
   * - String notes: "42" (converts to number)
   *
   * Python reference: extract_midi_notes() lines 371-393
   */
  private extractMidiNotes(
    noteMap: Map<number, DrumMapping[]>,
    noteList: (number | string)[],
    drumName: string
  ): void {
    const drumClass = `BP_${drumName}_C`;

    for (const note of noteList) {
      if (typeof note === 'string') {
        // Handle string notes (could be ranges like "42-46" or single notes like "42")
        const cleaned = note.replace(/\s/g, '');

        if (cleaned.includes('-')) {
          // Range: "42-46"
          const [minStr, maxStr] = cleaned.split('-');
          const minNote = parseInt(minStr, 10);
          const maxNote = parseInt(maxStr, 10);

          if (!isNaN(minNote) && !isNaN(maxNote)) {
            for (let n = minNote; n <= maxNote; n++) {
              this.addNoteMapping(noteMap, n, drumClass);
            }
          } else {
            console.warn(`Invalid note range: ${note}`);
          }
        } else {
          // Single note as string: "42"
          const singleNote = parseInt(cleaned, 10);
          if (!isNaN(singleNote)) {
            this.addNoteMapping(noteMap, singleNote, drumClass);
          } else {
            console.warn(`Invalid note number: ${note}`);
          }
        }
      } else if (typeof note === 'number') {
        // Direct number: 42
        this.addNoteMapping(noteMap, note, drumClass);
      }
    }
  }

  /**
   * Add a note-to-drum mapping to the map.
   */
  private addNoteMapping(
    noteMap: Map<number, DrumMapping[]>,
    note: number,
    drumClass: string
  ): void {
    if (!noteMap.has(note)) {
      noteMap.set(note, []);
    }
    noteMap.get(note)!.push({ drum: drumClass });
  }

  /**
   * Get the note map for a specific difficulty index.
   * If the difficulty doesn't have a mapping, falls back to the highest available.
   * Python reference: midiconvert.py line 183
   */
  static getNoteMapsForDifficulty(
    noteMaps: Map<number, DrumMapping[]>[],
    difficultyIndex: number
  ): Map<number, DrumMapping[]> {
    const index = Math.min(difficultyIndex, noteMaps.length - 1);
    return noteMaps[index] || new Map();
  }

  /**
   * Get the toggle map for a specific difficulty index.
   */
  static getToggleMapsForDifficulty(
    toggleMaps: Map<number, string>[],
    difficultyIndex: number
  ): Map<number, string> {
    const index = Math.min(difficultyIndex, toggleMaps.length - 1);
    return toggleMaps[index] || new Map();
  }
}
