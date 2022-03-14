"""Small example OSC server anbd client combined
This program listens to serveral addresses and print if there is an input. 
It also transmits on a different port at the same time random values to different addresses.
This can be used to demonstrate concurrent send and recieve over OSC
"""

import math
import random
import time
import threading
import numpy as np
import cv2

import connection
import controller
from demo import visualizer as vis


class Analyzer(threading.Thread):

    def __init__(self, tm):
        super().__init__(target=self.__call)

        self.__tm_frame = tm

        self.cal_state = 0
        self.cal_max = None
        self.cal_min = None
        self.range = None

        self.curve_type = 0
        self.threshold = 0.3
        self.gamma = 0.7

        self.led_insert_pos = self.__insert_led()

        self.plot_size = (160, 320)
        self.grad_size = 100
        self.over_scan = 60

        self.grad_img = None
        self.plot_img = None
        self.disp_img = None
        self.disp2_img = None
        self.disp3_img = None

        self.set_grad(self.grad_size, 16)

        self.touch_callback = None
        self.draw_callback = None
        self.touch_status = False

        self.latest_data = None

    def set_touch_callback(self, callback):
        self.touch_callback = callback

    def set_draw_callback(self, callback):
        self.draw_callback = callback

    def _call_draw_event(self, labels):
        self.draw_callback(labels)

    def _call_object_event(self, event, position=(0, 0)):
        if self.touch_callback is None:
            return

        if event == cv2.EVENT_MOUSEMOVE:
            y = position[0] / self.plot_size[0]
            x = position[1] / self.plot_size[1]
            self.touch_callback(event, y, x)
        else:
            self.touch_callback(event, 0, 0)

    def __gauss2d(self, size, sd):
        gauss2d = np.zeros((size, size))
        for i in range(size):
            for j in range(size):
                x = i - size / 2
                y = j - size / 2
                gx = (-0.5) * pow((x / sd), 2)
                gy = (-0.5) * pow((y / sd), 2)
                gauss2d[i, j] = math.exp(gx + gy)
        return gauss2d

    def set_grad(self, size, sd):
        self.grad_size = size
        self.grad_img = self.__gauss2d(size, sd)

    def __insert_led(self):
        pos = []
        for i in range(11):
            pos.extend(range((i % 2) + (i * 11), (i + 1) * 11 + (i % 2), 1))
        return pos

    def set_curve(self, c_type):
        self.curve_type = c_type

    def save_data(self):
        np.savez("./cal_data", self.cal_min, self.cal_max, self.range)

    def load_data(self):
        data = None

        try:
            data = np.load("./cal_data.npz")
        except FileNotFoundError:
            print('Calibration file not found')
            return

        print(data.files)
        self.cal_min = data['arr_0']
        self.cal_max = data['arr_1']
        self.range = data['arr_2']

    def calibration_lower(self):
        self.cal_min = self.__tm_frame.n_array
        print(self.cal_min)

    def calibration_upper(self):
        if self.cal_min is None:
            print('need lower calibration')
            return

        self.cal_max = self.__tm_frame.n_array
        print(self.cal_max)
        self.range = self.cal_max - self.cal_min
        print(np.where(self.range == 0))  # ERROR DETECTOR
        # self.range[self.range < 0] = 0
        print(self.range)

    def set_threshold(self, threshold):
        self.threshold = threshold

    def set_curve_param(self, gamma):
        self.gamma = gamma

    def __call(self):
        while True:
            self.__loop()
            time.sleep(0.02)

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

    def put_color_to_objects(self, src_img, label_table):
        label_img = np.zeros_like(src_img)
        for label in range(label_table.max() + 1):
            label_group_index = np.where(label_table == label)
            label_img[label_group_index] = random.sample(range(255), k=3)
        return label_img

    def draw_centroids(self, src_img, centroids):
        centroids_img = src_img
        for coordinate in centroids[1:]:
            center = (int(coordinate[0]), int(coordinate[1]))
            cv2.drawMarker(centroids_img, center, (255, 0, 0), markerType=cv2.MARKER_CROSS,
                           markerSize=20, thickness=2,
                           line_type=cv2.LINE_8)
        return centroids_img

    def __loop(self):
        data = self.__tm_frame.n_array
        self.latest_data = data

        if data is None:
            return

        if self.cal_min is None or self.cal_max is None:
            return

        # replace out-of-range values (lower)
        data[data < self.cal_min] = self.cal_min[data < self.cal_min]
        offset = data - self.cal_min

        # replace out-of-range values (upper)
        offset[offset > self.range] = self.range[offset > self.range]

        # normalize
        calc = (offset / self.range) + 0.02
        calc[calc > 1.0] = 1.0

        # tone curve
        if self.curve_type == 1:
            calc = (calc ** self.gamma)
        if self.curve_type == 2:
            calc = (np.sin(np.pi * (calc - 0.1)) + 1) / 2
        if self.curve_type == 3:
            calc = (calc * 3)
        calc[calc > 1.0] = 1.0

        calc = np.insert(calc, self.led_insert_pos, 0)
        calc = np.reshape(calc, (11, 22))

        self.__plot(calc)

        tmpx = self.over_scan + self.plot_size[0]
        tmpy = self.over_scan + self.plot_size[1]
        ret, tmp = cv2.threshold(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy],
                                 float(self.threshold), 1.0, cv2.THRESH_BINARY)

        kernel = np.ones((5, 5), np.uint8)
        tmp = cv2.dilate(tmp, kernel, iterations=5)
        tmp = cv2.erode(tmp, kernel, iterations=5)

        tmp8bit = (tmp * 255).astype(np.uint8)                          # 8bitのスケールへ変換
        color = np.zeros((tmp.shape[0], tmp.shape[1], 3), np.uint8)     # 3chの画像を生成
        cv2.cvtColor(tmp8bit, cv2.COLOR_GRAY2RGB, color)                # RGB画像へ変換

        retval, labels, stats, centroids = cv2.connectedComponentsWithStats(tmp8bit)        # Labeling

        if len(centroids) > 1:
            self._call_object_event(cv2.EVENT_MOUSEMOVE, centroids[1])
            if self.touch_status is False:
                self._call_object_event(cv2.EVENT_RBUTTONDOWN)
                self.touch_status = True
        else:
            if self.touch_status is True:
                self._call_object_event(cv2.EVENT_RBUTTONUP)
                self.touch_status = False

        color_labels = self.draw_centroids(color, centroids)
        self._call_draw_event(color_labels)

        self.disp_img = color_labels
        self.disp2_img = (self.plot_img * 255).astype(np.uint8)
        self.disp3_img = cv2.resize(calc * 255, (self.plot_size[1], self.plot_size[0]), interpolation=cv2.INTER_NEAREST)


