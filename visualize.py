import numpy as np
import cv2

from tracker import ObjTracker


color_list = [
    (255, 255,   0),
    (255,   0, 255),
    (  0, 255, 255),
    (255,   0,   0),
    (  0, 255,   0),
    (  0,   0, 255),
    (255, 128, 128),
    (128, 128, 255),
    (128, 255, 128),
    ( 64, 128, 255),
]


def visualize(img, tracker):
    if not isinstance(tracker, ObjTracker):
        return

    t_dict = tracker.get_objects()

    for key, obj in t_dict:
        cv2.drawMarker(img, obj.point, color_list[key])


