import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2
import numpy as np

import requests


class FindContours(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Car Controller"
        self.touch_rec = [0, 0]
        self.status = 0

    def draw(self):
        self.clear_frame()
        if not self.visualizer.is_touch:
            return

        y = int(self.visualizer.frame_size[0] / 2)
        if self.status == 1:
            cv2.arrowedLine(self.frame, (500, y), (100, y), (255, 255, 255), thickness=20,
                            tipLength=0.5)
        elif self.status == 2:
            cv2.arrowedLine(self.frame, (100, y), (500, y), (255, 255, 255), thickness=20,
                            tipLength=0.5)

        control = self.touch_rec[0] - self.visualizer.touch_pos[0]
        if -20 < control < 20 and self.status != 0:
            print("stop")
            requests.get("http://192.168.32.2/F")
            self.status = 0
        elif control > 20 and self.status != 1:
            print("forward")
            requests.get("http://192.168.32.2/R")
            self.status = 1
        elif control < -20 and self.status != 2:
            requests.get("http://192.168.32.2/G")
            print("back")
            self.status = 2

    def touch_down(self):
        self.touch_rec = self.visualizer.touch_pos
        self.status = 0
        print("down")

    def touch_up(self):
        print("stop")
        requests.get("http://192.168.32.2/F")
        self.status = 0


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    ocr = FindContours(vis)
    vis.set_content(ocr)
    vis.start()
    time.sleep(10.0)
    vis.stop()
