import { useMemo } from 'react';
import { useMidiStore } from '../stores/midi-store';
import { useMappingStore } from '../stores/mapping-store';
import { MappingProcessor } from '../core/mapping-processor';

export interface NoteStats {
  totalMidiNotes: number;
  mappedNotes: number;
  unmappedCount: number;
  unmappedNoteNumbers: number[];
}

export function useNoteStats(): NoteStats | null {
  const parsed = useMidiStore((s) => s.parsed);
  const selectedTrackIndex = useMidiStore((s) => s.selectedTrackIndex);
  const mapping = useMappingStore((s) => s.mapping);
  const difficulty = useMappingStore((s) => s.difficulty);

  return useMemo(() => {
    if (!parsed || !mapping) {
      return null;
    }

    const track = parsed.tracks[selectedTrackIndex];
    if (!track) return null;

    const totalMidiNotes = track.notes.length;

    const processor = new MappingProcessor();
    const { noteToInstrument } = processor.createNoteMaps(mapping);
    const difficultyIndex = ['easy', 'medium', 'hard', 'expert'].indexOf(difficulty);
    const noteMap = noteToInstrument[difficultyIndex] || new Map();

    let mappedNotes = 0;
    const unmappedNoteNumbers = new Set<number>();

    for (const note of track.notes) {
      if (noteMap.has(note.note)) {
        mappedNotes++;
      } else {
        unmappedNoteNumbers.add(note.note);
      }
    }

    return {
      totalMidiNotes,
      mappedNotes,
      unmappedCount: totalMidiNotes - mappedNotes,
      unmappedNoteNumbers: Array.from(unmappedNoteNumbers).sort((a, b) => a - b),
    };
  }, [parsed, selectedTrackIndex, mapping, difficulty]);
}
