import { create } from 'zustand';

type ViewMode = 'mapped' | 'raw';

interface TrackToggles {
  drums: boolean;
  audio: boolean;
  midi: boolean;
}

interface UIStore {
  viewMode: ViewMode;
  zoom: number;
  scrollOffset: number;
  currentTime: number;
  isPlaying: boolean;
  trackToggles: TrackToggles;

  setViewMode: (mode: ViewMode) => void;
  setZoom: (zoom: number) => void;
  setScrollOffset: (offset: number) => void;
  setCurrentTime: (time: number) => void;
  togglePlayback: () => void;
  setPlaying: (isPlaying: boolean) => void;
  toggleTrack: (track: keyof TrackToggles) => void;
  reset: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  viewMode: 'mapped',
  zoom: 1.0,
  scrollOffset: 0,
  currentTime: 0,
  isPlaying: false,
  trackToggles: {
    drums: true,
    audio: true,
    midi: true,
  },

  setViewMode: (mode: ViewMode) => {
    set({ viewMode: mode });
  },

  setZoom: (zoom: number) => {
    set({ zoom: Math.max(0.1, Math.min(10, zoom)) });
  },

  setScrollOffset: (offset: number) => {
    set({ scrollOffset: Math.max(0, offset) });
  },

  setCurrentTime: (time: number) => {
    set({ currentTime: Math.max(0, time) });
  },

  togglePlayback: () => {
    set((state) => ({ isPlaying: !state.isPlaying }));
  },

  setPlaying: (isPlaying: boolean) => {
    set({ isPlaying });
  },

  toggleTrack: (track: keyof TrackToggles) => {
    set((state) => ({
      trackToggles: {
        ...state.trackToggles,
        [track]: !state.trackToggles[track],
      },
    }));
  },

  reset: () => {
    set({
      viewMode: 'mapped',
      zoom: 1.0,
      scrollOffset: 0,
      currentTime: 0,
      isPlaying: false,
      trackToggles: {
        drums: true,
        audio: true,
        midi: true,
      },
    });
  },
}));
