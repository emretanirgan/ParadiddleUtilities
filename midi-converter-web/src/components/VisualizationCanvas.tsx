import { useEffect, useRef } from 'react';
import { useMidiStore } from '../stores/midi-store';
import { useMappingStore } from '../stores/mapping-store';
import { useUIStore } from '../stores/ui-store';
import { PianoRollRenderer, DRUM_COLORS, type InstrumentLane } from '../visualization/piano-roll-renderer';
import { ZoomPanController } from '../visualization/zoom-pan-controller';
import { MappingProcessor } from '../core/mapping-processor';

export function VisualizationCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<PianoRollRenderer | null>(null);
  const controllerRef = useRef<ZoomPanController | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const midiState = useMidiStore();
  const mappingState = useMappingStore();
  const uiState = useUIStore();

  // Initialize renderer and controller
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !midiState.parsed) {
      return;
    }

    const container = canvas.parentElement;
    if (!container) {
      return;
    }

    const width = container.clientWidth;
    const height = container.clientHeight;

    // Create renderer
    rendererRef.current = new PianoRollRenderer(canvas, {
      width,
      height,
      zoom: uiState.zoom,
      scrollOffset: uiState.scrollOffset,
      currentTime: uiState.currentTime,
      duration: midiState.parsed.duration,
    });

    // Create controller
    controllerRef.current = new ZoomPanController(canvas, {
      onZoomChange: (zoom) => {
        uiState.setZoom(zoom);
      },
      onScrollChange: (offset) => {
        uiState.setScrollOffset(offset);
      },
      onSeek: (x) => {
        if (rendererRef.current) {
          const time = rendererRef.current.timeFromX(x);
          uiState.setCurrentTime(time);
        }
      },
    });

    // Cleanup
    return () => {
      if (controllerRef.current) {
        controllerRef.current.detach();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [midiState.parsed]);

  // Update controller state when UI state changes
  useEffect(() => {
    if (controllerRef.current) {
      controllerRef.current.setZoom(uiState.zoom);
      controllerRef.current.setScrollOffset(uiState.scrollOffset);
    }
  }, [uiState.zoom, uiState.scrollOffset]);

  // Render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const renderer = rendererRef.current;

    if (!canvas || !renderer || !midiState.parsed || !mappingState.mapping || !mappingState.drumSet) {
      return;
    }

    // Get selected track
    const track = midiState.parsed.tracks[midiState.selectedTrackIndex];
    if (!track) {
      return;
    }

    // Create note maps
    const processor = new MappingProcessor();
    const { noteToInstrument } = processor.createNoteMaps(mappingState.mapping);
    const difficultyIndex = ['easy', 'medium', 'hard', 'expert'].indexOf(mappingState.difficulty);
    const noteMap = MappingProcessor.getNoteMapsForDifficulty(noteToInstrument, difficultyIndex);

    // Create instrument lanes from drum set
    const lanes: InstrumentLane[] = mappingState.drumSet.instruments.map((instrument) => {
      // Extract drum name from instrument name (e.g., "BP_Kick_C" -> "Kick")
      const drumName = instrument.name.replace('BP_', '').replace('_C', '');
      return {
        name: drumName,
        color: DRUM_COLORS[drumName] || '#64c8ff',
        drumClass: instrument.name,
      };
    });

    // Render function
    const render = () => {
      renderer.updateConfig({
        zoom: uiState.zoom,
        scrollOffset: uiState.scrollOffset,
        currentTime: uiState.currentTime,
      });

      renderer.render(track.notes, lanes, noteMap);

      // Continue animation loop
      animationFrameRef.current = requestAnimationFrame(render);
    };

    // Start render loop
    render();

    // Cleanup
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [
    midiState.parsed,
    midiState.selectedTrackIndex,
    mappingState.mapping,
    mappingState.drumSet,
    mappingState.difficulty,
    uiState.zoom,
    uiState.scrollOffset,
    uiState.currentTime,
  ]);

  // Show empty state if no MIDI loaded
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
