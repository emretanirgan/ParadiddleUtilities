import { create } from 'zustand';
import type { MidiMapping, DrumSet } from '../types/mapping.types';
import { MappingProcessor } from '../core/mapping-processor';

type Difficulty = 'easy' | 'medium' | 'hard' | 'expert';

interface MappingStore {
  mappingFile: File | null;
  mapping: MidiMapping | null;
  drumSetFile: File | null;
  drumSet: DrumSet | null;
  difficulty: Difficulty;

  loadMapping: (file: File) => Promise<void>;
  loadDrumSet: (file: File) => Promise<void>;
  setDifficulty: (difficulty: Difficulty) => void;
  updateMapping: (mapping: MidiMapping) => void;
  useDefaultMapping: () => Promise<void>;
  useDefaultDrumSet: () => Promise<void>;
  reset: () => void;
}

export const useMappingStore = create<MappingStore>((set) => ({
  mappingFile: null,
  mapping: null,
  drumSetFile: null,
  drumSet: null,
  difficulty: 'expert',

  loadMapping: async (file: File) => {
    try {
      const text = await file.text();
      const processor = new MappingProcessor();
      const mapping = processor.parseYAML(text);
      set({ mappingFile: file, mapping });
      console.log('✅ Mapping file loaded:', mapping);
    } catch (error) {
      console.error('Failed to parse mapping file:', error);
      set({ mappingFile: null, mapping: null });
    }
  },

  loadDrumSet: async (file: File) => {
    try {
      const text = await file.text();
      const drumSet: DrumSet = JSON.parse(text);
      set({ drumSetFile: file, drumSet });
      console.log('✅ Drum set file loaded:', drumSet);
    } catch (error) {
      console.error('Failed to parse drum set file:', error);
      set({ drumSetFile: null, drumSet: null });
    }
  },

  setDifficulty: (difficulty: Difficulty) => {
    set({ difficulty });
  },

  updateMapping: (mapping: MidiMapping) => {
    set({ mapping });
    console.log('✅ Mapping updated');
  },

  useDefaultMapping: async () => {
    try {
      // Simple default mapping (bypasses YAML CSP issue)
      // Based on General MIDI drum kit standard
      const defaultMapping: MidiMapping = {
        easy: {
          Kick: [35, 36],
          Snare: [38, 40],
          HiHat: [42, 44, 46],
          Tom1: [48, 50],
          FloorTom: [41, 43, 45],
          Crash17: [49, 57],
          Ride20: [51, 59],
        },
        medium: {
          Kick: [35, 36],
          Snare: [38, 40],
          HiHat: [42, 44, 46],
          Tom1: [48, 50],
          FloorTom: [41, 43, 45],
          Crash17: [49, 57],
          Ride20: [51, 59],
        },
        hard: {
          Kick: [35, 36],
          Snare: [38, 40],
          HiHat: [42, 44, 46],
          Tom1: [48, 50],
          FloorTom: [41, 43, 45],
          Crash17: [49, 57],
          Ride20: [51, 59],
        },
        expert: {
          Kick: [35, 36],
          Snare: [38, 40],
          HiHat: [42, 44, 46],
          Tom1: [48, 50],
          FloorTom: [41, 43, 45],
          Crash17: [49, 57],
          Ride20: [51, 59],
        },
      };

      set({ mapping: defaultMapping });
      console.log('✅ Default mapping loaded');
    } catch (error) {
      console.error('Failed to load default mapping:', error);
    }
  },

  useDefaultDrumSet: async () => {
    try {
      const response = await fetch('/assets/drum-sets/defaultset.json');
      if (!response.ok) {
        throw new Error('Failed to fetch drum set');
      }
      const drumSet: DrumSet = await response.json();
      set({ drumSet });
      console.log('✅ Default drum set loaded:', drumSet);
    } catch (error) {
      console.error('Failed to load default drum set:', error);
    }
  },

  reset: () => {
    set({
      mappingFile: null,
      mapping: null,
      drumSetFile: null,
      drumSet: null,
      difficulty: 'expert',
    });
  },
}));
