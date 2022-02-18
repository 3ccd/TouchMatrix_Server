import time
from abc import ABCMeta, abstractmethod
import threading
import numpy as np
import cv2


class Visualizer:

    def __init__(self, size):
        self.thread = None
        self.running = False            # スレッド処理の状態
        self.content = None             # 表示するコンテンツ

        self.frame_size = size          # 描画サイズ
        self.is_touch = False           # タッチしているか
        self.touch_pos = (-1, -1)       # タッチ座標
        self.prev_touch_pos = (-1, -1)  # 前回のタッチ座標

    def run(self):
        while self.running:
            if self.content is None:
                time.sleep(2)
                continue

            self.content.draw()

            cv2.imshow("Visualizer", self.content.frame)
            cv2.setMouseCallback("Visualizer", self.touch_event)

            matrix = cv2.resize(self.content.frame, dsize=(64, 32), interpolation=cv2.INTER_LINEAR)
            matrix_preview = cv2.resize(matrix, dsize=(640, 320), interpolation=cv2.INTER_NEAREST)
            cv2.imshow("preview", matrix_preview)

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

    def touch_event_from_analyzer(self, event, x, y):
        if event == cv2.EVENT_MOUSEMOVE:
            self.is_touch = True
            x_s = int(x * self.frame_size[0])
            y_s = int(y * self.frame_size[1])
            if self.prev_touch_pos == (-1, -1):
                self.prev_touch_pos = (x_s, y_s)
            self.touch_pos = (x_s, y_s)

        if event == cv2.EVENT_RBUTTONDOWN:
            self.is_touch = True
        if event == cv2.EVENT_RBUTTONUP:
            self.is_touch = False
            self.prev_touch_pos = (-1, -1)
            self.touch_pos = (-1, -1)

    def touch_event(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            if self.prev_touch_pos == (-1, -1):
                self.prev_touch_pos = (x, y)
            self.touch_pos = (x, y)

        if event == cv2.EVENT_RBUTTONDOWN:
            self.is_touch = True
        if event == cv2.EVENT_RBUTTONUP:
            self.is_touch = False
            self.prev_touch_pos = (-1, -1)
            self.touch_pos = (-1, -1)


class DemoContents(metaclass=ABCMeta):

    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.frame = None
        self.name = ""

        self.clear_frame()

    def clear_frame(self):
        self.frame = np.zeros((self.visualizer.frame_size[0], self.visualizer.frame_size[1], 3), np.uint8)

    @abstractmethod
    def draw(self):
        pass
