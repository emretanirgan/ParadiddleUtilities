from PyQt5.QtGui import QIcon, QPainter, QPen, QColor
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QScrollBar
from PyQt5.QtCore import Qt, QTimer
import os
import mido
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time

project_dir = os.path.dirname(os.path.realpath(__file__))

class DrumSamplePlayer:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.samples = {}
        self.load_default_samples()
        
    def load_default_samples(self):
        """Load default drum samples from the drum_samples directory"""
        samples_dir = os.path.join(project_dir, "drum_samples")
        print(f"Loading drum samples from: {samples_dir}")
        
        # Default sample mappings with fallbacks
        sample_files = {
            'kick': 'kick.wav',
            'snare': 'snare.wav',
            'hihat': 'hihat.wav',
            'crash15': 'crash.wav',
            'crash17': 'crash.wav',
            'tom1': 'tom1.wav',
            'tom2': 'tom2.wav',
            'floortom': 'floortom.wav',
            'ride17': 'ride.wav',
            'ride20': 'ride.wav',
        }
        
        for drum_type, filename in sample_files.items():
            sample_path = os.path.join(samples_dir, filename)
            if os.path.exists(sample_path):
                try:
                    audio_data, sr = sf.read(sample_path)
                    # Convert to mono if stereo
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    # Resample if necessary
                    if sr != self.sample_rate:
                        # Simple resampling (for more accurate resampling, use scipy.signal.resample)
                        audio_data = np.interp(
                            np.linspace(0, len(audio_data), int(len(audio_data) * self.sample_rate / sr)),
                            np.arange(len(audio_data)),
                            audio_data
                        )
                    # Normalize the sample to prevent clipping
                    if len(audio_data) > 0:
                        max_val = np.max(np.abs(audio_data))
                        if max_val > 0:
                            audio_data = audio_data / max_val * 0.8  # Scale to 80% to prevent clipping
                    
                    self.samples[drum_type] = audio_data
                    print(f"✓ Loaded {drum_type} sample: {len(audio_data)} samples at {sr}Hz")
                except Exception as e:
                    print(f"✗ Could not load drum sample {sample_path}: {e}")
            else:
                print(f"✗ Sample file not found: {sample_path}")
                
        print(f"Total samples loaded: {len(self.samples)}")
        
        # Ensure we have at least basic samples
        if len(self.samples) == 0:
            print("⚠️ No drum samples loaded! Creating silent fallbacks.")
            # Create silent samples as absolute fallback
            silent_sample = np.zeros(int(self.sample_rate * 0.1))  # 100ms of silence
            for drum_type in sample_files.keys():
                self.samples[drum_type] = silent_sample
        
    def get_sample(self, drum_type):
        """Get the audio sample for a specific drum type"""
        return self.samples.get(drum_type, None)
        
    def load_custom_sample(self, drum_type, file_path):
        """Load a custom sample for a specific drum type"""
        try:
            audio_data, sr = sf.read(file_path)
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            # Resample if necessary
            if sr != self.sample_rate:
                audio_data = np.interp(
                    np.linspace(0, len(audio_data), int(len(audio_data) * self.sample_rate / sr)),
                    np.arange(len(audio_data)),
                    audio_data
                )
            self.samples[drum_type] = audio_data
            return True
        except Exception as e:
            print(f"Could not load custom sample {file_path}: {e}")
            return False

