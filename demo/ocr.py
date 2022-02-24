import random
import time
from abc import ABC
from visualizer import DemoContents, Visualizer
import cv2
import numpy as np


class OCR(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Cool Graphics"

        self.timing_counter = 0

    def draw(self):
        self.frame = (self.frame / 1.02).astype(np.uint8)
        if self.timing_counter > 6:
            cv2.circle(img=self.frame,
                       center=(random.randint(0, self.visualizer.frame_size[1]),
                               random.randint(0, self.visualizer.frame_size[0])),
                       radius=random.randint(50, 100),
                       color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                       thickness=-1)
            self.timing_counter = 0
        self.timing_counter += 1


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    ocr = OCR(vis)
    vis.set_content(ocr)
    vis.start()
    time.sleep(10.0)
    vis.stop()
