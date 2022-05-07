import time
from abc import ABC

from demo.visualizer import DemoContents, Visualizer


class TouchSend(DemoContents, ABC):

    def __init__(self, visualizer, client):
        super().__init__(visualizer)
        self.name = "Touch Send"
        self.client = client

        self.frame_available = False

    def draw(self):
        if self.visualizer.is_touch:
            self.client.send_message("/touch",
                                     [int(self.visualizer.touch_pos[0] / 10),
                                      int(self.visualizer.touch_pos[1] / 10)])

    def touch_up(self):
        self.client.send_message("/touch", [-1, -1])

    def touch_down(self):
        pass

    def content_changed(self):
        self.clear_frame()


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = TouchSend(vis, None)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
