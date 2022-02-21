import time
from abc import ABCMeta, abstractmethod
import threading
import numpy as np
import cv2

import pygame.midi as midi


class Visualizer:

    def __init__(self, size):
        self.thread = None
        self.running = False            # スレッド処理の状態
        self.content = None             # 表示するコンテンツ

        self.frame_size = size          # 描画サイズ
        self.is_touch = False           # タッチしているか
        self.touch_pos = (-1, -1)       # タッチ座標
        self.prev_touch_pos = (-1, -1)  # 前回のタッチ座標

        self.draw_callback = None

        self.object_image = np.zeros(self.frame_size, dtype=np.uint8)

        self.midi_out = None
        self.init_midi()

    def set_callback(self, cb):
        self.draw_callback = cb

    def __call(self, result):
        self.draw_callback(result)

    def run(self):
        while self.running:
            if self.content is None:
                time.sleep(2)
                continue

            self.content.draw()

            cv2.imshow("Visualizer", self.content.frame)
            cv2.setMouseCallback("Visualizer", self.touch_event)

            matrix = cv2.resize(self.content.frame, dsize=(64, 32), interpolation=cv2.INTER_LINEAR)
            # matrix_preview = cv2.resize(matrix, dsize=(640, 320), interpolation=cv2.INTER_NEAREST)
            # cv2.imshow("preview", matrix_preview)

            self.__call(matrix)
            self.prev_touch_pos = self.touch_pos
            cv2.waitKey(30)

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()
        self.thread = None

    def set_content(self, content):
        self.content = content

    def set_object_image(self, img):
        self.object_image = cv2.resize(img, dsize=(self.frame_size[1], self.frame_size[0]))

    def touch_event_from_analyzer(self, event, x, y):
        x_s = 0
        y_s = 0
        if event == cv2.EVENT_MOUSEMOVE:
            x_s = int(x * self.frame_size[0])
            y_s = int(y * self.frame_size[1])

        self.touch_event(event, x_s, y_s)

    def touch_event(self, event, x, y, flags=None, param=None):
        if event == cv2.EVENT_MOUSEMOVE:
            if self.prev_touch_pos == (-1, -1):
                self.prev_touch_pos = (x, y)
            self.touch_pos = (x, y)

        if event == cv2.EVENT_RBUTTONDOWN:
            self.content.touch_event(event)
            self.is_touch = True
        if event == cv2.EVENT_RBUTTONUP:
            self.content.touch_event(event)
            self.is_touch = False
            self.prev_touch_pos = (-1, -1)
            self.touch_pos = (-1, -1)

    def init_midi(self):
        midi.init()
        i_num = midi.get_count()
        for i in range(i_num):
            print(i)
            print(midi.get_device_info(i))

        self.midi_out = midi.Output(midi.get_default_output_id())
        self.midi_out.set_instrument(40)


class DemoContents(metaclass=ABCMeta):

    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.frame = None
        self.name = ""

        self.clear_frame()

    def touch_event(self, event):
        if event == cv2.EVENT_RBUTTONDOWN:
            self.touch_down()
        elif event == cv2.EVENT_RBUTTONUP:
            self.touch_up()

    def clear_frame(self):
        self.frame = np.zeros((self.visualizer.frame_size[0], self.visualizer.frame_size[1], 3), np.uint8)

    @abstractmethod
    def draw(self):
        pass

    def touch_down(self):
        pass

    def touch_up(self):
        pass
