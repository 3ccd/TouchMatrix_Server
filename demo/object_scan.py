import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2
import numpy as np


class ObjectScan(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Object Scan"

        self.scan_line = 0
        self.tmp_frame = np.zeros_like(self.frame)

    def draw(self):
        obj_img = self.visualizer.get_object_image(False)

        self.tmp_frame[:, self.scan_line:self.scan_line+1, 2] = obj_img[:, self.scan_line:self.scan_line+1, 2]
        self.frame = self.tmp_frame.copy()
        cv2.line(self.frame, (self.scan_line, 0), (self.scan_line, self.visualizer.frame_size[0]), (0, 255, 0),
                 thickness=20)

        self.scan_line = self.scan_line + 1
        if self.scan_line > self.visualizer.frame_size[1]:
            self.scan_line = 0

    def touch_up(self):
        pass

    def touch_down(self):
        pass


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = ObjectScan(vis)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
