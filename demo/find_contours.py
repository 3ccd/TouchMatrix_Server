import random
import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2
import numpy as np


class FindContours(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Find Contours"

    def draw(self):
        obj_img = self.visualizer.get_object_image(True)
        contours, hierarchy = cv2.findContours(
            obj_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_img = np.zeros_like(obj_img)
        cv2.drawContours(contours_img, contours, -1, color=(0, 0, 255), thickness=10)

        self.frame = cv2.resize(contours_img, dsize=(self.visualizer.frame_size[1], self.visualizer.frame_size[0]))


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    ocr = FindContours(vis)
    vis.set_content(ocr)
    vis.start()
    time.sleep(10.0)
    vis.stop()