class SongDisplay_GUI(QtWidgets.QDockWidget):
    def __init__(self, midi_converter=None):
        super(SongDisplay_GUI, self).__init__()
        
        self.setWindowIcon(QIcon(os.path.join(project_dir, "assets", "favicon.ico")))
        uic.loadUi(os.path.join(project_dir, "ui_layouts", "song_display_layout.ui"), self)
        
        # Set initial window title
        self.setWindowTitle("Song Display - No Song Loaded")
        
        # Initialize variables
        self.midi_converter = midi_converter
        self.midi_file = None
        self.midi_data = None
        self.mapped_midi_data = None  # Store mapped drum events
        self.audio_data = None
        self.sample_rate = 44100  # Default sample rate
        self.is_playing = False
        self.current_position = 0
        self.playback_thread = None
        self.stop_playback = False
        self.drum_sample_player = DrumSamplePlayer()
        self.show_mapped_view = True  # Default to showing mapped drum events
        
        # Audio tracks from MIDI converter
        self.song_tracks = []  # List of song track audio data
        self.drum_tracks = []  # List of drum track audio data
        self.track_sample_rates = []  # Sample rates for each track
        
        # Song metadata
        self.song_name = "Unknown Song"
        self.artist_name = "Unknown Artist"
        
        # Zoom and scroll variables
        self.zoom_factor = 1.0
        self.scroll_offset = 0.0
        self.label_width = 100  # Width reserved for instrument labels
        
        # Mouse tracking for drag functionality
        self.is_dragging = False
        self.last_mouse_x = 0
        
        # Audio toggle variables
        self.drum_sounds_enabled = True
        self.audio_track_enabled = True
        self.instrument_sounds_enabled = True
        
        # Volume control for realtime mixing
        self._realtime_audio_lock = threading.Lock()
        self._realtime_volume_multipliers = {
            'drums': 1.0,
            'audio': 1.0,
            'instruments': 1.0
        }
        
        # Instrument row mapping for proper spacing
        self.instrument_rows = {}
        self.row_height = 25
        self.total_rows = 0
        
        # Connect UI signals
        self.playStateButton.clicked.connect(self._playState_changed)
        self.curSongPosSlider.valueChanged.connect(self._curSongPos_changed)
        
        # Set up radio button group for view mode
        from PyQt5.QtWidgets import QButtonGroup
        self.viewModeButtonGroup = QButtonGroup()
        self.viewModeButtonGroup.addButton(self.mappedViewRadio)
        self.viewModeButtonGroup.addButton(self.rawMidiViewRadio)
        
        self.mappedViewRadio.toggled.connect(self._view_mode_changed)
        self.rawMidiViewRadio.toggled.connect(self._view_mode_changed)
        self.zoomSlider.valueChanged.connect(self._zoom_changed)
        self.horizontalScrollBar.valueChanged.connect(self._scroll_changed)
        self.drumSoundsToggle.clicked.connect(self._toggle_drum_sounds)
        self.audioTrackToggle.clicked.connect(self._toggle_audio_track)
        self.instrumentSoundsToggle.clicked.connect(self._toggle_instrument_sounds)
        
        # Set up timer for updating position
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_position)
        self.update_timer.start(50)  # Update every 50ms
        
        # Set up MIDI visualization
        self.setMinimumHeight(400)  # Ensure enough space for visualization
        
        # Initialize zoom label
        self.zoomLabel.setText(f"Zoom: {int(self.zoom_factor * 100)}%")
        
        # Set up initial control positions (anchored to bottom)
        self._update_control_positions()
        
        # Waveform visualization
        self.combined_audio = None
        self.waveform_data = None
        self.waveform_height = 60  # Height reserved for waveform display
        self.show_waveform = True
        
    def _playState_changed(self):
        if not self.midi_file:
            return
            
        if self.is_playing:
            self.stop_playback = True
            if self.playback_thread:
                self.playback_thread.join()
            self.playStateButton.setText("Play")
            self.is_playing = False
        else:
            self.stop_playback = False
            self.playback_thread = threading.Thread(target=self._playback_loop)
            self.playback_thread.start()
            self.playStateButton.setText("Pause")
            self.is_playing = True
            
    def _curSongPos_changed(self):
        if not self.midi_file:
            return
            
        # Choose data source based on toggle state
        if self.show_mapped_view and self.mapped_midi_data:
            display_data = self.mapped_midi_data
        elif self.midi_data:
            display_data = self.midi_data
        else:
            return
            
        # Convert slider value (0-100) to actual position
        if self.audio_data is not None:
            self.current_position = (self.curSongPosSlider.value() / 100.0) * len(self.audio_data)
        elif display_data:
            # For MIDI-only playback, use time-based position
            if self.sample_rate is None:
                self.sample_rate = 44100  # Default sample rate
            self.current_position = (self.curSongPosSlider.value() / 100.0) * display_data['duration'] * self.sample_rate
        self.update()  # Trigger repaint
        
    def _update_position(self):
        if self.audio_data is not None:
            position_percent = (self.current_position / len(self.audio_data)) * 100
        elif self.midi_data:
            # For MIDI-only playback - ensure sample_rate is set
            if self.sample_rate is None:
                self.sample_rate = 44100  # Default sample rate
            time_position = self.current_position / self.sample_rate
            position_percent = (time_position / self.midi_data['duration']) * 100
        else:
            position_percent = 0
            
        self.curSongPosSlider.setValue(int(position_percent))
        
        # Update time display with consistent timing
        if self.midi_data or self.audio_data:
            if self.audio_data is not None:
                # Use direct time calculation for better sync
                current_time = self.current_position / self.sample_rate
            else:
                if self.sample_rate is None:
                    self.sample_rate = 44100
                current_time = self.current_position / self.sample_rate
                
            total_time = self.midi_data['duration'] if self.midi_data else 0
            time_text = f"{self._format_time(current_time)} / {self._format_time(total_time)}"
            self.timeLabel.setText(time_text)
            
        # Trigger repaint for smooth visual updates
        self.update()
        
    def _playback_loop(self):
        if not self.sample_rate:
            self.sample_rate = 44100  # Default sample rate
            
        # Choose data source based on toggle state
        if self.show_mapped_view and self.mapped_midi_data:
            display_data = self.mapped_midi_data
            drum_data_source = self.mapped_midi_data  # Use mapped data for drum generation
        elif self.midi_data:
            display_data = self.midi_data
            drum_data_source = self.midi_file  # Use raw MIDI for drum generation
        else:
            display_data = None
            drum_data_source = None
            
        # Start from current position instead of beginning
        if self.audio_data is not None:
            start_time = self.current_position / self.sample_rate
            start_sample = int(self.current_position)
        else:
            start_time = self.current_position / self.sample_rate
            start_sample = 0
            
        # For audio playback, use continuous streaming
        if self.audio_data is not None:
            # Calculate the remaining audio data to play
            remaining_audio = self.audio_data[start_sample:]
            
            if len(remaining_audio) > 0:
                # Pre-mix individual track data for realtime processing
                song_tracks_mixed = []
                drum_tracks_mixed = []
                midi_drum_track = None
                
                # Prepare song tracks
                for i, track in enumerate(self.song_tracks):
                    if track is not None and len(track) > start_sample:
                        track_remaining = track[start_sample:]
                        if len(track_remaining) < len(remaining_audio):
                            padded_track = np.zeros(len(remaining_audio))
                            padded_track[:len(track_remaining)] = track_remaining
                            song_tracks_mixed.append(padded_track * 0.6)
                        else:
                            song_tracks_mixed.append(track_remaining[:len(remaining_audio)] * 0.6)
                
                # Prepare drum tracks
                for i, track in enumerate(self.drum_tracks):
                    if track is not None and len(track) > start_sample:
                        track_remaining = track[start_sample:]
                        if len(track_remaining) < len(remaining_audio):
                            padded_track = np.zeros(len(remaining_audio))
                            padded_track[:len(track_remaining)] = track_remaining
                            drum_tracks_mixed.append(padded_track * 0.8)
                        else:
                            drum_tracks_mixed.append(track_remaining[:len(remaining_audio)] * 0.8)
                
                # Prepare MIDI drum track for instrument sounds (always generate if available)
                if drum_data_source:
                    midi_drum_track = self._generate_full_drum_track(start_time, len(remaining_audio), drum_data_source) * 0.8
                
                # Track current frame position for the callback
                current_frame = [0]  # Use list to allow modification in callback
                
                # Play with realtime mixing in callback
                def audio_callback(outdata, frames, time, status):
                    if self.stop_playback:
                        raise sd.CallbackStop()
                    
                    # Calculate the range of frames to play
                    start_frame = current_frame[0]
                    end_frame = start_frame + frames
                    
                    if start_frame < len(remaining_audio):
                        # Get the chunk size for this callback
                        chunk_end = min(end_frame, len(remaining_audio))
                        chunk_size = chunk_end - start_frame
                        
                        # Start with silence
                        mixed_chunk = np.zeros(chunk_size)
                        
                        # Get current volume settings (thread-safe)
                        with self._realtime_audio_lock:
                            audio_volume = self._realtime_volume_multipliers['audio']
                            drum_volume = self._realtime_volume_multipliers['drums']
                            instr_volume = self._realtime_volume_multipliers['instruments']
                        
                        # Mix song tracks with current volume
                        if audio_volume > 0.0:
                            for song_track in song_tracks_mixed:
                                mixed_chunk += song_track[start_frame:chunk_end] * audio_volume
                        
                        # Mix drum tracks with current volume
                        if drum_volume > 0.0:
                            for drum_track in drum_tracks_mixed:
                                mixed_chunk += drum_track[start_frame:chunk_end] * drum_volume
                        
                        # Mix MIDI-generated instrument sounds with Instr toggle
                        if instr_volume > 0.0 and midi_drum_track is not None:
                            # Ensure we don't exceed MIDI track bounds
                            midi_start = min(start_frame, len(midi_drum_track))
                            midi_end = min(chunk_end, len(midi_drum_track))
                            if midi_start < midi_end:
                                # Only mix available MIDI data
                                midi_chunk = midi_drum_track[midi_start:midi_end]
                                # Pad mixed_chunk if MIDI chunk is shorter
                                if len(midi_chunk) < len(mixed_chunk):
                                    mixed_chunk[:len(midi_chunk)] += midi_chunk * instr_volume
                                else:
                                    mixed_chunk += midi_chunk[:len(mixed_chunk)] * instr_volume
                        
                        # Update current position for the UI (absolute position)
                        self.current_position = start_sample + chunk_end
                        
                        # Apply gentle normalization only if needed to prevent distortion
                        max_val = np.max(np.abs(mixed_chunk))
                        if max_val > 1.0:  # Only normalize if clipping would occur
                            mixed_chunk = mixed_chunk / max_val * 0.95
                        else:
                            # Apply gentle limiting to prevent any potential clipping
                            mixed_chunk = np.clip(mixed_chunk, -0.98, 0.98)
                        
                        # Fill output buffer
                        if len(mixed_chunk) < frames:
                            # Pad with zeros if we've reached the end
                            if outdata.ndim == 1:  # Mono output
                                outdata[:len(mixed_chunk)] = mixed_chunk
                                outdata[len(mixed_chunk):] = 0
                            else:  # Stereo output
                                outdata[:len(mixed_chunk), :] = mixed_chunk.reshape(-1, 1)
                                outdata[len(mixed_chunk):, :] = 0
                            # Update frame counter and stop
                            current_frame[0] = len(remaining_audio)
                            raise sd.CallbackStop()
                        else:
                            if outdata.ndim == 1:  # Mono output
                                outdata[:] = mixed_chunk
                            else:  # Stereo output
                                outdata[:, :] = mixed_chunk.reshape(-1, 1)
                            
                        # Update frame counter
                        current_frame[0] = chunk_end
                    else:
                        # We've reached the end
                        outdata.fill(0)
                        raise sd.CallbackStop()
                
                try:
                    # Start the audio stream - auto-detect channels
                    with sd.OutputStream(samplerate=self.sample_rate, 
                                       callback=audio_callback, blocksize=1024):
                        # Keep the stream alive while playing
                        while not self.stop_playback and current_frame[0] < len(remaining_audio):
                            time.sleep(0.01)
                                
                except Exception as e:
                    print(f"Audio playback error: {e}")
                    
        else:
            # MIDI-only playback with drum sounds
            if drum_data_source and (self.drum_sounds_enabled or self.instrument_sounds_enabled):
                # Pre-generate the entire drum track for more reliable playback
                total_duration = display_data['duration'] if display_data else 60.0  # Default 60 seconds
                total_samples = int(total_duration * self.sample_rate)
                
                print(f"Pre-generating drum track for {total_duration:.2f} seconds ({total_samples} samples)")
                drum_track = self._generate_full_drum_track(start_time, total_samples, drum_data_source)
                
                # Track current frame position for the callback
                current_frame = [0]  # Use list to allow modification in callback
                
                # Play the drum track using continuous streaming with realtime volume
                def midi_audio_callback(outdata, frames, time, status):
                    if self.stop_playback:
                        raise sd.CallbackStop()
                    
                    # Calculate the range of frames to play
                    start_frame = current_frame[0]
                    end_frame = start_frame + frames
                    
                    if start_frame < len(drum_track):
                        # Get the audio chunk for this callback
                        chunk_end = min(end_frame, len(drum_track))
                        base_chunk = drum_track[start_frame:chunk_end]
                        
                        # Get current instrument volume (thread-safe) - MIDI drums controlled by Instr toggle
                        with self._realtime_audio_lock:
                            instr_volume = self._realtime_volume_multipliers['instruments']
                        
                        # Apply realtime volume
                        chunk = base_chunk * instr_volume
                        
                        # Update current position for the UI (absolute position)
                        # start_frame is relative to drum track, need to add initial start sample
                        initial_start_sample = int(start_time * self.sample_rate) if hasattr(self, 'sample_rate') else 0
                        self.current_position = initial_start_sample + chunk_end
                        
                        # Fill output buffer
                        if len(chunk) < frames:
                            # Pad with zeros if we've reached the end
                            if outdata.ndim == 1:  # Mono output
                                outdata[:len(chunk)] = chunk
                                outdata[len(chunk):] = 0
                            else:  # Stereo output
                                outdata[:len(chunk), :] = chunk.reshape(-1, 1)
                                outdata[len(chunk):, :] = 0
                            # Update frame counter and stop
                            current_frame[0] = len(drum_track)
                            raise sd.CallbackStop()
                        else:
                            if outdata.ndim == 1:  # Mono output
                                outdata[:] = chunk
                            else:  # Stereo output
                                outdata[:, :] = chunk.reshape(-1, 1)
                            
                        # Update frame counter
                        current_frame[0] = chunk_end
                    else:
                        # We've reached the end
                        outdata.fill(0)
                        raise sd.CallbackStop()
                
                try:
                    # Start the audio stream - auto-detect channels
                    with sd.OutputStream(samplerate=self.sample_rate, 
                                       callback=midi_audio_callback, blocksize=1024):
                        # Keep the stream alive while playing
                        while not self.stop_playback and current_frame[0] < len(drum_track):
                            time.sleep(0.01)
                                
                except Exception as e:
                    print(f"MIDI playback error: {e}")
        
        # Stop playback but don't reset position
        self.is_playing = False
        self.playStateButton.setText("Play")
        
    def _generate_drum_chunk(self, start_frame, chunk_size, data_source):
        """Generate drum sounds for a chunk of audio using mapped drum events"""
        if not self.drum_sample_player or not data_source:
            return np.zeros(chunk_size)
            
        drum_chunk = np.zeros(chunk_size)
        
        # Calculate time range for this chunk
        start_time = start_frame / self.sample_rate
        end_time = (start_frame + chunk_size) / self.sample_rate
        
        # Find mapped drum events in this time range
        events_in_chunk = []
        
        # Use mapped MIDI data if available, otherwise fall back to raw MIDI
        if isinstance(data_source, dict) and 'notes' in data_source and isinstance(data_source['notes'], list):
            # This is mapped MIDI data with drum classes
            for note in data_source['notes']:
                if start_time <= note['time'] < end_time:
                    events_in_chunk.append({
                        'time': note['time'],
                        'drum_class': note.get('drum_class'),
                        'velocity': note.get('velocity', 100),
                        'is_mapped': True
                    })
        elif hasattr(data_source, 'tracks'):
            # This is a raw MIDI file object
            events_in_chunk = self._process_raw_midi_events(data_source, start_time, end_time)
        else:
            # Invalid data source type
            print(f"Warning: Invalid data source type for drum generation: {type(data_source)}")
            return drum_chunk
        
        if events_in_chunk:
            print(f"Found {len(events_in_chunk)} drum events in time range {start_time:.2f}-{end_time:.2f}s")
            
            # Debug: Show all events
            for event in events_in_chunk:
                if event.get('is_mapped'):
                    print(f"  Mapped Event: drum_class={event['drum_class']}, velocity={event['velocity']}")
                else:
                    print(f"  Raw Event: note={event['note']}, channel={event['channel']}, velocity={event['velocity']}")
        
        # Generate drum sounds for each event
        for event in events_in_chunk:
            # Calculate frame position within chunk
            event_frame = int((event['time'] - start_time) * self.sample_rate)
            if 0 <= event_frame < chunk_size:
                drum_type = None
                
                if event.get('is_mapped') and event['drum_class']:
                    # Use mapped drum class
                    drum_type = self._map_drum_class_to_sample(event['drum_class'])
                    print(f"  Using mapped drum class: {event['drum_class']} -> {drum_type}")
                else:
                    # Fall back to raw MIDI note mapping
                    drum_type = self._get_drum_type_from_note(event['note'])
                    print(f"  Using raw MIDI note: {event['note']} -> {drum_type}")
                
                if drum_type:
                    sample = self.drum_sample_player.get_sample(drum_type)
                    if sample is not None and len(sample) > 0:
                        # Calculate velocity scaling (ensure minimum volume)
                        velocity_scale = max(0.3, event['velocity'] / 127.0)  # Minimum 30% volume
                        
                        # Add sample to chunk
                        end_frame = min(event_frame + len(sample), chunk_size)
                        sample_length = end_frame - event_frame
                        
                        # Use addition with clipping to prevent overflow
                        sample_data = sample[:sample_length] * velocity_scale
                        drum_chunk[event_frame:end_frame] = np.clip(
                            drum_chunk[event_frame:end_frame] + sample_data,
                            -1.0, 1.0
                        )
                        
                        if event.get('is_mapped'):
                            print(f"  Added {drum_type} drum at frame {event_frame} (drum_class {event['drum_class']}, velocity {event['velocity']}, vol={velocity_scale:.2f})")
                        else:
                            print(f"  Added {drum_type} drum at frame {event_frame} (note {event['note']}, channel {event['channel']}, velocity {event['velocity']}, vol={velocity_scale:.2f})")
                    else:
                        print(f"  No sample found for drum type: {drum_type}")
        
        return drum_chunk
        
    def _process_raw_midi_events(self, data_source, start_time, end_time):
        """Process raw MIDI events as fallback when mapped data is not available"""
        events_in_chunk = []
        
        # Process all tracks in the MIDI file
        for track in data_source.tracks:
            current_time = 0
            current_tempo = 500000  # Default tempo (120 BPM)
            
            for msg in track:
                # Update tempo if we encounter a tempo change
                if msg.type == 'set_tempo':
                    current_tempo = msg.tempo
                    
                # Convert MIDI ticks to seconds with current tempo
                current_time += mido.tick2second(msg.time, data_source.ticks_per_beat, current_tempo)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    if start_time <= current_time < end_time:
                        # Get channel, default to 9 if not specified
                        channel = getattr(msg, 'channel', 9)
                        events_in_chunk.append({
                            'time': current_time,
                            'note': msg.note,
                            'velocity': msg.velocity,
                            'channel': channel,
                            'is_mapped': False
                        })
        
        return events_in_chunk
        
    def _get_drum_type_from_note(self, midi_note):
        """Map MIDI note numbers to drum sounds using the actual MIDI mapping file"""
        if not self.midi_converter:
            return self._get_drum_type_from_note_fallback(midi_note)
            
        # Get the current difficulty and mapping
        difficulty = getattr(self.midi_converter, 'difficulty', 'Easy')
        diff_index = self.midi_converter.difficulty_names.index(difficulty)
        
        # Get the note mapping for current difficulty
        if diff_index < len(self.midi_converter.note_to_drum_maps):
            note_map = self.midi_converter.note_to_drum_maps[diff_index]
        else:
            return self._get_drum_type_from_note_fallback(midi_note)
            
        # Look up the MIDI note in the mapping
        if midi_note in note_map:
            # Get the first drum mapping for this note
            drum_mapping = note_map[midi_note][0] if note_map[midi_note] else None
            if drum_mapping and 'drum' in drum_mapping:
                drum_class = drum_mapping['drum']
                # Map drum class to sample type
                sample_type = self._map_drum_class_to_sample(drum_class)
                print(f"  MIDI note {midi_note} -> {drum_class} -> {sample_type} (using mapping)")
                return sample_type
                
        # If not found in mapping, use fallback
        return self._get_drum_type_from_note_fallback(midi_note)
        
    def _map_drum_class_to_sample(self, drum_class):
        """Map drum class from MIDI mapping to sample type"""
        # Map drum classes to available sample types
        class_to_sample = {
            'BP_Kick_C': 'kick',
            'BP_Snare_C': 'snare', 
            'BP_HiHat_C': 'hihat',
            'BP_Crash15_C': 'crash15',
            'BP_Crash17_C': 'crash17',
            'BP_FloorTom_C': 'floortom',
            'BP_Ride17_C': 'ride17',
            'BP_Ride20_C': 'ride20',
            'BP_Tom1_C': 'tom1',
            'BP_Tom2_C': 'tom2',
            'BP_China15_C': 'china15',
            'BP_Cowbell_C': 'hihat',  # Fallback to hihat for percussion
            'BP_Tambourine1_C': 'hihat',
            'BP_Tambourine2_C': 'hihat',
            'BP_Timpani1_C': 'tom',
            'BP_Timpani2_C': 'tom', 
            'BP_Timpani3_C': 'tom',
            'BP_Triangle_C': 'hihat',
            'BP_BongoH_C': 'tom',
            'BP_BongoL_C': 'tom',
            'BP_Xylophone_C': 'hihat',
            'BP_Marimba_C': 'hihat',
            'BP_Glockenspiel_C': 'hihat',
            'BP_Gong_C': 'crash',
        }
        
        return class_to_sample.get(drum_class, 'hihat')  # Default to hihat
        
    def _get_drum_type_from_note_fallback(self, midi_note):
        """Fallback to General MIDI mapping if no custom mapping is available"""
        # Standard GM drum mapping (Channel 10) - expanded for better coverage
        drum_mapping = {
            # Kick drums
            35: 'kick',    # Acoustic Bass Drum
            36: 'kick',    # Bass Drum 1
            
            # Snare drums
            38: 'snare',   # Acoustic Snare
            40: 'snare',   # Electric Snare
            37: 'snare',   # Side Stick
            39: 'snare',   # Hand Clap
            
            # Hi-hats
            42: 'hihat',   # Closed Hi Hat
            44: 'hihat',   # Pedal Hi-Hat
            46: 'hihat',   # Open Hi Hat
            
            # Toms
            41: 'tom',     # Low Floor Tom
            43: 'tom',     # High Floor Tom
            45: 'tom',     # Low Tom
            47: 'tom',     # Low-Mid Tom
            48: 'tom',     # Hi-Mid Tom
            50: 'tom',     # High Tom
            
            # Cymbals
            49: 'crash',   # Crash Cymbal 1
            51: 'ride',    # Ride Cymbal 1
            52: 'crash',   # Chinese Cymbal
            53: 'ride',    # Ride Bell
            55: 'crash',   # Splash Cymbal
            57: 'crash',   # Crash Cymbal 2
            59: 'ride',    # Ride Cymbal 2
            
            # Additional percussion
            54: 'hihat',   # Tambourine -> hihat
            56: 'tom',     # Cowbell -> tom
            58: 'tom',     # Vibraslap -> tom
            60: 'tom',     # Hi Bongo -> tom
            61: 'tom',     # Low Bongo -> tom
            62: 'tom',     # Mute Hi Conga -> tom
            63: 'tom',     # Open Hi Conga -> tom
            64: 'tom',     # Low Conga -> tom
            65: 'tom',     # High Timbale -> tom
            66: 'tom',     # Low Timbale -> tom
            67: 'tom',     # High Agogo -> tom
            68: 'tom',     # Low Agogo -> tom
            69: 'hihat',   # Cabasa -> hihat
            70: 'hihat',   # Maracas -> hihat
            71: 'hihat',   # Short Whistle -> hihat
            72: 'hihat',   # Long Whistle -> hihat
            73: 'hihat',   # Short Guiro -> hihat
            74: 'hihat',   # Long Guiro -> hihat
            75: 'hihat',   # Claves -> hihat
            76: 'tom',     # Hi Wood Block -> tom
            77: 'tom',     # Low Wood Block -> tom
            78: 'hihat',   # Mute Cuica -> hihat
            79: 'hihat',   # Open Cuica -> hihat
            80: 'hihat',   # Mute Triangle -> hihat
            81: 'hihat',   # Open Triangle -> hihat
        }
        
        # Get drum type with fallback logic
        drum_type = drum_mapping.get(midi_note)
        
        if drum_type is None:
            # Fallback logic based on note ranges
            if midi_note <= 40:
                drum_type = 'kick'  # Low notes -> kick
            elif midi_note <= 50:
                drum_type = 'snare'  # Mid-low notes -> snare
            elif midi_note <= 60:
                drum_type = 'tom'    # Mid notes -> tom
            elif midi_note <= 70:
                drum_type = 'crash'  # Mid-high notes -> crash
            else:
                drum_type = 'hihat'  # High notes -> hihat
                
            print(f"  Unmapped MIDI note {midi_note} -> fallback to {drum_type}")
        
        return drum_type
            
    def resizeEvent(self, event):
        """Handle window resize to keep controls anchored to bottom"""
        super().resizeEvent(event)
        self._update_control_positions()
    
    def _update_control_positions(self):
        """Update control positions to anchor them to the bottom of the window"""
        if not hasattr(self, 'playStateButton'):
            return
            
        # Get current window dimensions
        window_width = self.width()
        window_height = self.height()
        
        # Define control heights and margins
        bottom_margin = 20
        control_spacing = 30
        button_height = 25
        slider_height = 20
        time_height = 41
        play_button_height = 41
        
        # Calculate positions from bottom
        play_button_y = window_height - bottom_margin - play_button_height
        time_label_y = play_button_y
        view_button_y = play_button_y
        
        slider_y = play_button_y - control_spacing - slider_height
        toggle_y = slider_y - control_spacing - button_height
        zoom_controls_y = toggle_y - control_spacing - slider_height
        
        # Update control positions
        try:
            # Play controls row
            self.playStateButton.setGeometry(146, play_button_y, 71, play_button_height)
            self.timeLabel.setGeometry(225, time_label_y, 116, time_height)
            self.viewModeWidget.setGeometry(20, view_button_y, 120, play_button_height)
            
            # Position slider
            self.curSongPosSlider.setGeometry(20, slider_y, window_width - 40, slider_height)
            
            # Toggle buttons row
            self.drumSoundsToggle.setGeometry(20, toggle_y, 85, button_height)
            self.audioTrackToggle.setGeometry(110, toggle_y, 85, button_height)
            self.instrumentSoundsToggle.setGeometry(200, toggle_y, 110, button_height)
            
            # Zoom controls row
            self.zoomSlider.setGeometry(20, zoom_controls_y, 75, slider_height)
            self.zoomLabel.setGeometry(105, zoom_controls_y, 80, slider_height)
            self.horizontalScrollBar.setGeometry(190, zoom_controls_y, window_width - 210, slider_height)
            
        except AttributeError:
            # Controls not yet initialized
            pass
    
    def paintEvent(self, event):
        if not self.midi_file:
            return
            
        # Choose data source based on toggle state
        if self.show_mapped_view and self.mapped_midi_data:
            display_data = self.mapped_midi_data
        elif self.midi_data:
            display_data = self.midi_data
        else:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set up colors and pens
        background_color = QColor(40, 40, 40)
        label_bg_color = QColor(30, 30, 30)
        grid_color = QColor(60, 60, 60)
        text_color = QColor(200, 200, 200)
        current_time_color = QColor(255, 255, 255)
        
        # Fill background
        painter.fillRect(self.rect(), background_color)
        
        # Set up instrument rows
        self._setup_instrument_rows(display_data)
        
        # Calculate dimensions
        total_width = self.width()
        total_height = self.height() - 120  # Leave space for controls
        piano_roll_width = total_width - self.label_width
        
        # Reserve space for waveform if enabled
        waveform_offset = 0
        if self.show_waveform and self.waveform_data is not None:
            waveform_offset = self.waveform_height + 10  # Extra padding
            total_height -= waveform_offset
        
        # Avoid division by zero
        if display_data['duration'] <= 0:
            return
            
        # Calculate time scale with zoom and scroll
        time_scale = (piano_roll_width * self.zoom_factor) / display_data['duration']
        
        # Draw label background
        painter.fillRect(0, 0, self.label_width, total_height, label_bg_color)
        
        # Draw horizontal grid lines and instrument labels
        painter.setPen(QPen(grid_color, 1))
        painter.setFont(painter.font())
        
        if self.total_rows > 0:
            for instrument, row_index in self.instrument_rows.items():
                y = row_index * self.row_height + waveform_offset
                if y < total_height + waveform_offset:
                    # Draw grid line
                    painter.drawLine(self.label_width, y, total_width, y)
                    
                    # Draw instrument label
                    painter.setPen(QPen(text_color, 1))
                    label_rect = painter.boundingRect(5, y, self.label_width - 10, self.row_height, 
                                                    Qt.AlignLeft | Qt.AlignVCenter, 
                                                    self._get_instrument_label(instrument))
                    painter.drawText(5, y + 5, self.label_width - 10, self.row_height - 10, 
                                   Qt.AlignLeft | Qt.AlignVCenter, 
                                   self._get_instrument_label(instrument))
                    painter.setPen(QPen(grid_color, 1))
        
        # Set clipping region for piano roll area
        painter.setClipRect(self.label_width, 0, piano_roll_width, total_height)
        
        # Draw waveform if available
        if self.show_waveform and self.waveform_data is not None:
            self._draw_waveform(painter, piano_roll_width, time_scale, display_data['duration'])
        
        # Draw notes
        for note in display_data['notes']:
            # Calculate note position with zoom and scroll
            note_start_time = note['time'] - self.scroll_offset
            x = self.label_width + int(note_start_time * time_scale)
            w = max(2, int(note['duration'] * time_scale))  # Ensure minimum width of 2 pixels
            
            # Skip notes that are outside the visible area
            if x + w < self.label_width or x > total_width:
                continue
                
            # Get instrument row
            if self.show_mapped_view and 'drum_class' in note:
                instrument_key = note['drum_class']
            else:
                instrument_key = note['note']
                
            if instrument_key not in self.instrument_rows:
                continue
                
            row_index = self.instrument_rows[instrument_key]
            y = row_index * self.row_height + waveform_offset + 2  # Small padding + waveform offset
            h = self.row_height - 4  # Leave some space between rows
            
            # Skip notes that are outside the visible height
            if y > total_height + waveform_offset:
                continue
            
            # Use different colors for different drum types in mapped view
            if self.show_mapped_view and 'drum_class' in note:
                drum_class = note['drum_class']
                if 'Kick' in drum_class:
                    note_color = QColor(255, 100, 100)  # Red for kick
                elif 'Snare' in drum_class:
                    note_color = QColor(255, 255, 100)  # Yellow for snare
                elif 'HiHat' in drum_class:
                    note_color = QColor(100, 255, 100)  # Green for hi-hat
                elif 'Crash' in drum_class or 'China' in drum_class:
                    note_color = QColor(255, 150, 0)    # Orange for crashes
                elif 'Ride' in drum_class:
                    note_color = QColor(150, 100, 255)  # Purple for ride
                elif 'Tom' in drum_class or 'FloorTom' in drum_class:
                    note_color = QColor(100, 200, 255)  # Light blue for toms
                else:
                    note_color = QColor(200, 200, 200)  # Gray for other drums
            else:
                note_color = QColor(0, 255, 0)  # Green for raw MIDI
            
            # Draw note rectangle
            painter.fillRect(x, y, w, h, note_color)
            
        # Reset clipping
        painter.setClipping(False)
        
        # Draw current time indicator with consistent timing
        if display_data:
            # Use direct time calculation for accurate sync
            if self.sample_rate is None:
                self.sample_rate = 44100  # Default sample rate
            current_time = self.current_position / self.sample_rate
                
            # Calculate current time position with zoom and scroll
            current_time_pos = current_time - self.scroll_offset
            x = self.label_width + int(current_time_pos * time_scale)
            
            # Only draw if within visible area
            if self.label_width <= x <= total_width:
                painter.setPen(QPen(current_time_color, 2))
                # Draw line from top of display (including waveform) to bottom of notes
                painter.drawLine(x, 0, x, total_height + waveform_offset)
                
        # Update scroll range
        self._update_scroll_range()
        
        # Update time display with consistent timing
        if display_data:
            # Use direct time calculation for accurate sync
            if self.sample_rate is None:
                self.sample_rate = 44100
            current_time = self.current_position / self.sample_rate
                
            total_time = display_data['duration']
            time_text = f"{self._format_time(current_time)} / {self._format_time(total_time)}"
            self.timeLabel.setText(time_text)

    def _update_window_title(self):
        """Update the window title with current song information"""
        if self.song_name and self.song_name != "Unknown Song":
            title = f"Song Display - {self.song_name}"
            if self.artist_name and self.artist_name != "Unknown Artist":
                title += f" by {self.artist_name}"
        else:
            title = "Song Display - No Song Loaded"
        self.setWindowTitle(title)
        
    def change_midi(self, song_path):
        if not song_path:
            return
            
        self.midi_file = mido.MidiFile(song_path)
        self.midi_data = self._process_midi_data()
        self.mapped_midi_data = self._process_mapped_midi_data()
        
        # Extract song name from file path
        self.song_name = os.path.splitext(os.path.basename(song_path))[0]
        
        # Try to get artist name from MIDI converter if available
        if self.midi_converter:
            self.artist_name = getattr(self.midi_converter, 'artist_name', 'Unknown Artist')
        
        # Update window title
        self._update_window_title()
        
        # Load audio tracks and generate waveform
        self.load_audio_tracks_from_converter()
        
        self.update()
        
    def change_midi_map(self, midi_map_path):
        # Reload mapped data when mapping changes
        if self.midi_file:
            self.mapped_midi_data = self._process_mapped_midi_data()
            self.update()
        
    def change_drumset(self, drumset_path):
        # TODO: Implement drum set changes
        pass
        
    def change_midi_track(self, midi_track):
        if not self.midi_file:
            return
            
        self.midi_data = self._process_midi_data(track_index=midi_track)
        self.mapped_midi_data = self._process_mapped_midi_data(track_index=midi_track)
        self.update()
        
    def _process_midi_data(self, track_index=None):
        if not self.midi_file:
            return None
            
        notes = []
        active_notes = {}  # Track active notes and their start times
        
        # Process all tracks or specific track
        tracks_to_process = [self.midi_file.tracks[track_index]] if track_index is not None else self.midi_file.tracks
        
        for track in tracks_to_process:
            current_time = 0
            current_tempo = 500000  # Default tempo (120 BPM)
            for msg in track:
                # Update tempo if we encounter a tempo change
                if msg.type == 'set_tempo':
                    current_tempo = msg.tempo
                    
                # Convert MIDI ticks to seconds with current tempo
                current_time += mido.tick2second(msg.time, self.midi_file.ticks_per_beat, current_tempo)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    active_notes[msg.note] = current_time
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        start_time = active_notes[msg.note]
                        duration = current_time - start_time
                        notes.append({
                            'note': msg.note,
                            'time': start_time,
                            'duration': max(0.01, duration),  # Ensure minimum duration
                            'velocity': msg.velocity
                        })
                        del active_notes[msg.note]
                        
        # Handle any remaining active notes
        for note, start_time in active_notes.items():
            notes.append({
                'note': note,
                'time': start_time,
                'duration': 0.1,  # Default duration for notes that don't have note_off
                'velocity': 64
            })
                        
        return {
            'notes': notes,
            'duration': max(self.midi_file.length, max([n['time'] + n['duration'] for n in notes]) if notes else 0)
        }
        
    def set_audio_data(self, audio_path):
        if not audio_path:
            return
            
        try:
            self.audio_data, self.sample_rate = sf.read(audio_path)
            # Convert to mono if stereo
            if len(self.audio_data.shape) > 1:
                self.audio_data = np.mean(self.audio_data, axis=1)
        except Exception as e:
            print(f"Error loading audio file: {e}")
            self.audio_data = None
            self.sample_rate = None

    def _view_mode_changed(self):
        """Handle view mode change from radio buttons"""
        # Update the show_mapped_view state based on which radio button is checked
        self.show_mapped_view = self.mappedViewRadio.isChecked()
        
        self.update()  # Trigger repaint

    def _get_tempo_map(self, midi_file):
        """Extract tempo changes from MIDI file for accurate timing"""
        tempo_changes = []
        current_time = 0
        current_tempo = 500000  # Default tempo (120 BPM)
        
        # Scan all tracks for tempo changes
        for track in midi_file.tracks:
            track_time = 0
            track_tempo = 500000
            
            for msg in track:
                if msg.type == 'set_tempo':
                    track_tempo = msg.tempo
                    tempo_changes.append({
                        'time': track_time,
                        'tempo': track_tempo
                    })
                
                # Convert MIDI ticks to seconds with current tempo
                track_time += mido.tick2second(msg.time, midi_file.ticks_per_beat, track_tempo)
        
        # Sort by time and return
        tempo_changes.sort(key=lambda x: x['time'])
        if not tempo_changes:
            tempo_changes = [{'time': 0, 'tempo': 500000}]  # Default if no tempo found
            
        return tempo_changes
    
    def _get_tempo_at_time(self, tempo_map, time):
        """Get the tempo that should be active at a given time"""
        active_tempo = 500000  # Default
        
        for tempo_change in tempo_map:
            if tempo_change['time'] <= time:
                active_tempo = tempo_change['tempo']
            else:
                break
                
        return active_tempo
    
    def _process_mapped_midi_data(self, track_index=None):
        """Process MIDI data through the mapping system to get drum events"""
        if not self.midi_file or not self.midi_converter:
            return None
            
        # Get the current difficulty and mapping
        difficulty = getattr(self.midi_converter, 'difficulty', 'Easy')
        diff_index = self.midi_converter.difficulty_names.index(difficulty)
        
        # Get the note mapping for current difficulty
        if diff_index < len(self.midi_converter.note_to_drum_maps):
            note_map = self.midi_converter.note_to_drum_maps[diff_index]
            toggle_map = self.midi_converter.toggle_to_drum_maps[diff_index] if diff_index < len(self.midi_converter.toggle_to_drum_maps) else {}
        else:
            return None
            
        mapped_notes = []
        active_notes = {}
        active_toggles = []
        
        # Process the selected track or all tracks
        tracks_to_process = [self.midi_file.tracks[track_index]] if track_index is not None else self.midi_file.tracks
        
        for track in tracks_to_process:
            current_time = 0
            current_tempo = 500000  # Default tempo (120 BPM)
            for msg in track:
                # Update tempo if we encounter a tempo change
                if msg.type == 'set_tempo':
                    current_tempo = msg.tempo
                    
                # Convert MIDI ticks to seconds with current tempo
                current_time += mido.tick2second(msg.time, self.midi_file.ticks_per_beat, current_tempo)
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    note = msg.note
                    
                    # Handle toggle notes
                    if note in toggle_map:
                        if note not in active_toggles:
                            active_toggles.append(note)
                    
                    # Handle mapped drum notes
                    if note in note_map:
                        for drum_mapping in note_map[note]:
                            drum_class = drum_mapping['drum']
                            
                            # Check if this drum requires a toggle
                            toggle_required = False
                            for toggle_note, toggle_drum in toggle_map.items():
                                if toggle_drum == drum_class:
                                    toggle_required = True
                                    if toggle_note in active_toggles:
                                        # Create mapped note with drum class info
                                        mapped_note = {
                                            'note': self._get_drum_display_note(drum_class),
                                            'time': current_time,
                                            'duration': 0.1,  # Will be updated on note_off
                                            'velocity': msg.velocity,
                                            'drum_class': drum_class,
                                            'original_note': note
                                        }
                                        active_notes[f"{note}_{drum_class}"] = mapped_note
                                    break
                            
                            if not toggle_required:
                                # Create mapped note without toggle requirement
                                mapped_note = {
                                    'note': self._get_drum_display_note(drum_class),
                                    'time': current_time,
                                    'duration': 0.1,  # Will be updated on note_off
                                    'velocity': msg.velocity,
                                    'drum_class': drum_class,
                                    'original_note': note
                                }
                                active_notes[f"{note}_{drum_class}"] = mapped_note
                                
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    note = msg.note
                    
                    # Handle toggle note off
                    if note in toggle_map and note in active_toggles:
                        active_toggles.remove(note)
                    
                    # Handle mapped drum note off
                    if note in note_map:
                        for drum_mapping in note_map[note]:
                            drum_class = drum_mapping['drum']
                            key = f"{note}_{drum_class}"
                            if key in active_notes:
                                mapped_note = active_notes[key]
                                mapped_note['duration'] = max(0.01, current_time - mapped_note['time'])
                                mapped_notes.append(mapped_note)
                                del active_notes[key]
        
        # Handle any remaining active notes
        for key, mapped_note in active_notes.items():
            mapped_note['duration'] = 0.1  # Default duration
            mapped_notes.append(mapped_note)
            
        return {
            'notes': mapped_notes,
            'duration': max(self.midi_file.length, max([n['time'] + n['duration'] for n in mapped_notes]) if mapped_notes else 0)
        }
    
    def _get_drum_display_note(self, drum_class):
        """Map drum class to a MIDI note number for display purposes"""
        # Map drum classes to specific note ranges for visual organization
        drum_note_mapping = {
            'BP_Kick_C': 36,
            'BP_Snare_C': 38,
            'BP_HiHat_C': 42,
            'BP_Crash15_C': 49,
            'BP_Crash17_C': 57,
            'BP_FloorTom_C': 41,
            'BP_Ride17_C': 51,
            'BP_Ride20_C': 59,
            'BP_Tom1_C': 48,
            'BP_Tom2_C': 47,
            'BP_China15_C': 52,
            'BP_Timpani1_C': 65,
            'BP_Timpani2_C': 66,
            'BP_Timpani3_C': 67,
            'BP_Triangle_C': 81,
            'BP_BongoH_C': 60,
            'BP_BongoL_C': 61,
            'BP_Xylophone_C': 85,
            'BP_Marimba_C': 86,
            'BP_Glockenspiel_C': 87,
            'BP_Gong_C': 88,
            'BP_Tambourine1_C': 54,
            'BP_Tambourine2_C': 55,
            'BP_Cowbell_C': 56,
        }
        return drum_note_mapping.get(drum_class, 60)  # Default to middle C

    def _zoom_changed(self, value):
        """Handle zoom slider changes"""
        self.zoom_factor = value / 100.0  # Convert to decimal (1.0 = 100%)
        self.zoomLabel.setText(f"Zoom: {value}%")
        self._update_scroll_range()
        self.update()  # Trigger repaint
        
    def _scroll_changed(self):
        """Handle horizontal scroll changes"""
        if self.horizontalScrollBar.maximum() > 0:
            scroll_percent = self.horizontalScrollBar.value() / self.horizontalScrollBar.maximum()
            # Choose data source based on toggle state
            if self.show_mapped_view and self.mapped_midi_data:
                display_data = self.mapped_midi_data
            elif self.midi_data:
                display_data = self.midi_data
            else:
                return
                
            if display_data:
                # Calculate scroll offset based on zoom level
                max_scroll_time = display_data['duration'] * (self.zoom_factor - 1.0) / self.zoom_factor
                self.scroll_offset = scroll_percent * max_scroll_time
                self.update()
                
    def _update_scroll_range(self):
        """Update the horizontal scroll bar range based on zoom level"""
        # Choose data source based on toggle state
        if self.show_mapped_view and self.mapped_midi_data:
            display_data = self.mapped_midi_data
        elif self.midi_data:
            display_data = self.midi_data
        else:
            return
            
        if display_data:
            # Calculate if content is wider than visible area due to zoom
            piano_roll_width = self.width() - self.label_width
            content_width = piano_roll_width * self.zoom_factor
            
            # Show scroll bar if zoomed in beyond 100%
            if self.zoom_factor > 1.0:
                # Calculate the maximum scroll range
                max_scroll_time = display_data['duration'] * (self.zoom_factor - 1.0) / self.zoom_factor
                self.horizontalScrollBar.setMaximum(int(max_scroll_time * 100))  # Scale for precision
                self.horizontalScrollBar.setEnabled(True)
            else:
                self.horizontalScrollBar.setMaximum(0)
                self.horizontalScrollBar.setEnabled(False)
                
    def _setup_instrument_rows(self, display_data):
        """Set up instrument row mapping for proper spacing"""
        self.instrument_rows.clear()
        
        if not display_data or not display_data['notes']:
            return
            
        # Collect unique instruments/notes
        unique_instruments = set()
        
        if self.show_mapped_view:
            # Group by drum class for mapped view
            for note in display_data['notes']:
                if 'drum_class' in note:
                    unique_instruments.add(note['drum_class'])
                else:
                    unique_instruments.add(f"Note_{note['note']}")
        else:
            # Group by MIDI note for raw view
            for note in display_data['notes']:
                unique_instruments.add(note['note'])
                
        # Sort instruments for consistent ordering
        sorted_instruments = sorted(list(unique_instruments), key=lambda x: str(x))
        
        # Assign row numbers
        for i, instrument in enumerate(sorted_instruments):
            self.instrument_rows[instrument] = i
            
        self.total_rows = len(sorted_instruments)
        
    def _get_instrument_label(self, instrument_key):
        """Get display label for instrument"""
        if self.show_mapped_view and isinstance(instrument_key, str) and instrument_key.startswith('BP_'):
            # Map drum class to readable name
            label_mapping = {
                'BP_Kick_C': 'Kick',
                'BP_Snare_C': 'Snare',
                'BP_HiHat_C': 'Hi-Hat',
                'BP_Crash15_C': 'Crash 15"',
                'BP_Crash17_C': 'Crash 17"',
                'BP_FloorTom_C': 'Floor Tom',
                'BP_Ride17_C': 'Ride 17"',
                'BP_Ride20_C': 'Ride 20"',
                'BP_Tom1_C': 'Tom 1',
                'BP_Tom2_C': 'Tom 2',
                'BP_China15_C': 'China 15"',
                'BP_Cowbell_C': 'Cowbell',
                'BP_Tambourine1_C': 'Tambourine',
                'BP_Tambourine2_C': 'Tambourine 2',
            }
            return label_mapping.get(instrument_key, instrument_key.replace('BP_', '').replace('_C', ''))
        elif isinstance(instrument_key, int):
            # MIDI note number
            return f"Note {instrument_key}"
        else:
            return str(instrument_key)
            
    def _format_time(self, seconds):
        """Format time in MM:SS format"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def mousePressEvent(self, event):
        """Handle mouse clicks for seeking to different timeline positions"""
        if not self.midi_file:
            return
            
        # Choose data source based on toggle state
        if self.show_mapped_view and self.mapped_midi_data:
            display_data = self.mapped_midi_data
        elif self.midi_data:
            display_data = self.midi_data
        else:
            return
            
        # Check if click is in the piano roll area (not in the label area)
        if event.x() < self.label_width:
            return
            
        # Calculate dimensions
        total_width = self.width()
        total_height = self.height() - 120  # Leave space for controls
        piano_roll_width = total_width - self.label_width
        
        # Check if click is in the piano roll area (not in controls)
        if event.y() > total_height:
            return
            
        if display_data['duration'] <= 0:
            return
            
        # Start drag tracking
        self.is_dragging = True
        self.last_mouse_x = event.x()
        
        # Seek to clicked position
        self._seek_to_mouse_position(event.x(), display_data)
        
        # Call parent implementation for any other mouse handling
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse drag for live timeline scrubbing"""
        if self.is_dragging and self.midi_file:
            # Choose data source based on toggle state
            if self.show_mapped_view and self.mapped_midi_data:
                display_data = self.mapped_midi_data
            elif self.midi_data:
                display_data = self.midi_data
            else:
                return
                
            # Check if still in piano roll area
            if event.x() >= self.label_width and event.y() <= self.height() - 120:
                self._seek_to_mouse_position(event.x(), display_data)
                
        # Call parent implementation
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging"""
        self.is_dragging = False
        # Call parent implementation
        super().mouseReleaseEvent(event)
        
    def _seek_to_mouse_position(self, mouse_x, display_data):
        """Helper method to seek to a specific mouse position"""
        # Calculate dimensions
        total_width = self.width()
        piano_roll_width = total_width - self.label_width
        
        # Calculate time scale with zoom
        time_scale = (piano_roll_width * self.zoom_factor) / display_data['duration']
        
        # Calculate clicked time position
        click_x = mouse_x - self.label_width
        clicked_time = (click_x / time_scale) + self.scroll_offset
        
        # Clamp to valid time range
        clicked_time = max(0, min(clicked_time, display_data['duration']))
        
        # Update position based on data source
        if self.audio_data is not None:
            # For audio playback, convert time to sample position
            self.current_position = (clicked_time / display_data['duration']) * len(self.audio_data)
        else:
            # For MIDI-only playback, convert time to sample position
            if self.sample_rate is None:
                self.sample_rate = 44100
            self.current_position = clicked_time * self.sample_rate
            
        # Update slider position
        position_percent = (clicked_time / display_data['duration']) * 100
        self.curSongPosSlider.setValue(int(position_percent))
        
        # Trigger repaint to show new position
        self.update()

    def _generate_full_drum_track(self, start_time, total_samples, data_source):
        """Generate a complete drum track for the given duration"""
        drum_track = np.zeros(total_samples)
        
        if not self.drum_sample_player or not data_source:
            return drum_track
            
        # Calculate end time
        end_time = start_time + (total_samples / self.sample_rate)
        
        # Use mapped MIDI data if available, otherwise fall back to raw MIDI
        events_processed = 0
        if isinstance(data_source, dict) and 'notes' in data_source and isinstance(data_source['notes'], list):
            # This is mapped MIDI data with drum classes
            for note in data_source['notes']:
                if start_time <= note['time'] < end_time:
                    events_processed += 1
                    # Calculate frame position within track (relative to start_time)
                    relative_time = note['time'] - start_time
                    event_frame = int(relative_time * self.sample_rate)
                    
                    if 0 <= event_frame < total_samples:
                        # Get drum type from mapped drum class
                        drum_type = self._map_drum_class_to_sample(note.get('drum_class'))
                        if drum_type:
                            sample = self.drum_sample_player.get_sample(drum_type)
                            if sample is not None and len(sample) > 0:
                                # Calculate velocity scaling (ensure minimum volume)
                                velocity_scale = max(0.3, note.get('velocity', 100) / 127.0)  # Minimum 30% volume
                                
                                # Add sample to track
                                end_frame = min(event_frame + len(sample), total_samples)
                                sample_length = end_frame - event_frame
                                
                                # Use addition with clipping to prevent overflow
                                sample_data = sample[:sample_length] * velocity_scale
                                drum_track[event_frame:end_frame] = np.clip(
                                    drum_track[event_frame:end_frame] + sample_data,
                                    -1.0, 1.0
                                )
        elif hasattr(data_source, 'tracks'):
            # Fall back to raw MIDI processing
            # Process all tracks in the MIDI file
            for track in data_source.tracks:
                current_time = 0
                current_tempo = 500000  # Default tempo (120 BPM)
                
                for msg in track:
                    # Update tempo if we encounter a tempo change
                    if msg.type == 'set_tempo':
                        current_tempo = msg.tempo
                        
                    # Convert MIDI ticks to seconds with current tempo
                    current_time += mido.tick2second(msg.time, data_source.ticks_per_beat, current_tempo)
                    
                    if msg.type == 'note_on' and msg.velocity > 0:
                        # Only process drum channel (channel 9 in 0-based indexing)
                        if getattr(msg, 'channel', 9) != 9:
                            continue
                            
                        if start_time <= current_time < end_time:
                            # Calculate frame position (relative to start_time)
                            relative_time = current_time - start_time
                            event_frame = int(relative_time * self.sample_rate)
                            if 0 <= event_frame < total_samples:
                                # Get drum type from note
                                drum_type = self._get_drum_type_from_note(msg.note)
                                if drum_type:
                                    sample = self.drum_sample_player.get_sample(drum_type)
                                    if sample is not None and len(sample) > 0:
                                        # Calculate velocity scaling (ensure minimum volume)
                                        velocity_scale = max(0.3, msg.velocity / 127.0)  # Minimum 30% volume
                                        
                                        # Add sample to track
                                        end_frame = min(event_frame + len(sample), total_samples)
                                        sample_length = end_frame - event_frame
                                        
                                        # Use addition with clipping to prevent overflow
                                        sample_data = sample[:sample_length] * velocity_scale
                                        drum_track[event_frame:end_frame] = np.clip(
                                            drum_track[event_frame:end_frame] + sample_data,
                                            -1.0, 1.0
                                        )
        else:
            # Invalid data source type
            print(f"Warning: Invalid data source type for full drum track generation: {type(data_source)}")
                                
        return drum_track

    def closeEvent(self, event):
        """Handle window close event - stop playback and cleanup"""
        # Stop any ongoing playback
        if self.is_playing:
            self.stop_playback = True
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=1.0)  # Wait up to 1 second for thread to finish
            self.is_playing = False
            
        # Stop the update timer
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
            
        # Stop any active audio streams
        try:
            sd.stop()  # Stop all active sounddevice streams
        except Exception as e:
            print(f"Error stopping audio streams: {e}")
            
        # Accept the close event
        event.accept()
        
        # Call parent implementation
        super().closeEvent(event)

    def _toggle_drum_sounds(self):
        """Toggle drum sounds on/off"""
        self.drum_sounds_enabled = self.drumSoundsToggle.isChecked()
        with self._realtime_audio_lock:
            self._realtime_volume_multipliers['drums'] = 1.0 if self.drum_sounds_enabled else 0.0
        
        if self.drum_sounds_enabled:
            self.drumSoundsToggle.setText("Drums: ON")
        else:
            self.drumSoundsToggle.setText("Drums: OFF")
        
        print(f"Drum sounds toggled: {'ON' if self.drum_sounds_enabled else 'OFF'}")
            
    def _toggle_audio_track(self):
        """Toggle audio track on/off"""
        self.audio_track_enabled = self.audioTrackToggle.isChecked()
        with self._realtime_audio_lock:
            self._realtime_volume_multipliers['audio'] = 1.0 if self.audio_track_enabled else 0.0
        
        if self.audio_track_enabled:
            self.audioTrackToggle.setText("Audio: ON")
        else:
            self.audioTrackToggle.setText("Audio: OFF")
        
        print(f"Audio tracks toggled: {'ON' if self.audio_track_enabled else 'OFF'}")
            
    def _toggle_instrument_sounds(self):
        """Toggle instrument sounds on/off"""
        self.instrument_sounds_enabled = self.instrumentSoundsToggle.isChecked()
        with self._realtime_audio_lock:
            self._realtime_volume_multipliers['instruments'] = 1.0 if self.instrument_sounds_enabled else 0.0
        
        if self.instrument_sounds_enabled:
            self.instrumentSoundsToggle.setText("MIDI: ON")
        else:
            self.instrumentSoundsToggle.setText("MIDI: OFF")
        
        print(f"Instrument sounds toggled: {'ON' if self.instrument_sounds_enabled else 'OFF'}")

    def load_audio_tracks_from_converter(self):
        """Load all song tracks and drum tracks from the MIDI converter"""
        if not self.midi_converter:
            return
            
        # Clear existing tracks
        self.song_tracks.clear()
        self.drum_tracks.clear()
        self.track_sample_rates.clear()
        
        # Load song tracks
        for i, track_path in enumerate(self.midi_converter.song_tracks):
            if track_path and track_path.strip():
                try:
                    audio_data, sr = sf.read(track_path)
                    # Convert to mono if stereo
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    # Resample if necessary
                    if sr != self.sample_rate:
                        audio_data = np.interp(
                            np.linspace(0, len(audio_data), int(len(audio_data) * self.sample_rate / sr)),
                            np.arange(len(audio_data)),
                            audio_data
                        )
                    self.song_tracks.append(audio_data)
                    self.track_sample_rates.append(sr)
                    print(f"✓ Loaded song track {i+1}: {len(audio_data)} samples at {sr}Hz")
                except Exception as e:
                    print(f"✗ Could not load song track {i+1} ({track_path}): {e}")
                    self.song_tracks.append(None)
                    self.track_sample_rates.append(self.sample_rate)
            else:
                self.song_tracks.append(None)
                self.track_sample_rates.append(self.sample_rate)
                
        # Load drum tracks
        for i, track_path in enumerate(self.midi_converter.drum_tracks):
            if track_path and track_path.strip():
                try:
                    audio_data, sr = sf.read(track_path)
                    # Convert to mono if stereo
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    # Resample if necessary
                    if sr != self.sample_rate:
                        audio_data = np.interp(
                            np.linspace(0, len(audio_data), int(len(audio_data) * self.sample_rate / sr)),
                            np.arange(len(audio_data)),
                            audio_data
                        )
                    self.drum_tracks.append(audio_data)
                    self.track_sample_rates.append(sr)
                    print(f"✓ Loaded drum track {i+1}: {len(audio_data)} samples at {sr}Hz")
                except Exception as e:
                    print(f"✗ Could not load drum track {i+1} ({track_path}): {e}")
                    self.drum_tracks.append(None)
                    self.track_sample_rates.append(self.sample_rate)
            else:
                self.drum_tracks.append(None)
                self.track_sample_rates.append(self.sample_rate)
                
        print(f"Loaded {len([t for t in self.song_tracks if t is not None])} song tracks and {len([t for t in self.drum_tracks if t is not None])} drum tracks")
        
        # Set the main audio data to the longest track for duration calculation
        all_tracks = [t for t in self.song_tracks + self.drum_tracks if t is not None]
        if all_tracks:
            longest_track = max(all_tracks, key=len)
            self.audio_data = longest_track
            print(f"Set main audio data to longest track: {len(longest_track)} samples")
            
        # Generate combined audio and waveform after loading tracks
        self._combine_audio_tracks()
        self._generate_waveform_data()
        
    def _combine_audio_tracks(self):
        """Combine all loaded audio tracks into a single waveform"""
        if not self.song_tracks and not self.drum_tracks:
            self.combined_audio = None
            return
            
        # Get all non-None tracks
        valid_tracks = [t for t in self.song_tracks + self.drum_tracks if t is not None]
        
        if not valid_tracks:
            self.combined_audio = None
            return
            
        # Find the maximum length
        max_length = max(len(track) for track in valid_tracks)
        
        # Create combined audio array
        self.combined_audio = np.zeros(max_length)
        
        # Mix all tracks together
        for track in valid_tracks:
            if len(track) > 0:
                # Pad track to max length if necessary
                if len(track) < max_length:
                    padded_track = np.pad(track, (0, max_length - len(track)), 'constant')
                else:
                    padded_track = track
                    
                # Add to combined audio with normalization to prevent clipping
                self.combined_audio += padded_track * 0.5  # Scale down to prevent clipping
                
        # Normalize the combined audio
        if len(self.combined_audio) > 0:
            max_val = np.max(np.abs(self.combined_audio))
            if max_val > 0:
                self.combined_audio = self.combined_audio / max_val
                
        print(f"✓ Combined audio tracks: {len(self.combined_audio)} samples")
        
    def _generate_waveform_data(self, target_width=2000):
        """Generate downsampled waveform data for visualization"""
        if self.combined_audio is None or len(self.combined_audio) == 0:
            self.waveform_data = None
            return
            
        # Downsample for visualization
        audio_length = len(self.combined_audio)
        
        if audio_length <= target_width:
            # If audio is shorter than target, use it directly
            self.waveform_data = self.combined_audio
        else:
            # Downsample by taking maximum absolute values in chunks
            chunk_size = audio_length // target_width
            waveform = []
            
            for i in range(0, audio_length, chunk_size):
                chunk = self.combined_audio[i:i + chunk_size]
                if len(chunk) > 0:
                    # Take the maximum absolute value in the chunk
                    max_val = np.max(np.abs(chunk))
                    # Preserve the sign of the loudest sample in the chunk
                    max_idx = np.argmax(np.abs(chunk))
                    waveform.append(chunk[max_idx] if max_idx < len(chunk) else max_val)
                    
            self.waveform_data = np.array(waveform)
            
        print(f"✓ Generated waveform data: {len(self.waveform_data)} points")
        
        # Trigger a repaint to show the new waveform
        self.update()
        
    def _draw_waveform(self, painter, piano_roll_width, time_scale, duration):
        """Draw the combined audio waveform above the note timeline"""
        if self.waveform_data is None or len(self.waveform_data) == 0:
            return
            
        # Set up waveform colors
        waveform_color = QColor(100, 150, 255)  # Light blue
        waveform_bg_color = QColor(20, 20, 30)  # Dark background
        waveform_center_color = QColor(80, 80, 80)  # Center line
        
        # Draw waveform background
        waveform_rect_y = 5
        waveform_rect_height = self.waveform_height - 10
        painter.fillRect(self.label_width, waveform_rect_y, piano_roll_width, waveform_rect_height, waveform_bg_color)
        
        # Draw center line
        waveform_center_y = waveform_rect_y + waveform_rect_height // 2
        painter.setPen(QPen(waveform_center_color, 1))
        painter.drawLine(self.label_width, waveform_center_y, self.label_width + piano_roll_width, waveform_center_y)
        
        # Calculate waveform scaling
        waveform_length = len(self.waveform_data)
        if waveform_length == 0:
            return
            
        # Calculate time mapping from waveform samples to display pixels
        audio_duration = len(self.combined_audio) / self.sample_rate if self.combined_audio is not None else duration
        samples_per_second = waveform_length / audio_duration if audio_duration > 0 else 1
        
        # Set up waveform drawing
        painter.setPen(QPen(waveform_color, 1))
        
        # Draw waveform samples
        prev_x = None
        prev_y = None
        
        for i in range(0, waveform_length, max(1, waveform_length // (piano_roll_width * 2))):  # Subsample for performance
            # Calculate time position
            sample_time = (i / samples_per_second) - self.scroll_offset
            x = self.label_width + int(sample_time * time_scale)
            
            # Skip samples outside visible area
            if x < self.label_width or x > self.label_width + piano_roll_width:
                prev_x = None
                prev_y = None
                continue
                
            # Calculate waveform amplitude
            amplitude = self.waveform_data[i] if i < len(self.waveform_data) else 0
            y = waveform_center_y - int(amplitude * (waveform_rect_height // 2 - 5))
            
            # Draw line from previous point
            if prev_x is not None and prev_y is not None:
                painter.drawLine(prev_x, prev_y, x, y)
            
            prev_x = x
            prev_y = y
            
        # Draw waveform label
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawText(5, waveform_rect_y + 15, "Waveform")

    def update_artist_name(self, artist_name):
        """Update the artist name and window title"""
        self.artist_name = artist_name
        self._update_window_title()