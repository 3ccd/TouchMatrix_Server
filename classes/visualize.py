import numpy as np
import cv2

from classes.tracker import Touch, Blob


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


def visualize(img, t_dict, offset=(0, 0)):
    for key, obj in t_dict.items():
        if isinstance(obj, Touch):
            cv2.drawMarker(img, (obj.point[0]+offset[0], obj.point[1] + offset[1]), color_list[key], markerSize=30,
                           thickness=2)
        if isinstance(obj, Blob):
            cv2.rectangle(img,
                          (obj.point1[0]+offset[0], obj.point1[1] + offset[1]),
                          (obj.point2[0]+offset[0], obj.point2[1] + offset[1]),
                          color_list[key]
                          )


