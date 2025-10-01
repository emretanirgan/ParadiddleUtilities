# Copyright (C) 2020 Emre Tanirgan <emre@paradiddleapp.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from mido import MidiFile, tempo2bpm
import threading
import socket
from PyQt5.QtWidgets import *
import mido
import json
import os
from shutil import copyfile
import soundfile as sf
import copy
import time
from enum import Enum

class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    HANDSHAKE_SENT = 2
    CONNECTED = 3

message_types = {
    8: "note_off",
    9: "note_on",
    10: "polytouch",
    11: "control_change",
    12: "program_change",
    13: "aftertouch",
    14: "pitchwheel"
}

# Midi Companion class that receives incoming UDP midi messages
# and converts them to proper midi messages sent to a midi output
# through mido.
class MidiCompanion:
    def __init__(self):
        self.midi_input = None
        self.midi_output = None
        self.midi_output_index = 0
        self.midi_input_index = 0
        self.host_ip = None
        self.connected_to_host = False

        self.midi_msg_cb = None
        self.connection_cb = None
        self.midi_out_port = None
        self.midi_in_port = None

        self.client_socket = None
        self.midi_input_enabled = True  # New flag to control MIDI input

        self.midi_outputs = mido.get_output_names()
        self.midi_inputs = mido.get_input_names()

        self.connection_state = ConnectionState.DISCONNECTED
        self.handshake_timeout = 5.0  # seconds
        self.handshake_retry_interval = 1.0  # seconds
        self.last_handshake_time = 0
        self.last_heartbeat_time = 0
        self.heartbeat_interval = 30.0  # seconds
        self.connection_timeout = 60.0  # seconds
        self.handshake_attempts = 0
        self.max_handshake_attempts = 2

        return
    
    def set_midi_input_enabled(self, enabled):
        """Enable or disable MIDI input forwarding to VR"""
        self.midi_input_enabled = enabled
        if enabled and self.is_connected():
            self.setup_midi_input()
        elif not enabled and self.midi_in_port:
            self.cleanup_midi_input()
    
    def setup_midi_input(self):
        """Set up MIDI input port for reading from hardware"""
        if self.midi_inputs and self.midi_input_index < len(self.midi_inputs):
            try:
                if self.midi_in_port is None or self.midi_in_port.closed:
                    self.midi_in_port = mido.open_input(
                        self.midi_inputs[self.midi_input_index], 
                        callback=self.on_midi_input_message
                    )
                    print(f"Connected to MIDI input: {self.midi_inputs[self.midi_input_index]}")
            except Exception as e:
                print(f"Error connecting to MIDI input: {e}")
    
    def cleanup_midi_input(self):
        """Clean up MIDI input port"""
        if self.midi_in_port and not self.midi_in_port.closed:
            self.midi_in_port.close()
            self.midi_in_port = None
            print("Disconnected from MIDI input")
    
    def on_midi_input_message(self, message):
        """Callback for when MIDI messages are received from hardware"""
        print(message)
        # print("midi input enabled: " + str(self.midi_input_enabled) + " connected to host: " + str(self.connected_to_host))
        if not self.midi_input_enabled or not self.is_connected():
            return
        
        try:
            # Convert note_on with velocity 0 to note_off for consistency
            temp_msg = message
            if message.type == "note_on" and message.velocity == 0:
                temp_msg = mido.Message("note_off", channel=message.channel, note=message.note, velocity=message.velocity)
                
            # Convert MIDI message to bytes for UDP transmission
            midi_bytes = self.midi_message_to_bytes(temp_msg)
            if midi_bytes:
                self.client_socket.send(midi_bytes)
                print(f"Sent MIDI to VR: {temp_msg}")
                
        except Exception as e:
            print(f"Error sending MIDI message to VR: {e}")
    
    def midi_message_to_bytes(self, message):
        """Convert mido MIDI message to byte array for UDP transmission"""
        try:
            if message.type in ["note_on", "note_off"]:
                event_type = 9 if message.type == "note_on" else 8
                return bytearray([event_type, message.channel, message.note, message.velocity])
            elif message.type == "control_change":
                return bytearray([11, message.channel, message.control, message.value])
            elif message.type == "polytouch":
                return bytearray([10, message.channel, message.note, message.value])
            elif message.type == "program_change":
                return bytearray([12, message.channel, message.program, 0])
            elif message.type == "aftertouch":
                return bytearray([13, message.channel, message.value, 0])
            elif message.type == "pitchwheel":
                # Pitchwheel needs special handling for 14-bit value
                value = message.pitch + 8192  # Convert from signed to unsigned
                lsb = value & 0x7F
                msb = (value >> 7) & 0x7F
                return bytearray([14, message.channel, lsb, msb])
        except Exception as e:
            print(f"Error converting MIDI message to bytes: {e}")
        return None
    
    def disconnect_from_host(self):
        self.stopEvent.set()
        self.cleanup_midi_input()
        self.client_socket.close()
        self.client_socket = None
        self.connected_to_host = False
        self.connection_state = ConnectionState.DISCONNECTED
        if(self.connection_cb):
            self.connection_cb(False)
        return

    
    def connect_to_midi_output(self, midi_output):
        # mido.open_output(midi_output)
        self.midi_output = midi_output
        return
    
    def set_midi_input_index(self, index):
        """Set which MIDI input device to use"""
        if 0 <= index < len(self.midi_inputs):
            self.midi_input_index = index
            # Reconnect if currently connected
            if self.midi_input_enabled and self.is_connected():
                self.cleanup_midi_input()
                self.setup_midi_input()
    
    def is_connected(self):
        """Check if properly connected to VR"""
        return self.connection_state == ConnectionState.CONNECTED
        
    def connect_to_host(self, host_ip):
        self.host_ip = host_ip
        self.connection_state = ConnectionState.CONNECTING
        
        print(f"Connecting to host: {host_ip}")
        
        # Set up MIDI output
        if self.midi_out_port is None or self.midi_out_port.closed:
            self.midi_out_port = mido.open_output(self.midi_outputs[self.midi_output_index])
            print("Connected to " + self.midi_outputs[self.midi_output_index])
        
        # Set up MIDI input if enabled
        if self.midi_input_enabled:
            self.setup_midi_input()
            
        port = 9999
        if self.client_socket is None:
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.client_socket.settimeout(1.0)  # 1 second timeout for receives
                self.client_socket.connect((self.host_ip, port))
                
                self.stopEvent = threading.Event()
                self.midithread = threading.Thread(target=self.listening_thread)
                self.midithread.start()
                self.handshake_attempts = 1
                # Start handshake process
                self.initiate_handshake()
                
            except Exception as e:
                print(f"Error connecting to host: {e}")
                self.connection_state = ConnectionState.DISCONNECTED
                return False
        else:
            print("Already connected to a socket")
            
        return True
    
    def initiate_handshake(self):
        """Start the handshake process"""
        self.connection_state = ConnectionState.HANDSHAKE_SENT
        self.last_handshake_time = time.time()
        
        handshake_msg = {
            "type": "handshake_request",
            "timestamp": time.time(),
            "client_id": "midi_companion",
            "version": "1.0",
        }
        
        try:
            message_str = json.dumps(handshake_msg)
            self.client_socket.send(message_str.encode('utf-8'))
            print(f"Sent handshake request (attempt {self.handshake_attempts})")
        except Exception as e:
            print(f"Error sending handshake: {e}")
            self.connection_state = ConnectionState.DISCONNECTED
    
    def handle_handshake_response(self, message_data):
        """Handle handshake response from VR"""
        try:
            response = json.loads(message_data.decode('utf-8'))
            
            if response.get("type") == "handshake_response":
                if response.get("status") == "accepted":
                    self.connection_state = ConnectionState.CONNECTED
                    self.last_heartbeat_time = time.time()
                    print("Handshake successful - connection established!")
                    
                    if self.connection_cb:
                        self.connection_cb(True)
                        
                    return True
                else:
                    print(f"Handshake rejected: {response.get('reason', 'Unknown')}")
                    self.connection_state = ConnectionState.DISCONNECTED
                    return False
                    
        except json.JSONDecodeError:
            # Not a JSON message, might be MIDI data
            return False
        except Exception as e:
            print(f"Error handling handshake response: {e}")
            return False
            
        return False
    
    def send_heartbeat(self):
        """Send heartbeat to maintain connection"""
        if self.connection_state != ConnectionState.CONNECTED:
            return
            
        heartbeat_msg = {
            "type": "heartbeat",
            "timestamp": time.time()
        }
        
        try:
            message_str = json.dumps(heartbeat_msg)
            self.client_socket.send(message_str.encode('utf-8'))
            self.last_heartbeat_time = time.time()
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
            self.connection_state = ConnectionState.DISCONNECTED
    
    def check_connection_health(self):
        """Check if connection is still healthy and handle timeouts"""
        current_time = time.time()
        
        if self.connection_state == ConnectionState.HANDSHAKE_SENT:
            # Check for handshake timeout
            if current_time - self.last_handshake_time > self.handshake_timeout:
                if self.handshake_attempts < self.max_handshake_attempts:
                    print(f"Handshake timeout, retrying... (attempt {self.handshake_attempts + 1})")
                    self.handshake_attempts += 1
                    self.initiate_handshake()
                else:
                    print("Handshake failed after maximum attempts")
                    self.disconnect_from_host()
                        
        elif self.connection_state == ConnectionState.CONNECTED:
            # Send periodic heartbeats
            if current_time - self.last_heartbeat_time > self.heartbeat_interval:
                self.send_heartbeat()
                
            # Check for connection timeout (no response from VR)
            if current_time - self.last_heartbeat_time > self.connection_timeout:
                print("Connection timeout - lost connection to VR")
                self.connection_state = ConnectionState.DISCONNECTED
                if self.connection_cb:
                    self.connection_cb(False)
    
    def listening_thread(self):
        """Enhanced listening thread with connection management"""
        global message_types
        
        while not self.stopEvent.is_set():
            try:
                self.check_connection_health()
                
                # Only attempt to receive if we have a valid socket
                if self.client_socket is None:
                    time.sleep(0.1)
                    continue
                
                try:
                    data_raw, addr = self.client_socket.recvfrom(1024)
                except socket.timeout:
                    # Timeout is normal, just continue checking
                    continue
                except Exception as e:
                    print(f"Socket receive error: {e}")
                    break
                
                # Handle handshake responses first
                if self.connection_state == ConnectionState.HANDSHAKE_SENT:
                    if self.handle_handshake_response(data_raw):
                        continue  # Handshake handled, continue to next message
                
                # Handle heartbeat responses
                try:
                    if data_raw.startswith(b'{"type":"heartbeat_response"'):
                        self.last_heartbeat_time = time.time()
                        continue
                except:
                    pass  # Not a heartbeat, continue with MIDI processing
                
                # Only process MIDI if we're properly connected
                if self.connection_state != ConnectionState.CONNECTED:
                    continue
                
                # Process MIDI data (your existing MIDI handling code)
                if len(data_raw) >= 4 and all(isinstance(b, int) for b in data_raw[:4]):
                    nums = list(data_raw)
                    msg = None
                    
                    if nums[0] in message_types and len(nums) >= 4:
                        try:
                            if message_types[nums[0]] == "note_on" or message_types[nums[0]] == "note_off":
                                msg = mido.Message(message_types[nums[0]], channel=nums[1], note=nums[2], velocity=nums[3])
                            elif message_types[nums[0]] == "control_change":
                                msg = mido.Message(message_types[nums[0]], channel=nums[1], control=nums[2], value=nums[3])
                            elif message_types[nums[0]] == "polytouch":
                                msg = mido.Message(message_types[nums[0]], channel=nums[1], note=nums[2], value=nums[3])
                            elif message_types[nums[0]] == "program_change":
                                msg = mido.Message(message_types[nums[0]], channel=nums[1], program=nums[2])
                            elif message_types[nums[0]] == "aftertouch":
                                msg = mido.Message(message_types[nums[0]], channel=nums[1], value=nums[2])
                            elif message_types[nums[0]] == "pitchwheel":
                                # Reconstruct 14-bit pitch value
                                pitch_value = (nums[3] << 7) | nums[2]
                                pitch_value -= 8192  # Convert back to signed
                                msg = mido.Message(message_types[nums[0]], channel=nums[1], pitch=pitch_value)
                        except Exception as e:
                            print("Error constructing midi message: " + str(e))
                    
                    if msg is not None:
                        print("Received MIDI from VR: ", msg)
                        if self.midi_msg_cb:
                            self.midi_msg_cb(str(msg))
                        if self.midi_out_port:
                            self.midi_out_port.send(msg)
                            
            except Exception as e:
                print(f"Error in listening thread: {e}")
                if not self.stopEvent.is_set():
                    time.sleep(1)  # Brief pause before retrying
                    continue
                else:
                    break

