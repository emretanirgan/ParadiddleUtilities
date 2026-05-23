import type { MidiNote, TempoEvent } from '../types/midi.types';
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
  waveformHeight: number; // pixels reserved at top for waveform (0 = no waveform)
  tempoEvents: TempoEvent[];
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

const PEAKS_PER_SECOND = 100;
export const LABEL_WIDTH = 100;  // px reserved on left for lane names
export const HEADER_HEIGHT = 20; // px reserved at top of roll for bar number labels

export class PianoRollRenderer {
  private ctx: CanvasRenderingContext2D;
  private config: RenderConfig;
  private waveformPeaks: Float32Array | null = null;

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

  updateConfig(config: Partial<RenderConfig>): void {
    this.config = { ...this.config, ...config };
  }

  setWaveformPeaks(peaks: Float32Array | null): void {
    this.waveformPeaks = peaks;
  }

  private get pixelsPerSecond(): number {
    return ((this.config.width - LABEL_WIDTH) * this.config.zoom) / this.config.duration;
  }

  /**
   * Convert time (seconds) to x coordinate in the scrollable area
   */
  private timeToX(time: number): number {
    return LABEL_WIDTH + time * this.pixelsPerSecond - this.config.scrollOffset;
  }

  /**
   * Convert x coordinate to time (seconds)
   */
  timeFromX(x: number): number {
    return (x - LABEL_WIDTH + this.config.scrollOffset) / this.pixelsPerSecond;
  }

  clear(): void {
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fillRect(0, 0, this.config.width, this.config.height);
  }

  drawWaveform(): void {
    const { width, waveformHeight, scrollOffset, duration } = this.config;
    if (!this.waveformPeaks || waveformHeight <= 0) return;

    const peaks = this.waveformPeaks;
    const midY = waveformHeight / 2;
    const amplitude = midY * 0.9;
    const pps = this.pixelsPerSecond;

    // Waveform background — only in the scrollable area
    this.ctx.fillStyle = '#0f1f3d';
    this.ctx.fillRect(LABEL_WIDTH, 0, width - LABEL_WIDTH, waveformHeight);

    // Separator line
    this.ctx.strokeStyle = '#334155';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(LABEL_WIDTH, waveformHeight);
    this.ctx.lineTo(width, waveformHeight);
    this.ctx.stroke();

    // Draw waveform: one column per pixel in scrollable area
    this.ctx.fillStyle = '#3b82f6';
    for (let px = LABEL_WIDTH; px < width; px++) {
      const time = (px - LABEL_WIDTH + scrollOffset) / pps;
      if (time < 0 || time > duration) continue;

      const peakIndex = Math.floor(time * PEAKS_PER_SECOND);
      const peak = peaks[peakIndex] ?? 0;
      const barHeight = peak * amplitude;

      this.ctx.fillRect(px, midY - barHeight, 1, barHeight * 2);
    }

    // Centre line
    this.ctx.strokeStyle = '#1e40af';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(LABEL_WIDTH, midY);
    this.ctx.lineTo(width, midY);
    this.ctx.stroke();
  }

  drawGrid(): void {
    const { width, height, waveformHeight, duration, tempoEvents } = this.config;
    // rollTop is below the waveform; notes start after HEADER_HEIGHT within the roll
    const rollTop = waveformHeight;
    const headerBottom = rollTop + HEADER_HEIGHT;
    const rollHeight = height - headerBottom;
    const pps = this.pixelsPerSecond;

    // Header background
    this.ctx.fillStyle = '#0a101a';
    this.ctx.fillRect(LABEL_WIDTH, rollTop, width - LABEL_WIDTH, HEADER_HEIGHT);

    // Separator between header and lanes
    this.ctx.strokeStyle = '#1e293b';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(LABEL_WIDTH, headerBottom);
    this.ctx.lineTo(width, headerBottom);
    this.ctx.stroke();

    // Fallback to time-based grid if no tempo data
    if (!tempoEvents || tempoEvents.length === 0) {
      const timeInterval = this.pixelsPerSecond < 50 ? 5 : 1;
      this.ctx.strokeStyle = '#1e293b';
      this.ctx.lineWidth = 1;
      for (let t = 0; t <= duration; t += timeInterval) {
        const x = this.timeToX(t);
        if (x >= LABEL_WIDTH && x <= width) {
          this.ctx.beginPath();
          this.ctx.moveTo(x, headerBottom);
          this.ctx.lineTo(x, headerBottom + rollHeight);
          this.ctx.stroke();
          this.ctx.fillStyle = '#475569';
          this.ctx.font = '10px monospace';
          this.ctx.fillText(`${t}s`, x + 2, headerBottom - 4);
        }
      }
      return;
    }

    const BEATS_PER_BAR = 4; // assume 4/4
    let beatInBar = 0;
    let barNumber = 1;
    let lastLabelX = -Infinity;

    for (let i = 0; i < tempoEvents.length; i++) {
      const event = tempoEvents[i];
      const nextEvent = tempoEvents[i + 1];
      const segmentEnd = nextEvent ? nextEvent.time : duration;
      const beatDuration = 60 / event.bpm;
      const pixelsPerBeat = beatDuration * pps;
      const showBeats = pixelsPerBeat >= 8;
      const showHalfBeats = pixelsPerBeat >= 40;

      let t = event.time;
      while (t < segmentEnd - beatDuration * 0.01) {
        const x = this.timeToX(t);
        const isBarLine = beatInBar === 0;

        if (x >= LABEL_WIDTH && x <= width) {
          if (isBarLine) {
            // Bar line — brighter, full height
            this.ctx.strokeStyle = '#232d3a';
            this.ctx.lineWidth = 1;
            this.ctx.beginPath();
            this.ctx.moveTo(x, headerBottom);
            this.ctx.lineTo(x, headerBottom + rollHeight);
            this.ctx.stroke();

            // Tick mark into header
            this.ctx.strokeStyle = '#475569';
            this.ctx.beginPath();
            this.ctx.moveTo(x, rollTop);
            this.ctx.lineTo(x, headerBottom);
            this.ctx.stroke();

            // Bar number label in header
            if (x - lastLabelX > 40) {
              this.ctx.fillStyle = '#64748b';
              this.ctx.font = '10px monospace';
              this.ctx.fillText(`${barNumber}`, x + 3, headerBottom - 5);
              lastLabelX = x;
            }
          } else if (showBeats) {
            // Beat line — dim, lanes only
            this.ctx.strokeStyle = '#1e293b';
            this.ctx.lineWidth = 1;
            this.ctx.beginPath();
            this.ctx.moveTo(x, headerBottom);
            this.ctx.lineTo(x, headerBottom + rollHeight);
            this.ctx.stroke();
          }
        }

        // Half-beat subdivision — only at high zoom
        if (showHalfBeats) {
          const halfX = this.timeToX(t + beatDuration / 2);
          if (halfX >= LABEL_WIDTH && halfX <= width) {
            this.ctx.strokeStyle = '#162530';
            this.ctx.lineWidth = 1;
            this.ctx.beginPath();
            this.ctx.moveTo(halfX, headerBottom);
            this.ctx.lineTo(halfX, headerBottom + rollHeight);
            this.ctx.stroke();
          }
        }

        t += beatDuration;
        beatInBar = (beatInBar + 1) % BEATS_PER_BAR;
        if (beatInBar === 0) barNumber++;
      }
    }
  }

