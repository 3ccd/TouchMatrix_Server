import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2


class ObjectDetection(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Object Detection"

    def draw(self):
        self.frame = self.visualizer.get_object_image(False)

    def touch_up(self):
        pass

    def touch_down(self):
        pass


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = ObjectDetection(vis)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
