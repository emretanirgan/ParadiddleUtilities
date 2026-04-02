import type { MidiNote } from '../types/midi.types';
import type { DrumMapping } from '../types/mapping.types';

/**
 * Piano roll renderer using Canvas API.
 * Renders MIDI notes as colored rectangles in instrument lanes.
 * Reference: song_display.py lines 823-983
 */

export interface RenderConfig {
  width: number;
  height: number;
  zoom: number;
  scrollOffset: number;
  currentTime: number;
  duration: number;
}

export interface InstrumentLane {
  name: string;
  color: string;
  drumClass: string;
}

// Drum color mapping (linear sRGB converted)
export const DRUM_COLORS: Record<string, string> = {
  Snare: '#96001c',
  HiHat: '#389c9b',
  Tom1: '#2a6265',
  Tom2: '#0d3b00',
  FloorTom: '#3b1c69',
  Kick: '#222e76',
  China: '#3dc54f',
  Crash13: '#b89400',
  Crash15: '#961c8e',
  Crash17: '#e66945',
  Ride17: '#ffff00',
  Ride20: '#e97000',
  BongoH: '#3b3596',
  BongoL: '#6c4d35',
  Timpani1: '#5a3b82',
  Timp2: '#6a4b96',
  Timp3: '#af6ec3',
  Tambourine1: '#963547',
  Tambourine2: '#965651',
  Triangle: '#62966e',
  Gong: '#9b564b',
  Cowbell: '#712e16',
  Xylophone: '#cc5565',
  Marimba: '#4ba793',
  Glockenspiel: '#dc8166',
};

export class PianoRollRenderer {
  private ctx: CanvasRenderingContext2D;
  private config: RenderConfig;

  constructor(canvas: HTMLCanvasElement, config: RenderConfig) {
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Could not get 2D context from canvas');
    }
    this.ctx = ctx;
    this.config = config;

    // Set canvas resolution for sharp rendering
    const dpr = window.devicePixelRatio || 1;
    canvas.width = config.width * dpr;
    canvas.height = config.height * dpr;
    canvas.style.width = `${config.width}px`;
    canvas.style.height = `${config.height}px`;
    ctx.scale(dpr, dpr);
  }

  /**
   * Update render configuration
   */
  updateConfig(config: Partial<RenderConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Convert time (seconds) to x coordinate
   */
  private timeToX(time: number): number {
    const pixelsPerSecond = (this.config.width * this.config.zoom) / this.config.duration;
    return time * pixelsPerSecond - this.config.scrollOffset;
  }

  /**
   * Convert x coordinate to time (seconds)
   */
  timeFromX(x: number): number {
    const pixelsPerSecond = (this.config.width * this.config.zoom) / this.config.duration;
    return (x + this.config.scrollOffset) / pixelsPerSecond;
  }

  /**
   * Clear the canvas
   */
  clear(): void {
    this.ctx.fillStyle = '#0f172a'; // Dark background
    this.ctx.fillRect(0, 0, this.config.width, this.config.height);
  }

  /**
   * Draw grid lines and time markers
   */
  drawGrid(): void {
    const { width, height, duration, zoom } = this.config;

    // Draw time grid (every second or 5 seconds depending on zoom)
    const timeInterval = zoom < 1 ? 5 : 1;
    this.ctx.strokeStyle = '#1e293b';
    this.ctx.lineWidth = 1;

    for (let t = 0; t <= duration; t += timeInterval) {
      const x = this.timeToX(t);
      if (x >= 0 && x <= width) {
        this.ctx.beginPath();
        this.ctx.moveTo(x, 0);
        this.ctx.lineTo(x, height);
        this.ctx.stroke();

        // Draw time label
        this.ctx.fillStyle = '#475569';
        this.ctx.font = '10px monospace';
        this.ctx.fillText(`${t}s`, x + 2, 12);
      }
    }
  }

  /**
   * Draw instrument lanes (horizontal dividers)
   */
  drawLanes(lanes: InstrumentLane[]): void {
    const { height } = this.config;
    const laneHeight = height / lanes.length;

    this.ctx.strokeStyle = '#1e293b';
    this.ctx.lineWidth = 1;

    lanes.forEach((lane, index) => {
      const y = index * laneHeight;

      // Draw lane divider
      if (index > 0) {
        this.ctx.beginPath();
        this.ctx.moveTo(0, y);
        this.ctx.lineTo(this.config.width, y);
        this.ctx.stroke();
      }

      // Draw lane label
      this.ctx.fillStyle = '#94a3b8';
      this.ctx.font = 'bold 12px sans-serif';
      this.ctx.fillText(lane.name, 8, y + laneHeight / 2 + 4);
    });
  }

  /**
   * Draw MIDI notes in their respective lanes
   */
  drawNotes(
    notes: MidiNote[],
    lanes: InstrumentLane[],
    noteMap: Map<number, DrumMapping[]>
  ): void {
    const { height } = this.config;
    const laneHeight = height / lanes.length;

    // Create drum class to lane index mapping
    const drumClassToLaneIndex = new Map<string, number>();
    lanes.forEach((lane, index) => {
      drumClassToLaneIndex.set(lane.drumClass, index);
    });

    notes.forEach((note) => {
      // Get mapped drum for this MIDI note
      const mappedDrums = noteMap.get(note.note);
      if (!mappedDrums || mappedDrums.length === 0) {
        return; // Skip unmapped notes
      }

      // Use first drum mapping (handle multiple mappings if needed)
      const drumClass = mappedDrums[0].drum;
      const laneIndex = drumClassToLaneIndex.get(drumClass);

      if (laneIndex === undefined) {
        return; // Skip if lane not found
      }

      const lane = lanes[laneIndex];
      const x = this.timeToX(note.time);
      const y = laneIndex * laneHeight;
      const width = Math.max(2, this.timeToX(note.time + note.duration) - x);

      // Skip notes outside visible area
      if (x + width < 0 || x > this.config.width) {
        return;
      }

      // Calculate opacity based on velocity (0-127 → 0.3-1.0)
      const opacity = 0.3 + (note.velocity / 127) * 0.7;

      // Draw note rectangle
      this.ctx.fillStyle = lane.color + Math.floor(opacity * 255).toString(16).padStart(2, '0');
      this.ctx.fillRect(x, y + 2, width, laneHeight - 4);

      // Draw note border
      this.ctx.strokeStyle = lane.color;
      this.ctx.lineWidth = 1;
      this.ctx.strokeRect(x, y + 2, width, laneHeight - 4);
    });
  }

  /**
   * Draw playhead (current time indicator)
   */
  drawPlayhead(): void {
    const x = this.timeToX(this.config.currentTime);

    if (x >= 0 && x <= this.config.width) {
      this.ctx.strokeStyle = '#3b82f6';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, this.config.height);
      this.ctx.stroke();
    }
  }

  /**
   * Full render: clear, grid, lanes, notes, playhead
   */
  render(
    notes: MidiNote[],
    lanes: InstrumentLane[],
    noteMap: Map<number, DrumMapping[]>
  ): void {
    this.clear();
    this.drawGrid();
    this.drawLanes(lanes);
    this.drawNotes(notes, lanes, noteMap);
    this.drawPlayhead();
  }
}
