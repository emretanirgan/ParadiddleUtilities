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

        self.midi_outputs = mido.get_output_names()
        self.midi_inputs = mido.get_input_names()

        return
    
    def connect_to_host(self, host_ip):
        self.host_ip = host_ip

        print(mido.get_output_names())
        print(self.midi_output_index)
        if self.midi_out_port is None or self.midi_out_port.closed:
            self.midi_out_port = mido.open_output(self.midi_outputs[self.midi_output_index])
            print("Connected to " + self.midi_outputs[self.midi_output_index])
        # MIDI input is work in progress
        # if self.midi_in_port is None or self.midi_in_port.closed:
        #     self.midi_in_port = mido.open_input(self.midi_inputs[self.midi_input_index])
        #     print("Connected to " + self.midi_inputs[self.midi_input_index])
        # can use for local testing
        # host = socket.gethostname()  # as both code is running on same pc
        port = 9999  # socket server port number
        print("About to connect")
        if self.client_socket is None:
            self.client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  # instantiate
            self.client_socket.connect((self.host_ip, port))  # connect to the server
            self.connected_to_host = True
            if(self.connection_cb):
                self.connection_cb(True)
            print("post connect")
            try:
                self.stopEvent = threading.Event()
                self.midithread = threading.Thread(target=self.listening_thread)
                self.midithread.start()
            except:
                print ("Error: unable to start thread")
                quit()
        else:
            print("Already connected to a socket")

        # for msg in self.midi_in_port:
        #     print(msg)

        return
    
    def disconnect_from_host(self):
        self.stopEvent.set()
        self.client_socket.close()
        self.client_socket = None
        self.connected_to_host = False
        if(self.connection_cb):
            self.connection_cb(False)
        return

    
    def connect_to_midi_output(self, midi_output):
        # mido.open_output(midi_output)
        self.midi_output = midi_output
        return
    
    # Define a function for the thread
    def listening_thread(self):
        global message_types
        self.client_socket.send("boop".encode())  # send message - for UDP connections we need to send a message to establish recipient address
        while not self.stopEvent.is_set():
            # MIDI input - work in progress
            # for msg in self.midi_in_port.iter_pending():
            #     tempmsg = msg
            #     if msg.type == "note_on" and msg.velocity == 0:
            #         tempmsg = mido.Message("note_off", channel=msg.channel, note=msg.note, velocity=msg.velocity)
            #     my_bytes = bytearray()
            #     for byte in tempmsg.bytes():
            #         my_bytes.append(byte)
            #         print(byte)
            #     # # my_bytes = msg.bytes()
            #     self.client_socket.send(my_bytes)

            #     # self.client_socket.send(msg.bin())
            #     # self.client_socket.send(str(msg).encode())
            #     print(msg)
            # continue
            data_raw = None
            data_raw, addr = self.client_socket.recvfrom(128)

            print(type(data_raw))
            # try:
            #     # data_raw, addr = self.client_socket.recvfrom(1024)
            #     data_raw, addr = self.client_socket.recvfrom(1024).decode()
            #     # midi_out_port.send(mido.Message.from_bytes(data.encode()))
            # except:
            #     print("Error receiving message")
            #     # self.stopEvent.set()
            #     break
            # print(data_raw)
            # print("chars")
            nums = []
            for c in data_raw:
                print ([c, type(c)], sep=" ")
                nums.append(c)
            print(nums)
            # recvmidi = mido.parse(nums)
            # recvmidi = mido.Message.from_bytes(nums)
            msg = None
            if nums[0] in message_types and len(nums) > 3:
                try:
                    if message_types[nums[0]] == "note_on" or message_types[nums[0]] == "note_off":
                        msg = mido.Message(message_types[nums[0]], channel=nums[1], note=nums[2], velocity=nums[3])
                    elif message_types[nums[0]] == "control_change":
                        msg = mido.Message(message_types[nums[0]], channel=nums[1], control=nums[2], value=nums[3])
                    elif message_types[nums[0]] == "polytouch":
                        msg = mido.Message(message_types[nums[0]], channel=nums[1], note=nums[2], value=nums[3])
                except Exception as e:
                    print("Error constructing midi message: " + str(e))
            else:
                print("Unknown message type " + str(nums[0]))
            # # print ("Received message inside thread:", data)
            if msg is not None:
                print ("Received midi: ", msg)
                if(self.midi_msg_cb):
                    self.midi_msg_cb(str(msg))
                if(self.midi_out_port):
                    print("sending to port")
                    self.midi_out_port.send(msg)
