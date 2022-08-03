import math
import numpy as np
import cv2


class Object:

    def __init__(self, point, oid=-1):
        self.point = point
        self.oid = oid
        self.x = point[1]
        self.y = point[0]

    def set_id(self, oid):
        self.oid = oid


class Touch(Object):

    def __init__(self, point, oid=-1):
        super(Touch, self).__init__(point, oid)


class Blob(Object):

    def __init__(self, point, point1, point2, shape,  oid=-1):
        super(Blob, self).__init__(point, oid)
        self.point1 = point1
        self.point2 = point2
        self.shape = np.zeros([16, 16], dtype=np.uint8)
        self.set_shape(shape)

    def set_shape(self, shape):
        cv2.resize(shape, dsize=self.shape.shape, dst=self.shape)


class ObjTracker:

    EVENT_OBJ_UPDATE = 1
    EVENT_OBJ_DELETE = 2

    CONFIG_THRESHOLD = 1
    CONFIG_DETECTION_MAX = 2

    def __init__(self):
        self.touch_dict = {}        # idとオブジェクトの辞書
        self.updated_id = {}        # 単一フレームで座標が更新されたid（毎フレーム初期化）
        self.threshold = 40         # 同一オブジェクトと見なす距離
        self.max_detection = 10     # 最大検出数
        self.event_callback = None

    def config(self, cid, value):
        if cid is self.CONFIG_THRESHOLD:
            self.threshold = value
        elif cid is self.CONFIG_DETECTION_MAX:
            self.max_detection = value

    def set_callback(self, callback):
        self.event_callback = callback

    def call_event(self, obj, event):
        if self.event_callback is None:
            return

        self.event_callback(obj, event)

    def add_point(self, obj):
        """
        空きIDを検索し，挿入する
        :param obj: タッチ座標
        :return: 割り当てたID
        """
        for i in range(self.max_detection):
            if i not in self.touch_dict:
                self.update_point(obj, i)
                return i
        return -1

    def get_detected(self):
        for i in range(self.max_detection):
            if i not in self.touch_dict:
                return i - 1
        return self.max_detection

    def get_objects(self):
        return self.touch_dict

    def update_point(self, obj, num):
        """
        タッチ座標を更新する
        :param obj: 検出オブジェクト
        :param num: ID
        :return: None
        """
        obj.set_id(num)
        self.touch_dict[num] = obj
        self.updated_id[num] = True
        self.call_event(obj, self.EVENT_OBJ_UPDATE)

    def end_frame(self):
        """
        更新されなかったIDを解放
        :return: None
        """
        clear_ids = []
        for i in range(self.max_detection):
            if i not in self.updated_id and i in self.touch_dict:
                self.touch_dict.pop(i)
                self.call_event((-1, -1), self.EVENT_OBJ_DELETE)
                clear_ids.append(i)
        self.updated_id.clear()
        return clear_ids

    def update(self, obj):
        """
        タッチ座標を検索し，新規であれば挿入
        タッチ検出の最大値を超えれば-1が返る
        :param obj: 検出オブジェクト
        :return: ID
        """
        min_id = -1
        min_distance = 1000
        for num, p in self.touch_dict.items():
            distance = math.sqrt(((obj.x - p.x) ** 2) + ((obj.y - p.y) ** 2))
            if distance < self.threshold and\
                    distance < min_distance and\
                    num not in self.updated_id:
                # 閾値以下で，最短距離のタッチ座標を検索
                min_distance = distance
                min_id = num

        if min_id == -1:
            # 見つからなかった場合は新規に挿入
            num = self.add_point(obj)
            return num
        else:
            # 見つかった場合は更新
            self.update_point(obj, min_id)
            return min_id