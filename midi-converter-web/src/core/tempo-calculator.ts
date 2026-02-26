import type { TempoEvent } from '../types/midi.types';

/**
 * Handles tempo-aware timing calculations for MIDI files.
 * Ported from midiconvert.py lines 191-246
 */
export class TempoCalculator {
  private tempoEvents: TempoEvent[];
  private ticksPerBeat: number;

  constructor(tempoEvents: TempoEvent[], ticksPerBeat: number) {
    this.tempoEvents = tempoEvents;
    this.ticksPerBeat = ticksPerBeat;
  }

  /**
   * Convert MIDI ticks to seconds, accounting for tempo changes.
   * Python reference: total_time = tempo_events[tempo_index][1] +
   *   mido.tick2second(total_ticks - tempo_events[tempo_index][0], mid.ticks_per_beat, tempo)
   */
  tickToSeconds(tick: number): number {
    // Find the active tempo event at this tick
    const tempoIndex = this.findTempoIndex(tick);
    const tempoEvent = this.tempoEvents[tempoIndex];

    // Calculate time: base time + delta from tempo event
    const deltaTicks = tick - tempoEvent.tick;
    const deltaSeconds = this.ticksToSecondsWithTempo(
      deltaTicks,
      tempoEvent.tempo
    );

    return tempoEvent.time + deltaSeconds;
  }

  /**
   * Find the index of the active tempo event for a given tick.
   * Uses linear search (matches Python implementation).
   */
  private findTempoIndex(tick: number): number {
    let index = 0;
    while (
      index + 1 < this.tempoEvents.length &&
      tick > this.tempoEvents[index + 1].tick
    ) {
      index++;
    }
    return index;
  }

  /**
   * Convert ticks to seconds using a specific tempo.
   * Formula: seconds = (ticks * tempo) / (ticks_per_beat * 1_000_000)
   * tempo is in microseconds per quarter note.
   */
  private ticksToSecondsWithTempo(ticks: number, tempo: number): number {
    // Python: mido.tick2second(ticks, ticks_per_beat, tempo)
    return (ticks * tempo) / (this.ticksPerBeat * 1_000_000);
  }

  /**
   * Convert tempo (microseconds per quarter note) to BPM.
   */
  static tempoToBPM(tempo: number): number {
    return 60_000_000 / tempo;
  }

  /**
   * Convert BPM to tempo (microseconds per quarter note).
   */
  static bpmToTempo(bpm: number): number {
    return 60_000_000 / bpm;
  }

  /**
   * Get the tempo (in microseconds per quarter note) at a given time.
   */
  getTempoAtTime(time: number): number {
    for (let i = this.tempoEvents.length - 1; i >= 0; i--) {
      if (time >= this.tempoEvents[i].time) {
        return this.tempoEvents[i].tempo;
      }
    }
    return this.tempoEvents[0]?.tempo || 500000; // Default: 120 BPM
  }

  /**
   * Get the BPM at a given time.
   */
  getBPMAtTime(time: number): number {
    return TempoCalculator.tempoToBPM(this.getTempoAtTime(time));
  }
}
