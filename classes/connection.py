import threading
import time

import numpy as np

from classes.tracker import Touch, Blob, ObjTracker

from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server

import serial


class TmFrame:

    def __init__(self):
        self.frame_buffer = np.zeros((121, 5), np.uint16)
        self.available = False
        self.n_array = None
        self.n_array_4led = None

        self.time_stamp = 0.0
        self.prev_time_stamp = -1.0

    def add_pixel(self, index, value, mode):
        if index >= 121:
            return
        self.frame_buffer[index, mode] = value

    def get_rate(self):
        if self.time_stamp - self.prev_time_stamp == 0.0:
            return 1.0
        return 1.0 / (self.time_stamp - self.prev_time_stamp)

    def finalize(self):
        self.available = True
        self.n_array = np.array(self.frame_buffer[:, 0], np.uint16)
        self.n_array_4led = np.array(self.frame_buffer[:, 1:5], np.uint16)

        self.prev_time_stamp = self.time_stamp
        self.time_stamp = time.time()


class SerialServer:
    def __init__(self, tm_frame, dev="/dev/ttyACM0", baud=115200):
        self.dev = dev
        self.baud = baud
        self.running = False
        self.buffer = tm_frame
        self.ip = dev

        self.read_data = []
        self.prev_data = 0
        self.reading = False
        self.esc = False

    def set_addr(self, ip, port):
        self.dev = ip
        self.baud = port

    def set_buffer(self):
        num = int.from_bytes(self.read_data[0], 'big')
        mode = int.from_bytes(self.read_data[1], 'big')
        value = (int.from_bytes(self.read_data[2], 'big') << 8) | int.from_bytes(self.read_data[3], 'big')

        self.buffer.add_pixel(num, value, mode)
        if num == 120 and mode == 4:
            self.buffer.finalize()

        self.read_data.clear()

    def decode_slip(self, char):
        # detect end packet
        if char == b'\xc0':
            self.reading = True
            return

        if self.reading:
            # detect escape packet
            if char == b'\xdb':
                self.esc = True
                return

            # if escaping
            if self.esc:
                if char == b'\xdc':
                    self.read_data.append(b'\xc0')
                if char == b'\xdd':
                    self.read_data.append(b'\xdb')
                self.esc = False
            else:
                self.read_data.append(char)

            if len(self.read_data) == 4:
                self.set_buffer()
                self.reading = False

    def read(self):
        ser = serial.Serial(self.dev, self.baud, timeout=1)
        while self.running:
            char = ser.read()
            self.decode_slip(char)
        ser.close()

    def start_server(self):
        print("Starting Server")
        print("Serving on {}".format(self.dev))
        thread = threading.Thread(target=self.read)
        thread.start()
        self.running = True

    def stop(self):
        if self.running:
            self.running = False


class OSCServer:
    def __init__(self, tm_frame, ip="127.0.0.1", port=7000):
        self.ip = ip
        self.port = port
        self.server = None
        self.buffer = tm_frame

        self.running = False

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
        self.running = True

    def stop(self):
        if self.running:
            self.server.shutdown()


class ObjTransmitter:

    def __init__(self, ip="127.0.0.1", port=9000):
        self.ip = ip
        self.port = port
        self.running = False
        self.client = udp_client.SimpleUDPClient(self.ip, self.port)

    def set_addr(self, ip, port):
        self.ip = ip
        self.port = port

    def send_message(self, obj, event):
        if not self.running:
            return
        if isinstance(obj, Touch):
            base_path = "/touch/"+str(obj.oid)
            if event is ObjTracker.EVENT_OBJ_UPDATE:
                self.client.send_message(base_path + "/point", [int(obj.y * 0.2), int(obj.x * 0.2)])
            elif event is ObjTracker.EVENT_OBJ_DELETE:
                self.client.send_message(base_path + "/delete", [-1, -1])

        if isinstance(obj, Blob):
            base_path = "/blob/" + str(obj.oid)
            if event is ObjTracker.EVENT_OBJ_UPDATE:
                self.client.send_message(base_path + "/point", obj.point)
                self.client.send_message(base_path + "/bbox1", obj.point1)
                self.client.send_message(base_path + "/bbox2", obj.point2)
                self.client.send_message(base_path + "/contour", obj.shape.flatten().tolist())
            if event is ObjTracker.EVENT_OBJ_DELETE:
                self.client.send_message(base_path + "/delete", [-1, -1])

    def start_client(self):
        print("Starting Obj Client")
        self.client = udp_client.SimpleUDPClient(self.ip, self.port)
        self.running = True
        print("Sending on {}".format(self.ip))


class FrameTransmitter:

    def __init__(self, ip="127.0.0.1", port=9001):
        self.ip = ip
        self.port = port
        self.frame_status = False
        self.frame = np.zeros((32, 64, 3), dtype=np.uint8)
        self.running = False
        self.client = udp_client.SimpleUDPClient(self.ip, self.port)

        self.lock = threading.Lock()
        self.thread = None
        self.running = False

    def set_frame(self, frame):
        self.frame = frame.copy()
        self.frame_status = True

    def set_addr(self, ip, port):
        self.ip = ip
        self.port = port

    def __get_frame(self, ch):
        self.frame_status = False
        if ch == 'r':
            return self.frame[:, :, 0].flatten().tolist()
        if ch == 'g':
            return self.frame[:, :, 1].flatten().tolist()
        if ch == 'b':
            return self.frame[:, :, 2].flatten().tolist()

    def send_message(self, address, data):
        self.lock.acquire()
        self.client.send_message(address, data)
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
        print("Starting Frame Client")
        self.running = True
        self.client = udp_client.SimpleUDPClient(self.ip, self.port)
        print("Sending on {}".format(self.ip))
        self.thread = threading.Thread(target=self.__transmit_frame)
        self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.thread.join()