if __name__ == "__main__":

    # Sharing Data
    t_frame = connection.TmFrame()

    # initialize instance
    t_server = connection.OSCServer(t_frame, "192.168.0.4")
    t_client = connection.FrameTransmitter(ip='192.168.0.2')
    t_analyzer = Analyzer(t_frame)
    t_visualizer = vis.Visualizer((320, 640))
    t_view = controller.TmView(t_analyzer, t_server, t_visualizer, t_client)

    # set touch event callback
    t_analyzer.set_touch_callback(t_visualizer.touch_event_from_analyzer)
    t_analyzer.set_draw_callback(t_visualizer.set_object_image)
    # set draw event callback
    t_visualizer.set_callback(t_client.set_frame)

    # initialize demo contents instance
    from demo import continuous_lines, turn_table, synthesizer, object_detection, object_scan, ocr, find_contours, touch_send
    demo_lines = continuous_lines.ContinuousLines(t_visualizer)
    demo_table = turn_table.TurnTable(t_visualizer)
    demo_synth = synthesizer.Synthesizer(t_visualizer)
    demo_detection = object_detection.ObjectDetection(t_visualizer)
    demo_scan = object_scan.ObjectScan(t_visualizer)
    demo_graphic = ocr.OCR(t_visualizer)
    demo_contours = find_contours.FindContours(t_visualizer)
    demo_touch = touch_send.TouchSend(t_visualizer, t_client)

    # register demo contents
    t_view.insert_contents(demo_lines)
    t_view.insert_contents(demo_table)
    t_view.insert_contents(demo_synth)
    t_view.insert_contents(demo_detection)
    t_view.insert_contents(demo_scan)
    t_view.insert_contents(demo_graphic)
    t_view.insert_contents(demo_contours)
    t_view.insert_contents(demo_touch)

    t_server.start_server()
    t_analyzer.start()

    # start gui
    t_view.mainloop()
