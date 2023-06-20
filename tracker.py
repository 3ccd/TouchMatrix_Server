import math
import time

import numpy as np
import cv2


class Object:

    def __init__(self, point, oid=-1):
        self.point = (int(point[0]), int(point[1]))
        self.oid = oid
        self.x = point[1]
        self.y = point[0]
        self.timestamp = 0.0

    def set_id(self, oid):
        self.oid = oid


class Touch(Object):

    def __init__(self, point, oid=-1):
        super(Touch, self).__init__(point, oid)


class Blob(Object):

    def __init__(self, point, point1, point2, shape,  oid=-1):
        super(Blob, self).__init__(point, oid)
        self.point1 = (int(point1[0]), int(point1[1]))
        self.point2 = (int(point2[0]), int(point2[1]))
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
        self.candidate = {}         # 追加予定のオブジェクト
        self.updated_id = {}        # 候補に追加した時刻．IDとタイムスタンプのセット
        self.smoothing = {}         # smoothing coordinate

        self.lifetime_raising = 4   # 昇格するライフタイム
        self.cleanup_threshold = 0.2
        self.threshold = 30         # 同一オブジェクトと見なす距離
        self.max_detection = 10     # 最大検出数
        self.event_callback = None

        self.fixed_timestamp = 0.0

    def config(self, cid, value):
        if cid is self.CONFIG_THRESHOLD:
            self.threshold = value
        elif cid is self.CONFIG_DETECTION_MAX:
            self.max_detection = value

    def set_callback(self, callback):
        self.event_callback = callback

    def __call_event(self, obj, event):
        if self.event_callback is None:
            return

        self.event_callback(obj, event)

    def get_object_smoothing(self):
        return self.smoothing.copy()

    def get_objects(self):
        return self.touch_dict.copy()

    def __search_next_index(self, dic):
        """
        空きIDを検索
        :param dic: 辞書
        :return: 割り当てたID
        """
        for i in range(self.max_detection):
            if i not in dic:
                return i
        return -1

    def __update_point(self, obj, num):
        """
        タッチ座標を更新する
        :param obj: 検出オブジェクト
        :param num: ID
        :return: None
        """
        obj.set_id(num)
        obj.timestamp = self.fixed_timestamp
        self.touch_dict[num] = obj
        self.__call_event(obj, self.EVENT_OBJ_UPDATE)

    def __add_object(self, obj, dic):
        index = self.__search_next_index(dic)
        obj.set_id(index)
        obj.timestamp = self.fixed_timestamp

        dic[index] = obj
        return index

    def end_frame(self):
        """
        フレーム終了の時間を記録
        :return: None
        """
        self.__cleanup(self.candidate)
        cleaned = self.__cleanup(self.touch_dict, self.lifetime_raising)
        for obj in cleaned:
            self.__call_event(obj, self.EVENT_OBJ_DELETE)
            del obj

        prev_timestamp = self.fixed_timestamp
        self.fixed_timestamp = time.time()

        return prev_timestamp

    def __cleanup(self, dic, threshold=None):
        cleaned = []
        cleaned_id = []
        for num, obj in dic.items():
            # threshold　が指定なければ即削除
            if threshold is None:
                if self.fixed_timestamp != obj.timestamp:
                    cleaned.append(obj)
                    cleaned_id.append(num)
            else:
                elapsed_time = self.fixed_timestamp - obj.timestamp
                if elapsed_time > self.cleanup_threshold:
                    cleaned.append(obj)
                    cleaned_id.append(num)

        for key in cleaned_id:
            dic.pop(key)
        return cleaned

    def __search(self, obj, dic):
        min_id = -1
        min_distance = 1000
        for num, p in dic.items():
            distance = math.sqrt(((obj.x - p.x) ** 2) + ((obj.y - p.y) ** 2))
            if distance < self.threshold and \
                    distance < min_distance:
                # 閾値以下で，最短距離のタッチ座標を検索
                min_distance = distance
                min_id = num

        return min_id

    def update(self, obj):
        """
        タッチ座標を検索し，新規であれば挿入
        タッチ検出の最大値を超えれば-1が返る
        :param obj: 検出オブジェクト
        :return: ID
        """
        assert isinstance(obj, Object), "track error"

        # search candidate
        candidate_id = self.__search(obj, self.candidate)
        # search objects in detection
        detected_id = self.__search(obj, self.touch_dict)

        # 候補でも，検出中でもない
        if candidate_id == -1 and detected_id == -1:
            index = self.__search_next_index(self.updated_id)
            self.updated_id[index] = 1
            self.__add_object(obj, self.candidate)

        # 候補で，まだ採用されていない
        elif candidate_id != -1 and detected_id == -1:
            # 採用
            if self.updated_id[candidate_id] > self.lifetime_raising:
                self.candidate.pop(candidate_id)
                self.updated_id.pop(candidate_id)
                self.__add_object(obj, self.touch_dict)
            # 候補をアップデート
            else:
                self.candidate[candidate_id] = obj
                self.updated_id[candidate_id] += 1

        # 検出中
        elif candidate_id == -1 and detected_id != -1:
            self.__update_point(obj, detected_id)
