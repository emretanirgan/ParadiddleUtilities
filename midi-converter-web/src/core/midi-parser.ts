import { Midi } from '@tonejs/midi';
import type { MidiParseResult, MidiTrack, MidiNote, TempoEvent } from '../types/midi.types';
import { TempoCalculator } from './tempo-calculator';

/**
 * Parses MIDI files and extracts track, note, and tempo information.
 * Uses @tonejs/midi library (browser-compatible).
 */
export class MidiParser {
  /**
   * Parse a MIDI file from a File object.
   */
  async parse(file: File): Promise<MidiParseResult> {
    const arrayBuffer = await file.arrayBuffer();
    const midi = new Midi(arrayBuffer);

    // Extract tempo events from all tracks
    const tempoEvents = this.extractTempoEvents(midi);

    // Extract tracks with notes
    const tracks = this.extractTracks(midi);

    // Find default track (first track with "drum" in name, or track 0)
    const defaultTrackIndex = this.findDefaultTrackIndex(tracks);

    return {
      tracks,
      trackNames: tracks.map((t) => t.name),
      defaultTrackIndex,
      ticksPerBeat: midi.header.ppq, // Pulses Per Quarter note
      duration: midi.duration,
      tempoEvents,
    };
  }

  /**
   * Extract tempo events from MIDI file.
   * Python reference: midiconvert.py lines 191-211
   */
  private extractTempoEvents(midi: Midi): TempoEvent[] {
    const events: TempoEvent[] = [];
    const defaultTempo = 500000; // 120 BPM

    // @tonejs/midi stores tempo changes in header
    if (midi.header.tempos && midi.header.tempos.length > 0) {
      for (const tempoChange of midi.header.tempos) {
        const ticks = tempoChange.ticks ?? 0;
        const tempo = TempoCalculator.bpmToTempo(tempoChange.bpm);

        events.push({
          tick: ticks,
          time: tempoChange.time ?? 0,
          tempo: tempo,
          bpm: tempoChange.bpm,
        });
      }
    }

    // If no tempo events, add default
    if (events.length === 0) {
      events.push({
        tick: 0,
        time: 0,
        tempo: defaultTempo,
        bpm: TempoCalculator.tempoToBPM(defaultTempo),
      });
    }

    return events;
  }

  /**
   * Extract all tracks with their notes.
   */
  private extractTracks(midi: Midi): MidiTrack[] {
    return midi.tracks.map((track, index) => {
      const notes: MidiNote[] = track.notes.map((note) => ({
        note: note.midi,
        time: note.time,
        duration: note.duration,
        velocity: Math.round(note.velocity * 127), // @tonejs/midi uses 0-1, convert to 0-127
        channel: track.channel ?? 0,
      }));

      return {
        name: track.name || `Track ${index + 1}`,
        index,
        notes,
      };
    });
  }

  /**
   * Find the default track to convert.
   * Prefers tracks with "drum" in the name, otherwise returns 0.
   * Python reference: get_default_midi_track()
   */
  private findDefaultTrackIndex(tracks: MidiTrack[]): number {
    // Look for "drum" in track name (case-insensitive)
    const drumTrackIndex = tracks.findIndex((track) =>
      track.name.toLowerCase().includes('drum')
    );

    if (drumTrackIndex !== -1) {
      return drumTrackIndex;
    }

    // Return first track with notes
    const trackWithNotes = tracks.findIndex((track) => track.notes.length > 0);
    return trackWithNotes !== -1 ? trackWithNotes : 0;
  }

  /**
   * Get track by index from parsed result.
   */
  static getTrack(parsed: MidiParseResult, index: number): MidiTrack | null {
    return parsed.tracks[index] || null;
  }

  /**
   * Count total events that would be generated for a track.
   * Python reference: count_converted_events()
   */
  static countEvents(track: MidiTrack): number {
    return track.notes.length;
  }
}
