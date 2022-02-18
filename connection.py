import threading
import time

import numpy as np

from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server


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
        self.server = osc_server.ThreadingOSCUDPServer(
            (self.ip, self.port), self.dispatcher)
        print("Serving on {}".format(self.server.server_address))
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()

    def stop(self):
        self.server.stop()


class FrameTransmitter:

    def __init__(self, ip="127.0.0.1", port=8585):
        self.ip = ip
        self.port = port
        self.frame_status = False
        self.frame = np.zeros((32, 64, 3), dtype=np.uint8)
        self.running = False
        self.client = None

    def set_frame(self, frame):
        self.frame = frame
        self.frame_status = True

    def __get_frame(self):
        self.frame_status = False
        return self.frame

    def __conversion(self):
        send_data = self.frame.tolist()
        return send_data

    def __transmit_frame(self):
        while self.running:
            if self.frame_status is False:
                time.sleep(1)       # wait for frame data
                continue

            self.client.send_message("/frame", self.__conversion())
            time.sleep(0.05)

    def start_client(self):
        print("Starting Client")
        self.running = True
        self.client = udp_client.SimpleUDPClient(self.ip, self.port)
        print("Sending on {}".format(self.ip))
        thread = threading.Thread(target=self.__transmit_frame)
        thread.start()
