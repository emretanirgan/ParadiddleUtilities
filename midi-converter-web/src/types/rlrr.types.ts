export interface RLRROutput {
  version: number;
  authoringTool: string;
  recordingMetadata: RecordingMetadata;
  audioFileData: AudioFileData;
  instruments: Instrument[];
  events: DrumEvent[];
  bpmEvents: BPMEvent[];
}

export interface DrumEvent {
  name: string;
  vel: number;
  loc: number;
  time: string;
}

export interface BPMEvent {
  bpm: number;
  time: number;
}

export interface Instrument {
  name: string;
  class: string;
  location: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
}

export interface RecordingMetadata {
  title: string;
  description: string;
  coverImagePath: string;
  artist: string;
  creator: string;
  length: number;
  complexity: number;
}

export interface AudioFileData {
  songTracks: string[];
  drumTracks: string[];
  songPreview: string;
  calibrationOffset: number;
}
