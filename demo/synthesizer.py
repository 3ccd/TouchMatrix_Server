import time
from abc import ABC
from demo.visualizer import DemoContents, Visualizer
import cv2


class Synthesizer(DemoContents, ABC):

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.name = "Synthesizer"

        self.note = 64
        self.playing = False

    def draw(self):
        self.frame = self.frame / 1.3
        if not self.visualizer.is_touch:
            return
        cv2.line(self.frame, self.visualizer.touch_pos, self.visualizer.prev_touch_pos, (255, 255, 255), thickness=30)
        self.note_change(int(20 * (self.visualizer.touch_pos[0] / self.visualizer.frame_size[0])) + 50)

    def note_change(self, note):
        if self.note == note:
            return
        self.visualizer.midi_out.note_off(self.note)
        self.visualizer.midi_out.note_on(note, 100)
        self.note = note

    def touch_up(self):
        self.playing = False
        self.visualizer.midi_out.note_off(self.note)

    def touch_down(self):
        self.playing = True
        self.visualizer.midi_out.note_on(self.note, 100)


if __name__ == "__main__":
    vis = Visualizer((320, 640))
    con = Synthesizer(vis)
    vis.set_content(con)
    vis.start()
    time.sleep(5.0)
    vis.stop()
