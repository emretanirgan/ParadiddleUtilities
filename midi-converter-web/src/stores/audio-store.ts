import { create } from 'zustand';

const PEAKS_PER_SECOND = 100;

// Stored outside Zustand — not serialisable, must not trigger re-renders.
let _sourceNodes: AudioBufferSourceNode[] = [];

interface AudioStore {
  songTracks: File[];
  drumTracks: File[];
  songPreview: File | null;
  coverImage: File | null;
  calibrationOffset: number;
  waveformPeaks: Float32Array | null;

  // Playback state
  audioContext: AudioContext | null;
  songAudioBuffers: AudioBuffer[];
  drumAudioBuffers: AudioBuffer[];
  playbackOffset: number;       // song position (seconds) where play last started
  startContextTime: number;     // audioContext.currentTime at that moment

  addSongTrack: (file: File) => void;
  removeSongTrack: (index: number) => void;
  addDrumTrack: (file: File) => void;
  removeDrumTrack: (index: number) => void;
  setSongPreview: (file: File | null) => void;
  setCoverImage: (file: File | null) => void;
  setCalibrationOffset: (offset: number) => void;
  decodeAudioBuffer: (file: File, kind: 'song' | 'drum') => Promise<void>;

  // Playback controls — call these alongside uiState.setPlaying()
  play: (offset: number, enableSongTracks?: boolean, enableDrumTracks?: boolean) => void;
  pause: () => void;
  getPlaybackTime: () => number;

  reset: () => void;
}

export const useAudioStore = create<AudioStore>((set, get) => ({
  songTracks: [],
  drumTracks: [],
  songPreview: null,
  coverImage: null,
  calibrationOffset: 0,
  waveformPeaks: null,
  audioContext: null,
  songAudioBuffers: [],
  drumAudioBuffers: [],
  playbackOffset: 0,
  startContextTime: 0,

  addSongTrack: (file: File) => {
    set((state) => ({ songTracks: [...state.songTracks, file].slice(0, 5) }));
    void get().decodeAudioBuffer(file, 'song');
  },

  removeSongTrack: (index: number) => {
    set((state) => ({
      songTracks: state.songTracks.filter((_, i) => i !== index),
      songAudioBuffers: state.songAudioBuffers.filter((_, i) => i !== index),
    }));
  },

  addDrumTrack: (file: File) => {
    set((state) => ({ drumTracks: [...state.drumTracks, file].slice(0, 4) }));
    void get().decodeAudioBuffer(file, 'drum');
  },

  removeDrumTrack: (index: number) => {
    set((state) => ({
      drumTracks: state.drumTracks.filter((_, i) => i !== index),
      drumAudioBuffers: state.drumAudioBuffers.filter((_, i) => i !== index),
    }));
  },

  setSongPreview: (file: File | null) => set({ songPreview: file }),
  setCoverImage: (file: File | null) => set({ coverImage: file }),
  setCalibrationOffset: (offset: number) => set({ calibrationOffset: offset }),

  decodeAudioBuffer: async (file: File, kind: 'song' | 'drum') => {
    const arrayBuffer = await file.arrayBuffer();

    let ctx = get().audioContext;
    if (!ctx || ctx.state === 'closed') {
      ctx = new AudioContext();
      set({ audioContext: ctx });
    }

    const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

    if (kind === 'drum') {
      set((state) => ({ drumAudioBuffers: [...state.drumAudioBuffers, audioBuffer] }));
      return;
    }

    // Song track — append buffer and generate waveform peaks from the first one
    const prevSong = get().songAudioBuffers;
    const isFirst = prevSong.length === 0;
    set({ songAudioBuffers: [...prevSong, audioBuffer] });

    if (!isFirst) return;

    const numChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const length = audioBuffer.length;
    const windowSize = Math.floor(sampleRate / PEAKS_PER_SECOND);
    const numPeaks = Math.ceil(length / windowSize);
    const peaks = new Float32Array(numPeaks);

    const channels: Float32Array[] = [];
    for (let c = 0; c < numChannels; c++) channels.push(audioBuffer.getChannelData(c));

    let maxPeak = 0;
    for (let i = 0; i < numPeaks; i++) {
      const start = i * windowSize;
      const end = Math.min(start + windowSize, length);
      let peak = 0;
      for (let s = start; s < end; s++) {
        let sample = 0;
        for (let c = 0; c < numChannels; c++) sample += Math.abs(channels[c][s]);
        sample /= numChannels;
        if (sample > peak) peak = sample;
      }
      peaks[i] = peak;
      if (peak > maxPeak) maxPeak = peak;
    }

    if (maxPeak > 0) for (let i = 0; i < peaks.length; i++) peaks[i] /= maxPeak;
    set({ waveformPeaks: peaks });
  },

  play: (offset: number, enableSongTracks = true, enableDrumTracks = true) => {
    const { songAudioBuffers, drumAudioBuffers } = get();
    const activeBuffers = [
      ...(enableSongTracks ? songAudioBuffers : []),
      ...(enableDrumTracks ? drumAudioBuffers : []),
    ];
    if (activeBuffers.length === 0 && !get().audioContext) return;

    let ctx = get().audioContext;
    if (!ctx || ctx.state === 'closed') {
      ctx = new AudioContext();
      set({ audioContext: ctx });
    }
    if (ctx.state === 'suspended') ctx.resume();

    for (const node of _sourceNodes) {
      try { node.stop(); } catch { /* already stopped */ }
    }
    _sourceNodes = [];

    for (const buf of activeBuffers) {
      const source = ctx.createBufferSource();
      source.buffer = buf;
      source.connect(ctx.destination);
      source.start(0, Math.max(0, offset));
      _sourceNodes.push(source);
    }

    set({ playbackOffset: offset, startContextTime: ctx.currentTime });
  },

  pause: () => {
    const { audioContext, startContextTime, playbackOffset } = get();
    const elapsed = audioContext ? audioContext.currentTime - startContextTime : 0;
    set({ playbackOffset: playbackOffset + elapsed });

    for (const node of _sourceNodes) {
      try { node.stop(); } catch { /* already stopped */ }
    }
    _sourceNodes = [];
  },

  // Call this each animation frame — reads AudioContext clock directly, no re-renders
  getPlaybackTime: () => {
    const { audioContext, startContextTime, playbackOffset } = get();
    if (!audioContext) return playbackOffset;
    return audioContext.currentTime - startContextTime + playbackOffset;
  },

  reset: () => {
    for (const node of _sourceNodes) {
      try { node.stop(); } catch { /* already stopped */ }
    }
    _sourceNodes = [];
    set({
      songTracks: [],
      drumTracks: [],
      songPreview: null,
      coverImage: null,
      calibrationOffset: 0,
      waveformPeaks: null,
      songAudioBuffers: [],
      drumAudioBuffers: [],
      playbackOffset: 0,
      startContextTime: 0,
    });
  },
}));
