"""Small example OSC server anbd client combined
This program listens to serveral addresses and print if there is an input. 
It also transmits on a different port at the same time random values to different addresses.
This can be used to demonstrate concurrent send and recieve over OSC
"""

import argparse
import random
import time
import math
import threading
import numpy as np
import cv2

from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server


class TmFrame:

    def __init__(self):
        self.frame_buffer = np.zeros(121)
        self.available = False
        self.n_array = None

    def add_pixel(self, index, value):
        self.frame_buffer[index] = value

    def finalize(self):
        self.available = True
        self.n_array = np.array(self.frame_buffer, np.uint16)


class Analyzer(threading.Thread):
    CAL_MAX = 2
    CAL_MIN = 1

    def __init__(self, tm):
        super().__init__(target=self.__call)

        self.__tm_frame = tm

        self.cal_state = 0
        self.cal_max = None
        self.cal_min = None

        self.led_insert_pos = self.__insert_led()

    def __insert_led(self):
            pos = []
            for i in range(11):
                pos.extend(range((i % 2) + (i * 11), (i + 1) * 11 + (i % 2), 1))
            return pos

    def __calibration(self, data):
        if self.cal_state < self.CAL_MIN:
            print('calibrate min')
            self.cal_min = data
            print(data)
            self.cal_state = self.CAL_MIN
            input()
            return
        if self.cal_state < self.CAL_MAX:
            print('calibrate max')
            self.cal_max = data
            print(data)
            self.range = self.cal_max - self.cal_min
            #self.range[self.range < 0] = 0
            print(self.range)
            self.cal_state = self.CAL_MAX
            return

    def __call(self):
        while True:
            self.__loop()
            time.sleep(0.3)

    def __loop(self):
        data = self.__tm_frame.n_array
        if data is None:
            return

        self.__calibration(data)
        if self.cal_min is not None and self.cal_max is not None:
            data[data <= self.cal_min] = self.cal_min[data <= self.cal_min]
            offset = data - self.cal_min

            offset[offset >= self.range] = self.range[offset >= self.range]

            calc = (offset / self.range)
            calc[calc >= 1.0] = 1.0
            # calc = (calc ** 0.7 )* 65535.0
            # calc = (np.sin(np.pi * (calc - 0.1)) + 1) / 2 * 65535
            calc = (calc * 3) * 65535.0
            calc[calc >= 65535.0] = 65535.0
            n_array = calc.astype(np.uint16)
        else:
            return

        n_array = np.insert(n_array, self.led_insert_pos, 0)
        n_array = np.reshape(n_array, (11, 22))

        img3 = cv2.resize(n_array, (int(22 * 50), int(11 * 50)), interpolation=cv2.INTER_NEAREST)
        cv2.imshow('ir', img3)
        cv2.waitKey(30)



def print_sensor_value(unused_addr, tm_frame_, value1, value2):
    tm_frame_[0].add_pixel(value1, value2)
    if value1 == 120:
        tm_frame_[0].finalize()


def start_server(ip, port):

    print("Starting Server")
    server = osc_server.ThreadingOSCUDPServer(
        (ip, port), dispatcher)
    print("Serving on {}".format(server.server_address))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()


def start_client(ip, port):
    print("Starting Client")
    client = udp_client.SimpleUDPClient(ip, port)
    # print("Sending on {}".format(client.))
    thread = threading.Thread(target=random_values(client))
    thread.start()


# send random values between 0-1 to the three addresses
def random_values(client):        
    while True:
        for x in range(10):
            client.send_message("/1/fader2", random.random())
            client.send_message("/1/fader1", random.random())
            client.send_message("/1/xy1", [random.random(), random.random()])
            time.sleep(.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serverip", default="192.168.1.127", help="The ip to listen on")
    parser.add_argument("--serverport", type=int, default=7000, help="The port the OSC Server is listening on")
    parser.add_argument("--clientip", default="127.0.0.1", help="The ip of the OSC server")
    parser.add_argument("--clientport", type=int, default=5005, help="The port the OSC Client is listening on")
    args = parser.parse_args()

    # touch matrix frame instance initialize
    tm_frame = TmFrame()

    # listen to addresses and print changes in values
    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/sensor_value", print_sensor_value, tm_frame)

    start_server(args.serverip, args.serverport)
    # start_client(args.clientip, args.clientport)

    analyzer = Analyzer(tm_frame)
    analyzer.start()


