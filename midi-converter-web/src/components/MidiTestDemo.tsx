import { useMidiStore } from '../stores/midi-store';

const styles = {
  container: { minHeight: '100vh', backgroundColor: '#0f172a', padding: '2rem', color: '#f1f5f9' },
  maxWidth: { maxWidth: '1200px', margin: '0 auto' },
  header: { textAlign: 'center' as const, marginBottom: '2rem' },
  title: { fontSize: '2.5rem', fontWeight: 'bold', color: '#60a5fa', marginBottom: '0.5rem' },
  subtitle: { color: '#94a3b8' },
  uploadBox: { border: '2px dashed #475569', borderRadius: '0.5rem', padding: '2rem', textAlign: 'center' as const, backgroundColor: '#1e293b', marginBottom: '1.5rem' },
  input: { width: '100%', padding: '0.5rem' },
  card: { backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.5rem', padding: '1.5rem', marginBottom: '1.5rem' },
  cardTitle: { fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem', color: '#f1f5f9' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' },
  label: { fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem' },
  value: { fontWeight: '600', color: '#f1f5f9' },
  scrollBox: { maxHeight: '200px', overflowY: 'auto' as const, marginTop: '0.75rem' },
  tempoEvent: { backgroundColor: '#334155', padding: '0.75rem', borderRadius: '0.25rem', marginBottom: '0.5rem', fontFamily: 'monospace', fontSize: '0.875rem' },
  trackCard: { padding: '1rem', borderRadius: '0.5rem', border: '1px solid #334155', marginBottom: '0.5rem', backgroundColor: '#1e293b' },
  trackCardDefault: { padding: '1rem', borderRadius: '0.5rem', border: '2px solid #3b82f6', marginBottom: '0.5rem', backgroundColor: '#1e3a5f' },
  badge: { display: 'inline-block', marginLeft: '0.5rem', fontSize: '0.75rem', backgroundColor: '#3b82f6', color: '#fff', padding: '0.25rem 0.5rem', borderRadius: '0.25rem' },
  trackHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  trackTitle: { fontWeight: '600', color: '#f1f5f9' },
  trackSubtitle: { fontSize: '0.875rem', color: '#94a3b8' },
  noteCount: { fontSize: '1.5rem', fontWeight: 'bold', color: '#3b82f6' },
  noteCountLabel: { fontSize: '0.75rem', color: '#94a3b8' },
  loading: { backgroundColor: '#334155', padding: '1rem', borderRadius: '0.5rem', textAlign: 'center' as const, color: '#94a3b8' },
  error: { backgroundColor: '#7f1d1d', border: '1px solid #991b1b', color: '#fecaca', padding: '1rem', borderRadius: '0.5rem' },
  instructions: { backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem', color: '#94a3b8' },
};

export function MidiTestDemo() {
  const { file, parsed, isLoading, error, loadMidiFile } = useMidiStore();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      await loadMidiFile(selectedFile);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.maxWidth}>
        <div style={styles.header}>
          <h1 style={styles.title}>MIDI Parser Demo 🎹</h1>
          <p style={styles.subtitle}>Phase 2 Test - Upload a MIDI file to see parsed data</p>
        </div>

        <div style={styles.uploadBox}>
          <input
            type="file"
            accept=".mid,.midi"
            onChange={handleFileChange}
            style={styles.input}
          />
        </div>

        {isLoading && (
          <div style={styles.loading}>
            <p>Parsing MIDI file...</p>
          </div>
        )}

        {error && (
          <div style={styles.error}>
            <p style={{ fontWeight: 'bold' }}>Error:</p>
            <p>{error}</p>
          </div>
        )}

        {parsed && (
          <div>
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>✅ MIDI Parsed Successfully</h2>
              <div style={styles.grid}>
                <div>
                  <p style={styles.label}>File Name</p>
                  <p style={styles.value}>{file?.name}</p>
                </div>
                <div>
                  <p style={styles.label}>Duration</p>
                  <p style={styles.value}>{parsed.duration.toFixed(2)}s</p>
                </div>
                <div>
                  <p style={styles.label}>Ticks Per Beat</p>
                  <p style={styles.value}>{parsed.ticksPerBeat}</p>
                </div>
                <div>
                  <p style={styles.label}>Number of Tracks</p>
                  <p style={styles.value}>{parsed.tracks.length}</p>
                </div>
              </div>
            </div>

            <div style={styles.card}>
              <h3 style={styles.cardTitle}>Tempo Events ({parsed.tempoEvents.length})</h3>
              <div style={styles.scrollBox}>
                {parsed.tempoEvents.map((event, idx) => (
                  <div key={idx} style={styles.tempoEvent}>
                    <span style={{ color: '#60a5fa' }}>BPM:</span> {event.bpm.toFixed(1)}
                    {' | '}
                    <span style={{ color: '#60a5fa' }}>Time:</span> {event.time.toFixed(2)}s
                    {' | '}
                    <span style={{ color: '#60a5fa' }}>Tick:</span> {event.tick}
                  </div>
                ))}
              </div>
            </div>

            <div style={styles.card}>
              <h3 style={styles.cardTitle}>Tracks</h3>
              <div style={styles.scrollBox}>
                {parsed.tracks.map((track, idx) => (
                  <div
                    key={idx}
                    style={idx === parsed.defaultTrackIndex ? styles.trackCardDefault : styles.trackCard}
                  >
                    <div style={styles.trackHeader}>
                      <div>
                        <p style={styles.trackTitle}>
                          {track.name}
                          {idx === parsed.defaultTrackIndex && (
                            <span style={styles.badge}>DEFAULT</span>
                          )}
                        </p>
                        <p style={styles.trackSubtitle}>Track {idx + 1}</p>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <p style={styles.noteCount}>{track.notes.length}</p>
                        <p style={styles.noteCountLabel}>notes</p>
                      </div>
                    </div>
                    {track.notes.length > 0 && (
                      <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid #334155' }}>
                        <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          First note: MIDI {track.notes[0].note} at {track.notes[0].time.toFixed(2)}s
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <details style={styles.card}>
              <summary style={{ ...styles.cardTitle, cursor: 'pointer' }}>
                Raw JSON Data (Click to expand)
              </summary>
              <pre style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#0f172a', borderRadius: '0.25rem', fontSize: '0.75rem', overflowX: 'auto' }}>
                {JSON.stringify(parsed, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {!parsed && !isLoading && !error && (
          <div style={styles.instructions}>
            <h3 style={{ fontWeight: '600', color: '#f1f5f9', marginBottom: '0.5rem' }}>Instructions:</h3>
            <ol style={{ paddingLeft: '1.5rem', marginBottom: '1rem' }}>
              <li>Click the file input above to select a MIDI file</li>
              <li>The parser will extract tracks, notes, and tempo events</li>
              <li>View the parsed data displayed below</li>
              <li>Check the browser console for detailed logs</li>
            </ol>
            <p style={{ fontSize: '0.875rem', marginTop: '1rem' }}>
              💡 Try a MIDI file from your desktop app's test files!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
