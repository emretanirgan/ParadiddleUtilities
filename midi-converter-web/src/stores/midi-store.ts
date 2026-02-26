import { create } from 'zustand';
import type { MidiParseResult } from '../types/midi.types';
import { MidiParser } from '../core/midi-parser';

interface MidiStore {
  file: File | null;
  parsed: MidiParseResult | null;
  selectedTrackIndex: number;
  isLoading: boolean;
  error: string | null;

  loadMidiFile: (file: File) => Promise<void>;
  selectTrack: (index: number) => void;
  reset: () => void;
}

export const useMidiStore = create<MidiStore>((set) => ({
  file: null,
  parsed: null,
  selectedTrackIndex: 0,
  isLoading: false,
  error: null,

  loadMidiFile: async (file: File) => {
    set({ isLoading: true, error: null });
    try {
      const parser = new MidiParser();
      const parsed = await parser.parse(file);
      set({
        file,
        parsed,
        selectedTrackIndex: parsed.defaultTrackIndex,
        isLoading: false,
      });
      console.log('MIDI file parsed:', parsed);
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to parse MIDI file',
        isLoading: false,
      });
      console.error('Failed to parse MIDI:', error);
    }
  },

  selectTrack: (index: number) => {
    set({ selectedTrackIndex: index });
  },

  reset: () => {
    set({
      file: null,
      parsed: null,
      selectedTrackIndex: 0,
      isLoading: false,
      error: null,
    });
  },
}));
