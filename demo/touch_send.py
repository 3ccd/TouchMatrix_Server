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
        pass

    def touch_up(self, tid):
        self.client.send_message("/touch/" + tid, [-1, -1])

    def touch_down(self, tid):
        pass

    def touch_update(self, tid, point):
        self.client.send_message("/touch" + tid, [int(point[0] / 10), int(point[1] / 10)])

    def content_changed(self):
        self.clear_frame()


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = TouchSend(vis, None)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