  drawLanes(lanes: InstrumentLane[]): void {
    const { height, waveformHeight, width } = this.config;
    const lanesTop = waveformHeight + HEADER_HEIGHT;
    const rollHeight = height - lanesTop;
    const laneHeight = rollHeight / lanes.length;

    this.ctx.strokeStyle = '#1e293b';
    this.ctx.lineWidth = 1;

    lanes.forEach((_lane, index) => {
      const y = lanesTop + index * laneHeight;

      // Lane background — full width including label column
      this.ctx.fillStyle = index % 2 === 0 ? '#0f172a' : '#11181c';
      this.ctx.fillRect(0, y, width, laneHeight);

      if (index > 0) {
        this.ctx.beginPath();
        this.ctx.moveTo(0, y);
        this.ctx.lineTo(width, y);
        this.ctx.stroke();
      }
    });

    // Vertical separator between label column and scrollable area
    this.ctx.strokeStyle = '#334155';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(LABEL_WIDTH, waveformHeight);
    this.ctx.lineTo(LABEL_WIDTH, height);
    this.ctx.stroke();
  }

  drawLaneLabels(lanes: InstrumentLane[]): void {
    const { height, waveformHeight } = this.config;
    const lanesTop = waveformHeight + HEADER_HEIGHT;
    const rollHeight = height - lanesTop;
    const laneHeight = rollHeight / lanes.length;

    this.ctx.font = 'bold 11px sans-serif';
    this.ctx.textBaseline = 'middle';

    lanes.forEach((lane, index) => {
      const y = lanesTop + index * laneHeight + laneHeight / 2;

      // Colored dot
      this.ctx.fillStyle = lane.color;
      this.ctx.beginPath();
      this.ctx.arc(10, y, 4, 0, Math.PI * 2);
      this.ctx.fill();

      // Label text, clipped to label column
      this.ctx.fillStyle = '#94a3b8';
      this.ctx.fillText(lane.name, 20, y, LABEL_WIDTH - 24);
    });

    this.ctx.textBaseline = 'alphabetic'; // reset
  }

  drawNotes(
    notes: MidiNote[],
    lanes: InstrumentLane[],
    noteMap: Map<number, DrumMapping[]>
  ): void {
    const { height, waveformHeight } = this.config;
    const lanesTop = waveformHeight + HEADER_HEIGHT;
    const rollHeight = height - lanesTop;
    const laneHeight = rollHeight / lanes.length;

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
      const y = lanesTop + laneIndex * laneHeight;
      const width = Math.max(2, this.timeToX(note.time + note.duration) - x);

      // Skip notes outside visible area
      if (x + width < LABEL_WIDTH || x > this.config.width) {
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

    if (x >= LABEL_WIDTH && x <= this.config.width) {
      this.ctx.strokeStyle = '#3b82f6';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, this.config.height);
      this.ctx.stroke();
    }
  }

  render(
    notes: MidiNote[],
    lanes: InstrumentLane[],
    noteMap: Map<number, DrumMapping[]>
  ): void {
    this.clear();
    this.drawWaveform();
    this.drawLanes(lanes);
    this.drawGrid();
    this.drawNotes(notes, lanes, noteMap);
    this.drawPlayhead();
    this.drawLaneLabels(lanes);
  }
}
