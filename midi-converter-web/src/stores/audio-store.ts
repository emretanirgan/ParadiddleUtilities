import { create } from 'zustand';

interface AudioStore {
  songTracks: File[];
  drumTracks: File[];
  songPreview: File | null;
  coverImage: File | null;
  calibrationOffset: number;

  addSongTrack: (file: File) => void;
  removeSongTrack: (index: number) => void;
  addDrumTrack: (file: File) => void;
  removeDrumTrack: (index: number) => void;
  setSongPreview: (file: File | null) => void;
  setCoverImage: (file: File | null) => void;
  setCalibrationOffset: (offset: number) => void;
  reset: () => void;
}

export const useAudioStore = create<AudioStore>((set) => ({
  songTracks: [],
  drumTracks: [],
  songPreview: null,
  coverImage: null,
  calibrationOffset: 0,

  addSongTrack: (file: File) => {
    set((state) => ({
      songTracks: [...state.songTracks, file].slice(0, 5), // Max 5
    }));
  },

  removeSongTrack: (index: number) => {
    set((state) => ({
      songTracks: state.songTracks.filter((_, i) => i !== index),
    }));
  },

  addDrumTrack: (file: File) => {
    set((state) => ({
      drumTracks: [...state.drumTracks, file].slice(0, 4), // Max 4
    }));
  },

  removeDrumTrack: (index: number) => {
    set((state) => ({
      drumTracks: state.drumTracks.filter((_, i) => i !== index),
    }));
  },

  setSongPreview: (file: File | null) => {
    set({ songPreview: file });
  },

  setCoverImage: (file: File | null) => {
    set({ coverImage: file });
  },

  setCalibrationOffset: (offset: number) => {
    set({ calibrationOffset: offset });
  },

  reset: () => {
    set({
      songTracks: [],
      drumTracks: [],
      songPreview: null,
      coverImage: null,
      calibrationOffset: 0,
    });
  },
}));
