import math
import time
import threading
import numpy as np
import cv2
from scipy.ndimage import maximum_filter


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


def gauss2d(size, sd):
    """
    ガウス分布のグラデーション画像の生成
    :param size: 画像の縦横解像度
    :param sd: 標準偏差
    :return: 画像のnumpy配列
    """
    grad = np.zeros((size, size))
    for i in range(size):
        for j in range(size):
            x = i - size / 2
            y = j - size / 2
            gx = (-0.5) * pow((x / sd), 2)
            gy = (-0.5) * pow((y / sd), 2)
            grad[i, j] = math.exp(gx + gy)
    return grad


def insert_led():
    """
    センサ配列に対して千鳥格子状にブランクを差し込む
    :return: numpy配列
    """
    pos = []
    for i in range(11):
        pos.extend(range((i % 2) + (i * 11), (i + 1) * 11 + (i % 2), 1))
    return pos


def draw_centroids(src_img, centroids):
    """
    ラベリング結果の重心を画像に描画する
    :param src_img: 描画元の画像
    :param centroids: 重心が格納された配列
    :return: 描画後の画像
    """
    centroids_img = src_img
    for coordinate in centroids[1:]:
        center = (int(coordinate[0]), int(coordinate[1]))
        cv2.drawMarker(centroids_img, center, (255, 0, 0), markerType=cv2.MARKER_CROSS,
                       markerSize=20, thickness=2,
                       line_type=cv2.LINE_8)
    return centroids_img


def detect_touch(img):
    """
    グラデーション画像の局所最大値を計算
    :param img: グラデーション画像
    :return: 局所最大値を持つ画素の座標
    """
    tmp_img = img.copy()
    tmp_img[tmp_img < 0.2] = 0.0        # ノイズの除去

    local_max = maximum_filter(tmp_img, footprint=np.ones((10, 10)), mode="constant")
    detected_peaks = np.ma.array(tmp_img, mask=~(tmp_img == local_max))

    tmp = np.ma.array(detected_peaks, mask=~(detected_peaks >= detected_peaks.max() * 0.2))
    peaks_index = np.where((not tmp.mask))

    touchs = []
    if len(peaks_index[0]) > 20:
        for i in range(len(peaks_index[0])):
            touchs[i] = Touch(peaks_index[1][i], peaks_index[0][i])

    return peaks_index


def detect_object(img):
    """
    判別分析を用いた二値化
    :param img: グラデーション画像
    :return: 二値化画像
    """
    tmp_img = img.copy()
    tmp_img[tmp_img < 0.2] = 0.0

    tmp8bit = (tmp_img * 255).astype(np.uint8)  # 8bitのスケールへ変換
    ret, tmp = cv2.threshold(tmp8bit, 0, 255, cv2.THRESH_OTSU)

    retval, labels, stats, centroids = cv2.connectedComponentsWithStats(tmp)  # Labeling

    # blobを抽出
    blobs = []
    for i in range(1, len(centroids)):
        coordinate = stats[i]
        center = centroids[i]
        left_top = (coordinate[0], coordinate[1])
        right_bottom = (coordinate[0] + coordinate[2], coordinate[1] + coordinate[3])
        shape = tmp[left_top[1]:left_top[1] + right_bottom[1], left_top[0]:left_top[0] + right_bottom[0]]
        blobs[i] = Blob(center, left_top, right_bottom, shape)

    return blobs


class Analyzer(threading.Thread):

    def __init__(self, tm, calibration, touch_tracker, blob_tracker):
        """
        アナライザクラスのコンストラクタ
        :param tm: TmFrameインスタンス
        :param calibration: Calibrationインスタンス
        """
        super().__init__(target=self.__call)

        self.__tm_frame = tm
        self.calibration = calibration
        self.touch_tracker = touch_tracker
        self.blob_tracker = blob_tracker

        self.running = True

        self.curve_type = 0
        self.threshold = 0.3
        self.gamma = 0.7

        self.led_insert_pos = insert_led()

        self.plot_size = (160, 320)
        self.grad_size = 100
        self.sd = 16
        self.over_scan = 60

        self.filter_buffer = np.zeros((3, 121))

        self.grad_img = None
        self.plot_img = None
        self.disp_img = None
        self.disp2_img = None
        self.disp3_img = None

        self.set_grad(self.grad_size, 16)

        self.latest_data = None

    def __del__(self):
        self.stop()

    def stop(self):
        self.running = False
        self.join()

    def set_grad(self, size, sd):
        self.grad_size = size
        self.sd = sd
        self.grad_img = gauss2d(size, sd)

    def set_curve(self, c_type):
        self.curve_type = c_type

    def set_threshold(self, threshold):
        self.threshold = threshold

    def set_curve_param(self, gamma):
        self.gamma = gamma

    def update_filter(self, sensor_data):
        """
        移動平均フィルタ
        :param sensor_data:
        :return:
        """
        self.filter_buffer = np.roll(self.filter_buffer, -1, axis=0)
        self.filter_buffer[-1, :] = sensor_data
        sensor_sum = self.filter_buffer.sum(axis=0) / (self.filter_buffer.shape[0] - 1)
        return sensor_sum

    def __call(self):
        """
        処理ループ
        :return: None
        """
        while self.running:
            self.__loop()
            time.sleep(0.02)

    def __clear_plot(self):
        """
        合成画像を初期化
        :return: None
        """
        extra_px = self.over_scan * 2
        self.plot_img = np.zeros((self.plot_size[0] + extra_px, self.plot_size[1] + extra_px))

    def __plot(self, sensor_data):
        """
        グラデーション画像にセンサ値をかけ合わせたものを合成
        :param sensor_data: センサ値
        :return: None
        """
        self.__clear_plot()
        sens_height, sens_width = sensor_data.shape[:2]
        xp = int(self.plot_size[1] / (sens_width - 1))  # step x
        yp = int(self.plot_size[0] / (sens_height - 1))  # step y
        grad_h = int(self.grad_size / 2)

        for hi in range(sens_height):
            for wi in range(sens_width):
                y = (hi * yp) + self.over_scan
                x = (wi * xp) + self.over_scan
                tmp = (self.grad_img * sensor_data[hi, wi])
                self.plot_img[y - grad_h:y + grad_h, x - grad_h:x + grad_h] += tmp

        self.plot_img[self.plot_img > 1.0] = 1.0

    def __loop(self):
        if not self.calibration.is_calibration_available():
            return

        tmp = self.calibration.get_calibrated_data()
        calc = self.update_filter(tmp)

        # tone curve
        if self.curve_type == 1:
            calc = (calc ** self.gamma)
        if self.curve_type == 2:
            calc = (np.sin(np.pi * (calc - 0.1)) + 1) / 2
        if self.curve_type == 3:
            calc = (calc * 3)
        calc[calc > 1.0] = 1.0

        calc = np.insert(calc, self.led_insert_pos, 0)
        calc = np.reshape(calc, (11, 22))

        self.__plot(calc)

        tmpx = self.over_scan + self.plot_size[0]
        tmpy = self.over_scan + self.plot_size[1]

        touchs = detect_touch(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy])
        blobs = detect_object(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy])

        for touch in touchs:
            self.touch_tracker.update(touch)
        self.touch_tracker.end_frame()

        for blob in blobs:
            self.blob_tracker.update(blob)
        self.blob_tracker.end_frame()


class Object:

    def __init__(self, point, oid=-1):
        self.point = point
        self.oid = oid

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
            distance = math.sqrt(((obj.x - p[0]) ** 2) + ((obj.y - p[1]) ** 2))
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
