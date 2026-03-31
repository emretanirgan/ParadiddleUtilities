import { useState, useMemo } from 'react';
import { useMidiStore } from '../stores/midi-store';
import { useMappingStore } from '../stores/mapping-store';
import { useAudioStore } from '../stores/audio-store';
import { useConversionStore } from '../stores/conversion-store';
import { FileUploader } from './FileUploader';
import { MetadataForm } from './MetadataForm';
import { DifficultySelector } from './DifficultySelector';
import { VisualizationCanvas } from './VisualizationCanvas';
import { AudioPlayerControls } from './AudioPlayerControls';
import { MappingEditor } from './MappingEditor';
import { DrumKitVisualizer } from './DrumKitVisualizer';
import { MappingProcessor } from '../core/mapping-processor';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

export function ConverterPage() {
  const [showMappingEditor, setShowMappingEditor] = useState(false);
  const [showDrumKitVisualizer, setShowDrumKitVisualizer] = useState(false);

  const midiStore = useMidiStore();
  const mappingStore = useMappingStore();
  const audioStore = useAudioStore();
  const conversionStore = useConversionStore();

  const canConvert = !!midiStore.parsed && !!conversionStore.metadata.title;

  // Calculate note counts for conversion preview
  const noteStats = useMemo(() => {
    if (!midiStore.parsed || !mappingStore.mapping) {
      return null;
    }

    const track = midiStore.parsed.tracks[midiStore.selectedTrackIndex];
    if (!track) return null;

    const totalMidiNotes = track.notes.length;

    // Get the note map for the selected difficulty
    const processor = new MappingProcessor();
    const { noteToInstrument } = processor.createNoteMaps(mappingStore.mapping);
    const difficultyIndex = ['easy', 'medium', 'hard', 'expert'].indexOf(mappingStore.difficulty);
    const noteMap = noteToInstrument[difficultyIndex] || new Map();

    // Count how many MIDI notes have mappings
    let mappedNotes = 0;
    const unmappedNoteNumbers = new Set<number>();

    for (const note of track.notes) {
      if (noteMap.has(note.note)) {
        mappedNotes++;
      } else {
        unmappedNoteNumbers.add(note.note);
      }
    }

    return {
      totalMidiNotes,
      mappedNotes,
      unmappedCount: totalMidiNotes - mappedNotes,
      unmappedNoteNumbers: Array.from(unmappedNoteNumbers).sort((a, b) => a - b),
    };
  }, [midiStore.parsed, midiStore.selectedTrackIndex, mappingStore.mapping, mappingStore.difficulty]);

  return (
    <div className="min-h-screen bg-background p-8 text-foreground">
      <div className="max-w-[1400px] mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-primary mb-2">Paradiddle MIDI Converter</h1>
          <p className="text-muted-foreground text-lg">Convert MIDI files to Paradiddle RLRR format</p>
        </div>

        {/* Visualization Section */}
        {midiStore.parsed && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <VisualizationCanvas />
              <AudioPlayerControls />
            </CardContent>
          </Card>
        )}

        <div className="space-y-8 mb-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Panel 1 - Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>1. Metadata</CardTitle>
            </CardHeader>
            <CardContent>
              <MetadataForm />
              <FileUploader
                label="Cover Image"
                accept={{ 'image/*': ['.png', '.jpg', '.jpeg'] }}
                onFilesSelected={(files) => files[0] && audioStore.setCoverImage(files[0])}
                currentFiles={audioStore.coverImage ? [audioStore.coverImage] : []}
                onRemoveFile={() => audioStore.setCoverImage(null)}
                description="Optional: Album/song artwork"
              />
            </CardContent>
          </Card>

          {/* Panel 2 - Audio Files */}
          <Card>
            <CardHeader>
              <CardTitle>2. Audio Files</CardTitle>
            </CardHeader>
            <CardContent>
              <FileUploader
                label="Song Audio Tracks"
                accept={{ 'audio/*': ['.mp3', '.wav', '.ogg'] }}
                maxFiles={5}
                onFilesSelected={(files) => files.forEach((f) => audioStore.addSongTrack(f))}
                currentFiles={audioStore.songTracks}
                onRemoveFile={(index) => audioStore.removeSongTrack(index)}
                description="Optional: Up to 5 backing tracks"
              />
              <FileUploader
                label="Drum Audio Tracks"
                accept={{ 'audio/*': ['.mp3', '.wav', '.ogg'] }}
                maxFiles={4}
                onFilesSelected={(files) => files.forEach((f) => audioStore.addDrumTrack(f))}
                currentFiles={audioStore.drumTracks}
                onRemoveFile={(index) => audioStore.removeDrumTrack(index)}
                description="Optional: Up to 4 drum tracks"
              />
              <FileUploader
                label="Song Preview"
                accept={{ 'audio/*': ['.mp3', '.wav', '.ogg'] }}
                onFilesSelected={(files) => files[0] && audioStore.setSongPreview(files[0])}
                currentFiles={audioStore.songPreview ? [audioStore.songPreview] : []}
                onRemoveFile={() => audioStore.setSongPreview(null)}
                description="Optional: Short audio clip for song selection menu"
              />
            </CardContent>
          </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Panel 3 - Drum Set */}
          <Card>
            <CardHeader>
              <CardTitle>3. Drum Set</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-3">
                <Button
                  variant="secondary"
                  size="sm"
                  className="flex-1"
                  onClick={() => mappingStore.useDefaultDrumSet()}
                >
                  Use Default
                </Button>
                <Button
                  variant={showDrumKitVisualizer ? 'default' : 'secondary'}
                  size="sm"
                  className="flex-1"
                  disabled={!mappingStore.drumSet}
                  onClick={() => setShowDrumKitVisualizer(!showDrumKitVisualizer)}
                >
                  {showDrumKitVisualizer ? 'Hide 3D' : 'View 3D'}
                </Button>
              </div>
              <FileUploader
                label=""
                accept={{ 'application/json': ['.json', '.rlrr'] }}
                onFilesSelected={(files) => files[0] && mappingStore.loadDrumSet(files[0])}
                currentFiles={mappingStore.drumSetFile ? [mappingStore.drumSetFile] : []}
                onRemoveFile={() => mappingStore.useDefaultDrumSet()}
                description="Optional: Upload custom drum set JSON"
              />
              {mappingStore.drumSet && !showDrumKitVisualizer && (
                <div className="bg-blue-950/50 border border-blue-800/50 p-3 rounded-md mt-2 text-blue-300 text-sm">
                  Drum set loaded: {mappingStore.drumSetFile?.name || 'Default'} ({mappingStore.drumSet.instruments.length} instruments)
                </div>
              )}
              {showDrumKitVisualizer && mappingStore.drumSet && (
                <DrumKitVisualizer onClose={() => setShowDrumKitVisualizer(false)} />
              )}
            </CardContent>
          </Card>

          {/* Panel 4 - MIDI */}
          <Card>
            <CardHeader>
              <CardTitle>4. MIDI</CardTitle>
            </CardHeader>
            <CardContent>
              <FileUploader
                label="MIDI File"
                accept={{ 'audio/midi': ['.mid', '.midi'] }}
                onFilesSelected={(files) => files[0] && midiStore.loadMidiFile(files[0])}
                currentFiles={midiStore.file ? [midiStore.file] : []}
                description="Required: Your MIDI drum track"
              />

              {midiStore.parsed && (
                <>
                  <div className="bg-blue-950/50 border border-blue-800/50 p-3 rounded-md mb-4 text-blue-300 text-sm">
                    MIDI loaded: {midiStore.parsed.tracks.length} tracks, {midiStore.parsed.duration.toFixed(1)}s
                  </div>
                  {midiStore.parsed.tracks.length > 1 && (
                    <div className="mb-4">
                      <Label className="mb-2">Select Track</Label>
                      <Select
                        value={String(midiStore.selectedTrackIndex)}
                        onValueChange={(value) => midiStore.selectTrack(Number(value))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {midiStore.parsed.tracks.map((track, idx) => (
                            <SelectItem key={idx} value={String(idx)}>
                              {track.name || `Track ${idx + 1}`} ({track.notes.length} notes)
                              {idx === midiStore.parsed!.defaultTrackIndex ? ' * Auto-detected' : ''}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                  {noteStats && (
                    <div className={cn(
                      'p-3 rounded-md mb-4 text-sm',
                      noteStats.unmappedCount > 0
                        ? 'bg-amber-950/50 border border-amber-800/50'
                        : 'bg-emerald-950/50 border border-emerald-800/50'
                    )}>
                      <div className={cn(
                        'font-bold mb-1',
                        noteStats.unmappedCount > 0 ? 'text-amber-300' : 'text-emerald-300'
                      )}>
                        Conversion Preview
                      </div>
                      <div className="text-slate-200">
                        {noteStats.mappedNotes} of {noteStats.totalMidiNotes} MIDI notes will be converted
                      </div>
                      {noteStats.unmappedCount > 0 && (
                        <div className="text-amber-300 mt-2 text-xs">
                          {noteStats.unmappedCount} unmapped notes (MIDI: {noteStats.unmappedNoteNumbers.slice(0, 5).join(', ')}
                          {noteStats.unmappedNoteNumbers.length > 5 ? `, +${noteStats.unmappedNoteNumbers.length - 5} more` : ''})
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              <DifficultySelector />

              <div className="mt-6">
                <h3 className="text-base font-bold text-foreground mb-2">MIDI Mapping</h3>
                <div className="flex gap-2 mb-3">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="flex-1"
                    onClick={() => mappingStore.useDefaultMapping()}
                  >
                    Use Default
                  </Button>
                  <Button
                    variant={showMappingEditor ? 'default' : 'secondary'}
                    size="sm"
                    className="flex-1"
                    disabled={!mappingStore.mapping}
                    onClick={() => setShowMappingEditor(!showMappingEditor)}
                  >
                    {showMappingEditor ? 'Hide Editor' : 'Edit Mapping'}
                  </Button>
                </div>
                <FileUploader
                  label=""
                  accept={{ 'text/yaml': ['.yaml', '.yml'] }}
                  onFilesSelected={(files) => files[0] && mappingStore.loadMapping(files[0])}
                  currentFiles={mappingStore.mappingFile ? [mappingStore.mappingFile] : []}
                  onRemoveFile={() => mappingStore.useDefaultMapping()}
                  description="Optional: Upload custom MIDI mapping YAML"
                />
                {mappingStore.mapping && !showMappingEditor && (
                  <div className="bg-blue-950/50 border border-blue-800/50 p-3 rounded-md mt-2 text-blue-300 text-sm">
                    Mapping loaded: {mappingStore.mappingFile?.name || 'Default'}
                  </div>
                )}
                {showMappingEditor && mappingStore.mapping && (
                  <MappingEditor onClose={() => setShowMappingEditor(false)} />
                )}
              </div>
            </CardContent>
          </Card>
          </div>

          {/* Panel 5 - Convert */}
          <Card>
            <CardHeader>
              <CardTitle>5. Convert</CardTitle>
            </CardHeader>
            <CardContent>
              {conversionStore.error && (
                <div className="bg-red-950/50 border border-red-800/50 p-3 rounded-md mb-4 text-red-300 text-sm">
                  <strong>Error:</strong> {conversionStore.error}
                </div>
              )}

              {conversionStore.result && (
                <div className="bg-emerald-950/50 border border-emerald-800/50 p-3 rounded-md mb-4 text-emerald-300 text-sm">
                  <strong>Conversion successful!</strong>
                  <div className="grid grid-cols-2 gap-1 mt-2 text-muted-foreground">
                    <div>Events: {conversionStore.result.events.length}</div>
                    <div>Instruments: {conversionStore.result.instruments.length}</div>
                    <div>BPM Events: {conversionStore.result.bpmEvents.length}</div>
                    <div>Duration: {conversionStore.result.recordingMetadata.length.toFixed(1)}s</div>
                  </div>
                </div>
              )}

              <Button
                className="w-full mb-3"
                size="lg"
                onClick={() => conversionStore.convert()}
                disabled={!canConvert || conversionStore.isConverting}
              >
                {conversionStore.isConverting ? 'Converting...' : 'Convert to RLRR'}
              </Button>

              {!canConvert && (
                <div className="bg-blue-950/50 border border-blue-800/50 p-3 rounded-md mb-3 text-blue-300 text-sm">
                  {!midiStore.parsed && 'Upload a MIDI file'}
                  {midiStore.parsed && !conversionStore.metadata.title && 'Enter a song title'}
                </div>
              )}

              {conversionStore.result && (
                <div className="space-y-2">
                  <Button
                    className="w-full"
                    variant="secondary"
                    size="lg"
                    onClick={() => conversionStore.downloadRLRR()}
                  >
                    Download ZIP Package
                  </Button>

                  <Button
                    className="w-full"
                    variant="outline"
                    size="lg"
                    onClick={() => conversionStore.downloadJSON()}
                  >
                    Download RLRR JSON Only
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