# def connect_to_host(self, host_ip):
    #     self.host_ip = host_ip

    #     print(mido.get_output_names())
    #     print(self.midi_output_index)
    #     if self.midi_out_port is None or self.midi_out_port.closed:
    #         self.midi_out_port = mido.open_output(self.midi_outputs[self.midi_output_index])
    #         print("Connected to " + self.midi_outputs[self.midi_output_index])
        
    #     # Set up MIDI input if enabled
    #     if self.midi_input_enabled:
    #         self.setup_midi_input()
            
    #     # can use for local testing
    #     # host = socket.gethostname()  # as both code is running on same pc
    #     port = 9999  # socket server port number
    #     print("About to connect")
    #     if self.client_socket is None:
    #         self.client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  # instantiate
    #         self.client_socket.connect((self.host_ip, port))  # connect to the server
    #         self.connected_to_host = True
    #         if(self.connection_cb):
    #             self.connection_cb(True)
    #         print("post connect")
    #         try:
    #             self.stopEvent = threading.Event()
    #             self.midithread = threading.Thread(target=self.listening_thread)
    #             self.midithread.start()
    #         except:
    #             print ("Error: unable to start thread")
    #             quit()
    #     else:
    #         print("Already connected to a socket")

    #     return

    # Define a function for the thread
    # def listening_thread(self):
    #     global message_types
    #     self.client_socket.send("boop".encode())  # send message - for UDP connections we need to send a message to establish recipient address
    #     while not self.stopEvent.is_set():
    #         try:
    #             data_raw, addr = self.client_socket.recvfrom(128)
                
    #             nums = list(data_raw)  # Direct conversion
    #             print(f"Received bytes: {nums}")
    #             # prev method before ^
    #             # print(type(data_raw))
    #             # nums = []
    #             # for c in data_raw:
    #             #     print ([c, type(c)], sep=" ")
    #             #     nums.append(c)
    #             # print(nums)
                
    #             msg = None
    #             if nums[0] in message_types and len(nums) >= 4:
    #                 try:
    #                     if message_types[nums[0]] == "note_on" or message_types[nums[0]] == "note_off":
    #                         msg = mido.Message(message_types[nums[0]], channel=nums[1], note=nums[2], velocity=nums[3])
    #                     elif message_types[nums[0]] == "control_change":
    #                         msg = mido.Message(message_types[nums[0]], channel=nums[1], control=nums[2], value=nums[3])
    #                     elif message_types[nums[0]] == "polytouch":
    #                         msg = mido.Message(message_types[nums[0]], channel=nums[1], note=nums[2], value=nums[3])
    #                     elif message_types[nums[0]] == "program_change":
    #                         msg = mido.Message(message_types[nums[0]], channel=nums[1], program=nums[2])
    #                     elif message_types[nums[0]] == "aftertouch":
    #                         msg = mido.Message(message_types[nums[0]], channel=nums[1], value=nums[2])
    #                     elif message_types[nums[0]] == "pitchwheel":
    #                         # Reconstruct 14-bit pitch value
    #                         pitch_value = (nums[3] << 7) | nums[2]
    #                         pitch_value -= 8192  # Convert back to signed
    #                         msg = mido.Message(message_types[nums[0]], channel=nums[1], pitch=pitch_value)
    #                 except Exception as e:
    #                     print("Error constructing midi message: " + str(e))
    #             else:
    #                 print("Unknown message type " + str(nums[0]))
                
    #             if msg is not None:
    #                 print ("Received midi from VR: ", msg)
    #                 if(self.midi_msg_cb):
    #                     self.midi_msg_cb(str(msg))
    #                 if(self.midi_out_port):
    #                     print("sending to MIDI output port")
    #                     self.midi_out_port.send(msg)
                        
    #         except Exception as e:
    #             print(f"Error in listening thread: {e}")
    #             if not self.stopEvent.is_set():
    #                 continue
    #             else:
    #                 break