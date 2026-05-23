import { useEffect, useLayoutEffect, useRef } from 'react';
import { useMidiStore } from '../stores/midi-store';
import { useMappingStore } from '../stores/mapping-store';
import { useUIStore } from '../stores/ui-store';
import { useAudioStore } from '../stores/audio-store';
import { PianoRollRenderer, DRUM_COLORS, type InstrumentLane } from '../visualization/piano-roll-renderer';
import { ZoomPanController } from '../visualization/zoom-pan-controller';
import { MappingProcessor } from '../core/mapping-processor';
import { DrumSynth } from '../visualization/drum-synth';
import type { MidiNote } from '../types/midi.types';
import type { DrumMapping } from '../types/mapping.types';

const WAVEFORM_HEIGHT = 80;

// Palette for raw note lanes — cycles through these by note number
const RAW_COLORS = [
  '#60a5fa', '#34d399', '#f87171', '#fbbf24', '#a78bfa',
  '#f472b6', '#38bdf8', '#4ade80', '#fb923c', '#e879f9',
];

export function VisualizationCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<PianoRollRenderer | null>(null);
  const controllerRef = useRef<ZoomPanController | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const clockFrameRef = useRef<number | null>(null);
  const drumSynthRef = useRef<DrumSynth | null>(null);

  // Refs carrying mapped notes/noteMap from render loop → clock effect
  const mappedNotesRef = useRef<MidiNote[]>([]);
  const mappedNoteMapRef = useRef<Map<number, DrumMapping[]>>(new Map());

  const renderStateRef = useRef({
    zoom: 1,
    scrollOffset: 0,
    currentTime: 0,
    waveformPeaks: null as Float32Array | null,
    isPlaying: false,
    duration: 0,
    viewMode: 'mapped' as 'mapped' | 'raw',
  });

  const midiState = useMidiStore();
  const mappingState = useMappingStore();
  const uiState = useUIStore();
  const audioState = useAudioStore();

  useLayoutEffect(() => {
    renderStateRef.current.zoom = uiState.zoom;
    renderStateRef.current.scrollOffset = uiState.scrollOffset;
    renderStateRef.current.currentTime = uiState.currentTime;
    renderStateRef.current.waveformPeaks = audioState.waveformPeaks;
    renderStateRef.current.isPlaying = uiState.isPlaying;
    renderStateRef.current.duration = midiState.parsed?.duration ?? 0;
    renderStateRef.current.viewMode = uiState.viewMode;
  });

  // Initialize renderer and controller
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !midiState.parsed) return;

    const container = canvas.parentElement;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;
    const { zoom, scrollOffset, currentTime, waveformPeaks } = renderStateRef.current;

    rendererRef.current = new PianoRollRenderer(canvas, {
      width,
      height,
      zoom,
      scrollOffset,
      currentTime,
      duration: midiState.parsed.duration,
      waveformHeight: waveformPeaks ? WAVEFORM_HEIGHT : 0,
      tempoEvents: midiState.parsed.tempoEvents,
    });

    controllerRef.current = new ZoomPanController(canvas, {
      onZoomChange: (z) => uiState.setZoom(z),
      onScrollChange: (o) => uiState.setScrollOffset(o),
      onSeek: (x) => {
        if (rendererRef.current) uiState.setCurrentTime(rendererRef.current.timeFromX(x));
      },
    });

    return () => {
      controllerRef.current?.detach();
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [midiState.parsed]);

  useEffect(() => {
    controllerRef.current?.setZoom(uiState.zoom);
    controllerRef.current?.setScrollOffset(uiState.scrollOffset);
  }, [uiState.zoom, uiState.scrollOffset]);

  // Render loop
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer || !midiState.parsed || !mappingState.mapping || !mappingState.drumSet) return;

    const track = midiState.parsed.tracks[midiState.selectedTrackIndex];
    if (!track) return;

    // Build mapped lanes + noteMap
    const processor = new MappingProcessor();
    const { noteToInstrument } = processor.createNoteMaps(mappingState.mapping);
    const difficultyIndex = ['easy', 'medium', 'hard', 'expert'].indexOf(mappingState.difficulty);
    const mappedNoteMap = MappingProcessor.getNoteMapsForDifficulty(noteToInstrument, difficultyIndex);
    const mappedLanes: InstrumentLane[] = mappingState.drumSet.instruments.map((instrument) => {
      const drumName = instrument.class.replace('BP_', '').replace('_C', '');
      return {
        name: drumName,
        color: DRUM_COLORS[drumName] || '#64c8ff',
        drumClass: instrument.class,
      };
    });

    // Store for use by the clock effect
    mappedNotesRef.current = track.notes;
    mappedNoteMapRef.current = mappedNoteMap;

    // Build raw lanes + noteMap from unique note numbers in the track
    const uniqueNotes = Array.from(new Set(track.notes.map((n) => n.note))).sort((a, b) => a - b);
    const rawNoteMap = new Map<number, DrumMapping[]>();
    const rawLanes: InstrumentLane[] = uniqueNotes.map((noteNum, i) => {
      const key = `raw-${noteNum}`;
      rawNoteMap.set(noteNum, [{ drum: key }]);
      return {
        name: `${noteNum}`,
        color: RAW_COLORS[i % RAW_COLORS.length],
        drumClass: key,
      };
    });

    const render = () => {
      const { zoom, scrollOffset, currentTime, waveformPeaks, viewMode } = renderStateRef.current;
      renderer.updateConfig({
        zoom,
        scrollOffset,
        currentTime,
        waveformHeight: waveformPeaks ? WAVEFORM_HEIGHT : 0,
      });
      renderer.setWaveformPeaks(waveformPeaks);

      const lanes = viewMode === 'raw' ? rawLanes : mappedLanes;
      const noteMap = viewMode === 'raw' ? rawNoteMap : mappedNoteMap;
      renderer.render(track.notes, lanes, noteMap);
      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();
    return () => { if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current); };
  }, [
    midiState.parsed,
    midiState.selectedTrackIndex,
    mappingState.mapping,
    mappingState.drumSet,
    mappingState.difficulty,
  ]);

  // Clock effect
  useEffect(() => {
    if (!uiState.isPlaying) {
      if (clockFrameRef.current) cancelAnimationFrame(clockFrameRef.current);
      drumSynthRef.current?.stopAll();
      return;
    }

    const duration = midiState.parsed?.duration ?? 0;
    const startOffset = uiState.currentTime;
    const { songTracks: enableSong, drumTracks: enableDrum, noteSounds: enableNoteSounds } = uiState.playbackToggles;

    const hasAudio = audioState.songAudioBuffers.length > 0 || audioState.drumAudioBuffers.length > 0;
    if (hasAudio) {
      audioState.play(startOffset, enableSong, enableDrum);
    }

    // Schedule drum synth hits — use existing AudioContext or create one for synth-only playback
    const ctx = audioState.audioContext ?? new AudioContext();
    if (enableNoteSounds) {
      if (ctx.state === 'suspended') ctx.resume();
      drumSynthRef.current = new DrumSynth(ctx);
      drumSynthRef.current.scheduleAll(
        mappedNotesRef.current,
        mappedNoteMapRef.current,
        startOffset
      );
    }

    let lastTs: number | null = null;

    const tick = (ts?: number) => {
      let t: number;

      if (hasAudio) {
        t = audioState.getPlaybackTime();
      } else {
        // No audio files: drive clock via rAF timestamps
        const now = ts ?? 0;
        const delta = lastTs !== null ? (now - lastTs) / 1000 : 0;
        lastTs = now;
        t = Math.min(renderStateRef.current.currentTime + delta, duration);
      }

      renderStateRef.current.currentTime = t;
      uiState.setCurrentTime(t);

      if (t >= duration) {
        uiState.setPlaying(false);
        audioState.pause();
        drumSynthRef.current?.stopAll();
        return;
      }
      clockFrameRef.current = requestAnimationFrame(tick);
    };
    clockFrameRef.current = requestAnimationFrame(tick);

    return () => {
      if (clockFrameRef.current) cancelAnimationFrame(clockFrameRef.current);
      if (hasAudio) audioState.pause();
      drumSynthRef.current?.stopAll();
    };
  }, [uiState.isPlaying]);

  // Hot-swap audio sources and drum synth when toggles change mid-playback
  useEffect(() => {
    if (!uiState.isPlaying) return;

    const { songTracks: enableSong, drumTracks: enableDrum, noteSounds: enableNoteSounds } = uiState.playbackToggles;
    const currentTime = renderStateRef.current.currentTime;
    const hasAudio = audioState.songAudioBuffers.length > 0 || audioState.drumAudioBuffers.length > 0;

    // Re-start audio sources from current position with updated toggle flags
    if (hasAudio) {
      audioState.play(currentTime, enableSong, enableDrum);
    }

    // Re-schedule drum synth from current position
    drumSynthRef.current?.stopAll();
    const ctx = audioState.audioContext;
    if (enableNoteSounds && ctx) {
      if (ctx.state === 'suspended') ctx.resume();
      drumSynthRef.current = new DrumSynth(ctx);
      drumSynthRef.current.scheduleAll(
        mappedNotesRef.current,
        mappedNoteMapRef.current,
        currentTime
      );
    } else {
      drumSynthRef.current = null;
    }
  }, [uiState.playbackToggles]);

  if (!midiState.parsed) {
    return (
      <div className="relative w-full h-[400px] bg-slate-900 rounded-lg overflow-hidden">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          Upload a MIDI file to see visualization
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-[400px] bg-slate-900 rounded-lg overflow-hidden">
      <canvas ref={canvasRef} className="block w-full h-full cursor-default" />
    </div>
  );
}
