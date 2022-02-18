import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2
import math


class TurnTable(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Turn Table"

        self.angle_l = 0.0
        self.angle_r = 0.0

        self.p_angle_l = None
        self.p_angle_r = None

    def draw(self):
        self.clear_frame()

        cv2.circle(self.frame, (160, 160), 150, (255, 255, 255), thickness=-1)
        cv2.circle(self.frame, (480, 160), 150, (255, 255, 255), thickness=-1)
        cv2.circle(self.frame, (160, 160), 50, (0, 0, 0), thickness=-1)
        cv2.circle(self.frame, (480, 160), 50, (0, 0, 0), thickness=-1)

        indicator_l = (math.floor(math.cos(self.angle_l) * 100 + 160),
                       math.floor(math.sin(self.angle_l) * 100 + 160))
        cv2.circle(self.frame, indicator_l, 40, (0, 0, 0), thickness=-1)

        indicator_r = (math.floor(math.cos(self.angle_r) * 100 + 480),
                       math.floor(math.sin(self.angle_r) * 100 + 160))
        cv2.circle(self.frame, indicator_r, 40, (0, 0, 0), thickness=-1)

        if self.visualizer.touch_pos[0] < 320 and self.visualizer.is_touch:
            angle = math.atan2(self.visualizer.touch_pos[1] - 160, self.visualizer.touch_pos[0] - 160)
            if self.p_angle_l is None:
                self.p_angle_l = angle
            control = angle - self.p_angle_l
            self.angle_l = self.angle_l + control
            self.p_angle_l = angle
        else:
            self.angle_l = self.angle_l + 0.1
            self.p_angle_l = None

        if self.visualizer.touch_pos[0] > 320 and self.visualizer.is_touch:
            angle = math.atan2(self.visualizer.touch_pos[1] - 160, self.visualizer.touch_pos[0] - 480)
            if self.p_angle_r is None:
                self.p_angle_r = angle
            control = angle - self.p_angle_r
            self.angle_r = self.angle_r + control
            self.p_angle_r = angle
        else:
            self.angle_r = self.angle_r + 0.1
            self.p_angle_r = None

        if self.angle_l > 360:
            self.angle_l = 0.0
        if self.angle_r > 360:
            self.angle_r = 0.0


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    tt = TurnTable(vis)
    vis.set_content(tt)
    vis.start()
    time.sleep(10.0)
    vis.stop()
