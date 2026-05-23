import { useMidiStore } from '../stores/midi-store';
import { useUIStore } from '../stores/ui-store';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { cn } from '@/lib/utils';

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

export function AudioPlayerControls() {
  const midiState = useMidiStore();
  const uiState = useUIStore();

  const duration = midiState.parsed?.duration || 0;

  const handlePlayPause = () => {
    uiState.togglePlayback();
  };

  const handleStop = () => {
    uiState.setPlaying(false);
    uiState.setCurrentTime(0);
  };

  const handleSeek = (value: number[]) => {
    uiState.setCurrentTime(value[0]);
  };

  const handleZoomIn = () => {
    uiState.setZoom(Math.min(10, uiState.zoom + 0.5));
  };

  const handleZoomOut = () => {
    uiState.setZoom(Math.max(0.1, uiState.zoom - 0.5));
  };

  const handleZoomReset = () => {
    uiState.setZoom(1.0);
    uiState.setScrollOffset(0);
  };

  return (
    <div className="border rounded-lg p-4 mt-4 bg-card">
      <div className="flex items-center gap-4 mb-4">
        <Button size="sm" onClick={handlePlayPause}>
          {uiState.isPlaying ? '⏸ Pause' : '▶ Play'}
        </Button>
        <Button size="sm" variant="secondary" onClick={handleStop}>
          ⏹ Stop
        </Button>

        <span className="font-mono text-sm text-foreground min-w-[120px]">
          {formatTime(uiState.currentTime)} / {formatTime(duration)}
        </span>

        <Slider
          className="flex-1"
          min={0}
          max={duration || 1}
          step={0.01}
          value={[uiState.currentTime]}
          onValueChange={handleSeek}
        />
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground min-w-[60px]">
          Zoom: {uiState.zoom.toFixed(1)}x
        </span>
        <Button size="sm" variant="outline" onClick={handleZoomOut}>-</Button>
        <Button size="sm" variant="outline" onClick={handleZoomIn}>+</Button>
        <Button size="sm" variant="outline" onClick={handleZoomReset}>Reset</Button>
      </div>

      <div className="flex items-center gap-2 mt-3 pt-3 border-t">
        <span className="text-xs text-muted-foreground mr-2">Play:</span>
        {([
          ['songTracks', 'Song Tracks'],
          ['drumTracks', 'Drum Tracks'],
          ['noteSounds', 'Note Sounds'],
        ] as const).map(([key, label]) => (
          <Button
            key={key}
            size="sm"
            variant={uiState.playbackToggles[key] ? 'default' : 'outline'}
            className={cn('text-xs px-3 h-7', !uiState.playbackToggles[key] && 'text-muted-foreground')}
            onClick={() => uiState.togglePlaybackTrack(key)}
          >
            {label}
          </Button>
        ))}
      </div>
    </div>
  );
}
