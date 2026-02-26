import { create } from 'zustand';
import type { RLRROutput, RecordingMetadata } from '../types/rlrr.types';
import { MidiConverter } from '../core/midi-converter';
import { FileHandler } from '../utils/file-handlers';
import { useMidiStore } from './midi-store';
import { useMappingStore } from './mapping-store';
import { useAudioStore } from './audio-store';

interface ConversionStore {
  metadata: RecordingMetadata;
  isConverting: boolean;
  result: RLRROutput | null;
  error: string | null;

  updateMetadata: (partial: Partial<RecordingMetadata>) => void;
  convert: () => Promise<void>;
  downloadRLRR: () => Promise<void>;
  downloadJSON: () => void;
  reset: () => void;
}

const defaultMetadata: RecordingMetadata = {
  title: '',
  description: '',
  coverImagePath: '',
  artist: '',
  creator: '',
  length: 0,
  complexity: 1,
};

export const useConversionStore = create<ConversionStore>((set, get) => ({
  metadata: defaultMetadata,
  isConverting: false,
  result: null,
  error: null,

  updateMetadata: (partial: Partial<RecordingMetadata>) => {
    set((state) => ({
      metadata: { ...state.metadata, ...partial },
    }));
  },

  convert: async () => {
    set({ isConverting: true, error: null });
    try {
      // Get data from other stores
      const midiState = useMidiStore.getState();
      const mappingState = useMappingStore.getState();

      // Validate we have all required data
      if (!midiState.parsed) {
        throw new Error('No MIDI file loaded. Please upload a MIDI file first.');
      }

      if (!mappingState.mapping) {
        throw new Error('No MIDI mapping loaded. Please load a mapping file or use default.');
      }

      if (!mappingState.drumSet) {
        throw new Error('No drum set loaded. Please load a drum set or use default.');
      }

      const { metadata } = get();

      if (!metadata.title) {
        throw new Error('Please provide a song title.');
      }

      // Run conversion
      console.log('Starting MIDI to RLRR conversion...');
      const result = await MidiConverter.convert(
        midiState.parsed,
        mappingState.mapping,
        mappingState.drumSet,
        mappingState.difficulty,
        metadata,
        midiState.selectedTrackIndex
      );

      console.log('Conversion successful!', result);
      set({ result, isConverting: false });
    } catch (error) {
      console.error('Conversion error:', error);
      set({
        error: error instanceof Error ? error.message : 'Conversion failed',
        isConverting: false,
      });
    }
  },

  downloadRLRR: async () => {
    const { result, metadata } = get();
    if (!result) {
      console.warn('No conversion result to download');
      return;
    }

    try {
      const audioState = useAudioStore.getState();
      const mappingState = useMappingStore.getState();

      const songName = metadata.title || 'song';
      const difficulty = mappingState.difficulty;

      // Create ZIP package
      console.log('Creating ZIP package...');
      const zipBlob = await FileHandler.createRLRRPackage(
        result,
        songName,
        difficulty,
        {
          songTracks: audioState.songTracks,
          drumTracks: audioState.drumTracks,
          songPreview: audioState.songPreview || undefined,
          coverImage: audioState.coverImage || undefined,
        }
      );

      // Download ZIP
      const zipFilename = `${songName}.zip`;
      FileHandler.downloadBlob(zipBlob, zipFilename);
      console.log(`Downloaded ${zipFilename}`);
    } catch (error) {
      console.error('Download error:', error);
      set({
        error: error instanceof Error ? error.message : 'Download failed',
      });
    }
  },

  downloadJSON: () => {
    const { result, metadata } = get();
    const mappingState = useMappingStore.getState();

    if (!result) {
      console.warn('No conversion result to download');
      return;
    }

    const songName = metadata.title || 'song';
    const difficulty = mappingState.difficulty;
    const filename = `${songName}_${difficulty}.rlrr`;

    FileHandler.downloadJSON(result, filename);
    console.log(`Downloaded ${filename}`);
  },

  reset: () => {
    set({
      metadata: defaultMetadata,
      isConverting: false,
      result: null,
      error: null,
    });
  },
}));
