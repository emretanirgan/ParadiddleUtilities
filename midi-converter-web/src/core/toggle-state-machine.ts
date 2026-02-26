import type { DrumMapping } from '../types/mapping.types';
import type { DrumEvent } from '../types/rlrr.types';

/**
 * State for tracking active toggle notes.
 */
export interface ToggleState {
  activeToggles: Set<number>;
}

/**
 * A queued MIDI message that needs to be processed after all simultaneous notes.
 */
interface QueuedNote {
  note: number;
  velocity: number;
  time: number;
}

/**
 * Manages toggle note state for Rock Band-style MIDI mappings.
 * Toggle notes modify the behavior of other notes while held.
 *
 * Ported from midiconvert.py lines 255-282
 */
export class ToggleStateMachine {
  private noteMap: Map<number, DrumMapping[]>;
  private toggleMap: Map<number, string>; // toggle note -> drum class
  private toggleMapReverse: Map<string, number>; // drum class -> toggle note
  private state: ToggleState;
  private queuedNotes: QueuedNote[];

  constructor(
    noteMap: Map<number, DrumMapping[]>,
    toggleMap: Map<number, string>
  ) {
    this.noteMap = noteMap;
    this.toggleMap = toggleMap;
    this.toggleMapReverse = this.reverseToggleMap(toggleMap);
    this.state = { activeToggles: new Set() };
    this.queuedNotes = [];
  }

  /**
   * Create reverse map: drum class -> toggle note
   */
  private reverseToggleMap(toggleMap: Map<number, string>): Map<string, number> {
    const reversed = new Map<string, number>();
    for (const [note, drumClass] of toggleMap.entries()) {
      reversed.set(drumClass, note);
    }
    return reversed;
  }

  /**
   * Process a note_on event.
   * Returns array of drum events to add (may be empty if queued).
   *
   * Python reference: lines 255-278
   */
  processNoteOn(note: number, velocity: number, time: number): DrumEvent[] {
    const events: DrumEvent[] = [];

    // Check if this is a toggle note
    if (this.toggleMap.has(note)) {
      if (!this.state.activeToggles.has(note)) {
        this.state.activeToggles.add(note);
      }
    }

    // Check if this note triggers drums
    if (this.noteMap.has(note) && velocity > 0) {
      const hits: DrumEvent[] = [];
      let hasToggle = false;

      for (const mapping of this.noteMap.get(note)!) {
        const drumName = mapping.drum;

        // If this drum requires a toggle note, queue it for later
        if (this.toggleMapReverse.has(drumName)) {
          hasToggle = true;
          // Queue this note to be processed after all simultaneous notes
          if (!this.queuedNotes.some((q) => q.note === note && q.time === time)) {
            this.queuedNotes.push({ note, velocity, time });
          }
        } else {
          // No toggle required, add immediately
          hits.push({
            name: drumName,
            vel: velocity,
            loc: 0,
            time: time.toFixed(4),
          });
        }
      }

      // If no toggle required, add all hits
      if (!hasToggle) {
        events.push(...hits);
      }
    }

    return events;
  }

  /**
   * Process a note_off event.
   *
   * Python reference: lines 279-282
   */
  processNoteOff(note: number): void {
    if (this.toggleMap.has(note)) {
      this.state.activeToggles.delete(note);
    }
  }

  /**
   * Process queued notes when time advances (msg.time > 0).
   * This handles the case where multiple notes occur at the same tick
   * and we need to know all active toggles before processing.
   *
   * Python reference: lines 219-237
   */
  processQueuedNotes(currentTime: number): DrumEvent[] {
    const events: DrumEvent[] = [];

    for (const queued of this.queuedNotes) {
      const note = queued.note;
      let toggleActive = false;
      const noToggleHits: DrumEvent[] = [];

      if (this.noteMap.has(note)) {
        for (const mapping of this.noteMap.get(note)!) {
          const drumName = mapping.drum;
          const drumHit: DrumEvent = {
            name: drumName,
            vel: queued.velocity,
            loc: 0,
            time: currentTime.toFixed(4),
          };

          // Check if this drum requires a toggle and if it's active
          if (this.toggleMapReverse.has(drumName)) {
            const toggleNote = this.toggleMapReverse.get(drumName)!;
            if (this.state.activeToggles.has(toggleNote)) {
              toggleActive = true;
              events.push(drumHit);
            }
          } else {
            noToggleHits.push(drumHit);
          }
        }

        // If no toggle was active, use non-toggle hits
        if (!toggleActive) {
          events.push(...noToggleHits);
        }
      }
    }

    // Clear the queue
    this.queuedNotes = [];

    return events;
  }

  /**
   * Check if there are queued notes waiting to be processed.
   */
  hasQueuedNotes(): boolean {
    return this.queuedNotes.length > 0;
  }

  /**
   * Get the current state (for debugging).
   */
  getState(): ToggleState {
    return this.state;
  }

  /**
   * Reset the state machine.
   */
  reset(): void {
    this.state.activeToggles.clear();
    this.queuedNotes = [];
  }
}
