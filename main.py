"""Small example OSC server anbd client combined
This program listens to serveral addresses and print if there is an input. 
It also transmits on a different port at the same time random values to different addresses.
This can be used to demonstrate concurrent send and recieve over OSC
"""

import argparse
import random
import time
import threading
import numpy as np
import cv2
import tkinter as tk
from PIL import Image, ImageTk, ImageOps

from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server


class TmView(tk.Tk):
    def __init__(self, analyzer, server):
        self.analyzer = analyzer
        self.server = server

        super().__init__()
        self.title("TouchMatrix Viewer")

        self.view_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        self.control_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        self.view_frame.grid(row=0, column=0, columnspan=2)
        self.control_frame.grid(row=1, column=0)

        self.canvas = tk.Canvas(self.view_frame, height=300, width=600)
        self.canvas.pack(expand=True, fill=tk.BOTH)

        self.server_start_button = tk.Button(self.control_frame, text="Start Server", command=self.server.start_server, width=40)
        self.analyze_start_button = tk.Button(self.control_frame, text="Start Analyze", command=self.analyzer.start, width=40)
        self.cal_lower_button = tk.Button(self.control_frame, text="Lower", command=self.analyzer.calibration_lower, width=40)
        self.cal_upper_button = tk.Button(self.control_frame, text="Upper", command=self.analyzer.calibration_upper, width=40)
        self.read_button = tk.Button(self.control_frame, text="Read Image", command=self.__update_image, width=40)
        self.server_start_button.pack()
        self.analyze_start_button.pack()
        self.cal_lower_button.pack()
        self.cal_upper_button.pack()
        self.read_button.pack()

    def __update_image(self):
        if self.analyzer.disp_img is None:
            self.view_frame.after(100, self.__update_image)
            return

        tmp = (self.analyzer.disp_img * 255).astype(np.uint8)
        self.disp_image(tmp)

        self.view_frame.after(30, self.__update_image)

    def disp_image(self, img):
        # NumPyのndarrayからPillowのImageへ変換
        pil_image = Image.fromarray(img)

        # キャンバスのサイズを取得
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 画像のアスペクト比（縦横比）を崩さずに指定したサイズ（キャンバスのサイズ）全体に画像をリサイズする
        pil_image = ImageOps.pad(pil_image, (canvas_width, canvas_height))

        # PIL.ImageからPhotoImageへ変換する
        self.photo_image = ImageTk.PhotoImage(image=pil_image)

        # 画像の描画
        self.canvas.create_image(
            canvas_width / 2,  # 画像表示位置(Canvasの中心)
            canvas_height / 2,
            image=self.photo_image  # 表示画像データ
        )


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
        self.range = None

        self.led_insert_pos = self.__insert_led()

        self.grad_size = 200
        self.plot_size = (330, 660)
        self.over_scan = 100
        self.grad_img = cv2.imread('resources/grad.png', cv2.IMREAD_GRAYSCALE) / 255
        self.grad_img = cv2.resize(self.grad_img, [self.grad_size, self.grad_size])
        self.plot_img = None
        self.disp_img = None

    def __insert_led(self):
        pos = []
        for i in range(11):
            pos.extend(range((i % 2) + (i * 11), (i + 1) * 11 + (i % 2), 1))
        return pos

    def calibration_lower(self):
        # self.cal_min = self.__tm_frame.n_array
        self.cal_min = np.random.randint(0, 60000, 121, np.uint16)
        print(self.cal_min)
        self.cal_state = self.CAL_MIN

    def calibration_upper(self):
        # self.cal_max = self.__tm_frame.n_array
        self.cal_max = np.random.randint(0, 60000, 121, np.uint16)
        print(self.cal_max)
        self.range = self.cal_max - self.cal_min
        # self.range[self.range < 0] = 0
        print(self.range)
        self.cal_state = self.CAL_MAX

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
            time.sleep(0.03)

    def __clear_plot(self):
        extra_px = self.over_scan * 2
        self.plot_img = np.zeros((self.plot_size[0] + extra_px, self.plot_size[1] + extra_px))

    def __plot(self, sensor_data):
        self.__clear_plot()
        sens_height, sens_width = sensor_data.shape[:2]
        xp = int(self.plot_size[1] / (sens_width - 1))   # step x
        yp = int(self.plot_size[0] / (sens_height - 1))  # step y
        grad_h = int(self.grad_size / 2)

        for hi in range(sens_height):
            for wi in range(sens_width):
                y = (hi * yp) + self.over_scan
                x = (wi * xp) + self.over_scan
                tmp = (self.grad_img * sensor_data[hi, wi])
                self.plot_img[y - grad_h:y + grad_h, x - grad_h:x + grad_h] += tmp

        self.plot_img[self.plot_img > 1.0] = 1.0
        self.disp_img = self.plot_img

    def __loop(self):
        # data = self.__tm_frame.n_array
        data = np.random.randint(0, 60000, 121, np.uint16)

        if data is None:
            return

        # self.__calibration(data)
        if self.cal_min is None or self.cal_max is None:
            return

        # replace out-of-range values (lower)
        data[data <= self.cal_min] = self.cal_min[data <= self.cal_min]
        offset = data - self.cal_min

        # replace out-of-range values (upper)
        offset[offset >= self.range] = self.range[offset >= self.range]

        # normalize
        calc = (offset / self.range)
        calc[calc >= 1.0] = 1.0

        # gamma correction
        """calc = (calc ** 0.7 )* 65535.0"""
        """calc = (np.sin(np.pi * (calc - 0.1)) + 1) / 2 * 65535"""
        """calc = (calc * 3)
        calc[calc >= 1.0] = 1.0"""

        calc = np.insert(calc, self.led_insert_pos, 0)
        calc = np.reshape(calc, (11, 22))

        self.__plot(calc)

        # img3 = cv2.resize(n_array, (int(22 * 50), int(11 * 50)), interpolation=cv2.INTER_NEAREST)
        # cv2.imshow('ir', self.plot_img.astype(np.uint16))
        # cv2.waitKey(1)


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

    def set_buffer(self, value1, value2):
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


if __name__ == "__main__":

    t_frame = TmFrame()

    t_server = OSCServer(t_frame)
    t_analyzer = Analyzer(t_frame)

    t_view = TmView(t_analyzer, t_server)
    t_view.mainloop()
