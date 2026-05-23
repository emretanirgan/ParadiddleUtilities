import { useState, useMemo } from 'react';
import { useMidiStore } from '../stores/midi-store';
import { useMappingStore } from '../stores/mapping-store';
import { useAudioStore } from '../stores/audio-store';
import { useUIStore } from '../stores/ui-store';
import { useConversionStore } from '../stores/conversion-store';
import { FileUploader } from './FileUploader';
import { MetadataForm } from './MetadataForm';
import { DifficultySelector } from './DifficultySelector';
import { VisualizationCanvas } from './VisualizationCanvas';
import { AudioPlayerControls } from './AudioPlayerControls';
import { MappingEditor } from './MappingEditor';
import { DrumKitVisualizer } from './DrumKitVisualizer';
import { DrumKitVisualizerThree } from './DrumKitVisualizerThree';
import { MappingProcessor } from '../core/mapping-processor';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
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
  const [showDrumKitVisualizerThree, setShowDrumKitVisualizerThree] = useState(true);

  const midiStore = useMidiStore();
  const mappingStore = useMappingStore();
  const audioStore = useAudioStore();
  const uiStore = useUIStore();
  const conversionStore = useConversionStore();

  const canConvert = !!midiStore.parsed && !!conversionStore.metadata.title;

  const noteStats = useMemo(() => {
    if (!midiStore.parsed || !mappingStore.mapping) return null;

    const track = midiStore.parsed.tracks[midiStore.selectedTrackIndex];
    if (!track) return null;

    const totalMidiNotes = track.notes.length;
    const processor = new MappingProcessor();
    const { noteToInstrument } = processor.createNoteMaps(mappingStore.mapping);
    const difficultyIndex = ['easy', 'medium', 'hard', 'expert'].indexOf(mappingStore.difficulty);
    const noteMap = noteToInstrument[difficultyIndex] || new Map();

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
      <div className="max-w-[900px] mx-auto">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-4 mb-2">
            <img src="/assets/PDLogo_Circle-300x300.png" alt="Paradiddle" className="w-16 h-16" />
            <h1 className="text-5xl font-futura-heavy text-primary">Paradiddle MIDI Converter</h1>
          </div>
          <p className="text-muted-foreground text-sm text-left max-w-2xl mx-auto">Convert MIDI files to Paradiddle's RLRR song format! This web tool is still new. If you run into any issues or have suggestions, reach out on <a href="https://discord.gg/paradiddle" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">Discord</a> or at <a href="mailto:hello@paradiddleapp.com" className="underline hover:text-foreground">hello@paradiddleapp.com</a>.</p>
        </div>

        {midiStore.parsed && (
          <Card className="mb-8">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle>Preview</CardTitle>
              <div className="flex gap-1">
                <Button
                  variant={uiStore.viewMode === 'mapped' ? 'default' : 'secondary'}
                  size="sm"
                  onClick={() => uiStore.setViewMode('mapped')}
                >
                  Mapped Notes
                </Button>
                <Button
                  variant={uiStore.viewMode === 'raw' ? 'default' : 'secondary'}
                  size="sm"
                  onClick={() => uiStore.setViewMode('raw')}
                >
                  Raw MIDI
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <VisualizationCanvas />
              <AudioPlayerControls />
            </CardContent>
          </Card>
        )}

        <Card className="mb-8">
          <CardContent className="pt-6">
            <Tabs defaultValue="metadata">
              <TabsList className="w-full mb-2">
                <TabsTrigger value="metadata" className="flex-1">1. Metadata</TabsTrigger>
                <TabsTrigger value="audio" className="flex-1">2. Audio</TabsTrigger>
                <TabsTrigger value="drumset" className="flex-1">3. Drum Set</TabsTrigger>
                <TabsTrigger value="midi" className="flex-1">4. MIDI</TabsTrigger>
                <TabsTrigger value="convert" className="flex-1">5. Convert</TabsTrigger>
              </TabsList>

              {/* Tab 1 - Metadata */}
              <TabsContent value="metadata">
                <MetadataForm />
                <FileUploader
                  label="Cover Image"
                  accept={{ 'image/*': ['.png', '.jpg', '.jpeg'] }}
                  onFilesSelected={(files) => files[0] && audioStore.setCoverImage(files[0])}
                  currentFiles={audioStore.coverImage ? [audioStore.coverImage] : []}
                  onRemoveFile={() => audioStore.setCoverImage(null)}
                  description="Optional: Album/song artwork"
                />
              </TabsContent>

              {/* Tab 2 - Audio Files */}
              <TabsContent value="audio">
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
              </TabsContent>

              {/* Tab 3 - Drum Set */}
              <TabsContent value="drumset">
                <div className="flex gap-2 mb-3">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="flex-1"
                    onClick={() => mappingStore.useDefaultDrumSet()}
                  >
                    Use Default
                  </Button>
                  {/* <Button
                    variant={showDrumKitVisualizer ? 'default' : 'secondary'}
                    size="sm"
                    className="flex-1"
                    disabled={!mappingStore.drumSet}
                    onClick={() => setShowDrumKitVisualizer(!showDrumKitVisualizer)}
                  >
                    {showDrumKitVisualizer ? 'Hide Zdog' : 'View Zdog'}
                  </Button> */}
                  <Button
                    variant={showDrumKitVisualizerThree ? 'default' : 'secondary'}
                    size="sm"
                    className="flex-1"
                    disabled={!mappingStore.drumSet}
                    onClick={() => setShowDrumKitVisualizerThree(!showDrumKitVisualizerThree)}
                  >
                    {showDrumKitVisualizerThree ? 'Hide Kit Visual' : 'Show Kit Visual'}
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
                {mappingStore.drumSet && (
                  <div className="bg-blue-950/50 border border-blue-800/50 p-3 rounded-md mt-2 text-blue-300 text-sm">
                    Drum set loaded: {mappingStore.drumSetFile?.name || 'Default'} ({mappingStore.drumSet.instruments.length} instruments)
                  </div>
                )}
                {showDrumKitVisualizer && mappingStore.drumSet && (
                  <DrumKitVisualizer onClose={() => setShowDrumKitVisualizer(false)} />
                )}
                {showDrumKitVisualizerThree && mappingStore.drumSet && (
                  <DrumKitVisualizerThree onClose={() => setShowDrumKitVisualizerThree(false)} />
                )}
              </TabsContent>

              {/* Tab 4 - MIDI */}
              <TabsContent value="midi">
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
                          'mb-1',
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
                  <h3 className="text-base text-foreground mb-2">MIDI Mapping</h3>
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
              </TabsContent>

              {/* Tab 5 - Convert */}
              <TabsContent value="convert">
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
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
