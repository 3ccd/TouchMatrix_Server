import threading
import time

import numpy as np

from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import osc_bundle_builder
from pythonosc import osc_message_builder


class TmFrame:

    def __init__(self):
        self.frame_buffer = np.zeros(121, np.uint16)
        self.available = False
        self.n_array = None

    def add_pixel(self, index, value):
        self.frame_buffer[index] = value

    def finalize(self):
        self.available = True
        self.n_array = np.array(self.frame_buffer, np.uint16)


class OSCServer:
    def __init__(self, tm_frame, ip="127.0.0.1", port=7000):
        self.ip = ip
        self.port = port
        self.server = None
        self.buffer = tm_frame

        # listen to addresses and print changes in values
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/sensor_value", self.set_buffer)

    def set_addr(self, ip, port):
        self.ip = ip
        self.port = port

    def set_buffer(self, something,  value1, value2):
        self.buffer.add_pixel(value1, value2)
        if value1 == 120:
            self.buffer.finalize()

    def start_server(self):
        print("Starting Server")
        try:
            self.server = osc_server.ThreadingOSCUDPServer(
                (self.ip, self.port), self.dispatcher)
        except OSError:
            print("Error : Wrong Address")
            return
        print("Serving on {}".format(self.server.server_address))
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()

    def stop(self):
        self.server.stop()


class FrameTransmitter:

    def __init__(self, ip="127.0.0.1", port=9000):
        self.ip = ip
        self.port = port
        self.frame_status = False
        self.frame = np.zeros((32, 64, 3), dtype=np.uint8)
        self.running = False
        self.client = udp_client.SimpleUDPClient(self.ip, self.port)

        self.lock = threading.Lock()

    def set_frame(self, frame):
        self.frame = frame.copy()
        self.frame_status = True

    def __get_frame(self, ch):
        self.frame_status = False
        if ch == 'r':
            return self.frame[:, :, 0].flatten().tolist()
        if ch == 'g':
            return self.frame[:, :, 1].flatten().tolist()
        if ch == 'b':
            return self.frame[:, :, 2].flatten().tolist()

    def send_message(self, address, x, y):
        self.lock.acquire()
        self.client.send_message(address, [x, y])
        self.lock.release()

    def __transmit_frame(self):
        while self.running:
            if self.frame_status is False:
                time.sleep(1)       # wait for frame data
                continue

            self.lock.acquire()
            self.client.send_message("/frame/red/upper", self.__get_frame('r')[:1024])
            self.client.send_message("/frame/red/lower", self.__get_frame('r')[1024:])
            self.client.send_message("/frame/green/upper", self.__get_frame('g')[:1024])
            self.client.send_message("/frame/green/lower", self.__get_frame('g')[1024:])
            self.client.send_message("/frame/blue/upper", self.__get_frame('b')[:1024])
            self.client.send_message("/frame/blue/lower", self.__get_frame('b')[1024:])
            self.lock.release()
            time.sleep(0.05)

    def start_client(self):
        print("Starting Client")
        self.running = True
        print("Sending on {}".format(self.ip))
        thread = threading.Thread(target=self.__transmit_frame)
        thread.start()
