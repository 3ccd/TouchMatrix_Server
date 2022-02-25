import time
from abc import ABC

import numpy as np

from demo.visualizer import DemoContents, Visualizer
import cv2


class ContinuousLines(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Continuous Lines"
        self.tmp_frame = np.zeros_like(self.frame)

    def draw(self):
        self.clear_frame()
        self.frame = self.tmp_frame.copy()
        if not self.visualizer.is_touch:
            return
        cv2.line(self.tmp_frame, self.visualizer.touch_pos, self.visualizer.prev_touch_pos, (255, 255, 255),
                 thickness=10)
        cv2.line(self.frame, (self.visualizer.touch_pos[0], 0),
                 (self.visualizer.touch_pos[0], self.visualizer.frame_size[1]), (0, 0, 255), thickness=10)
        cv2.line(self.frame, (0, self.visualizer.touch_pos[1]),
                 (self.visualizer.frame_size[1], self.visualizer.touch_pos[1]), (0, 0, 255), thickness=10)

    def touch_up(self):
        pass

    def touch_down(self):
        pass

    def content_changed(self):
        self.clear_frame()
        self.tmp_frame = np.zeros_like(self.frame)


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = ContinuousLines(vis)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
