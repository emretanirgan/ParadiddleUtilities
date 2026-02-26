export interface MidiTrack {
  name: string;
  index: number;
  notes: MidiNote[];
}

export interface MidiNote {
  note: number;
  time: number;
  duration: number;
  velocity: number;
  channel: number;
}

export interface TempoEvent {
  tick: number;
  time: number;
  tempo: number;
  bpm: number;
}

export interface MidiParseResult {
  tracks: MidiTrack[];
  trackNames: string[];
  defaultTrackIndex: number;
  ticksPerBeat: number;
  duration: number;
  tempoEvents: TempoEvent[];
}
