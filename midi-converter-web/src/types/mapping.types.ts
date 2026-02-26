export interface MidiMapping {
  easy: DifficultyMapping;
  medium: DifficultyMapping;
  hard: DifficultyMapping;
  expert: DifficultyMapping;
}

export interface DifficultyMapping {
  [drumName: string]: number[] | ToggleNoteMapping;
}

export interface ToggleNoteMapping {
  notes: number[];
  toggle_note: number;
}

export interface DrumMapping {
  drum: string;
}

export interface DrumSet {
  instruments: Array<{
    name: string;
    class: string;
    location: [number, number, number];
    rotation: [number, number, number];
    scale: [number, number, number];
  }>;
}
