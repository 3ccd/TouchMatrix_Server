import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2


class ContinuousLines(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Continuous Lines"

    def draw(self):
        if self.visualizer.prev_touch_pos is None:
            return
        cv2.line(self.frame, self.visualizer.touch_pos, self.visualizer.prev_touch_pos, (255, 255, 255), thickness=10)


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = ContinuousLines(vis)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()