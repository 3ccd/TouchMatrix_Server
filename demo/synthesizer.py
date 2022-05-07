import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2


class Synthesizer(DemoContents, ABC):

    def __init__(self, visualizer, client):
        super().__init__(visualizer)
        self.name = "Synthesizer"

        self.client = client

        self.note = 64
        self.playing = False
        self.frame_available = False

    def draw(self):
        self.frame = self.frame / 1.3
        if not self.visualizer.is_touch:
            return
        cv2.line(self.frame, self.visualizer.touch_pos, self.visualizer.prev_touch_pos, (255, 255, 255), thickness=30)
        self.client.send_message("/synth/note",
                                 [int(self.visualizer.touch_pos[0] / self.visualizer.frame_size[1] * 127)])
        self.client.send_message("/synth/pitch",
                                 [int(self.visualizer.touch_pos[1] / self.visualizer.frame_size[0] * 127)])

    def touch_up(self):
        self.playing = False

    def touch_down(self):
        self.playing = True


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = Synthesizer(vis)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
