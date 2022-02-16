import time
from abc import ABC
from visualizer import DemoContents, Visualizer
import cv2


class OCR(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "OCR"

    def draw(self):
        if self.visualizer.prev_touch_pos is None:
            return
        cv2.line(self.frame, self.visualizer.touch_pos, self.visualizer.prev_touch_pos, (255, 255, 255), thickness=2)


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    ocr = OCR(vis)
    vis.set_content(ocr)
    vis.start()
    time.sleep(10.0)
    vis.stop()
