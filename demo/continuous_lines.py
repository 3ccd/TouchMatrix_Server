import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2


class ContinuousLines(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Continuous Lines"

    def draw(self):
        if not self.visualizer.is_touch:
            return
        cv2.line(self.frame, self.visualizer.touch_pos, self.visualizer.prev_touch_pos, (255, 255, 255), thickness=10)

    def touch_up(self):
        pass

    def touch_down(self):
        pass

    def content_changed(self):
        self.clear_frame()


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = ContinuousLines(vis)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
