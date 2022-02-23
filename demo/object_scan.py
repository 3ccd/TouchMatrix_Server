import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2


class ObjectScan(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Object Scan"

        self.scan_line = 0

    def draw(self):
        self.frame = self.visualizer.object_image.copy()

        cv2.line(self.frame, (self.scan_line, 0), (self.scan_line, self.visualizer.frame_size[0]), (0, 255, 0),
                 thickness=20)

        self.scan_line = self.scan_line + 2
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
