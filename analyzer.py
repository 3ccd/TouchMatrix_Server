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
    peaks_index = np.where((tmp.mask != True))

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
    return tmp


class Analyzer(threading.Thread):

    def __init__(self, tm, calibration):
        """
        アナライザクラスのコンストラクタ
        :param tm: TmFrameインスタンス
        :param calibration: Calibrationインスタンス
        """
        super().__init__(target=self.__call)

        self.__tm_frame = tm
        self.calibration = calibration

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

        self.touch_callback = None
        self.draw_callback = None
        self.touch_status = False

        self.latest_data = None
        self.touch_tracker = TouchTracker()

    def __del__(self):
        self.stop()

    def stop(self):
        self.running = False
        self.join()

    def set_touch_callback(self, callback):
        self.touch_callback = callback

    def set_draw_callback(self, callback):
        self.draw_callback = callback

    def _call_draw_event(self, labels):
        self.draw_callback(labels)

    def _call_object_event(self, event, position=(0, 0)):
        if self.touch_callback is None:
            return

        if event == cv2.EVENT_MOUSEMOVE:
            y = position[0] / self.plot_size[0]
            x = position[1] / self.plot_size[1]
            self.touch_callback(event, y, x)
        else:
            self.touch_callback(event, 0, 0)

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
        sensor_sum = self.filter_buffer.sum(axis=0) / self.filter_buffer.shape[0]
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

        ret, tmp = cv2.threshold(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy],
                                 float(self.threshold), 1.0, cv2.THRESH_BINARY)
        peaks = detect_touch(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy])
        obj = detect_object(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy])

        color = np.zeros((tmp.shape[0], tmp.shape[1], 3), np.uint8)  # 3chの画像を生成
        cv2.cvtColor(obj.astype(np.uint8), cv2.COLOR_GRAY2RGB, color)  # RGB画像へ変換

        # retval, labels, stats, centroids = cv2.connectedComponentsWithStats(obj)  # Labeling

        color_labels = color
        if len(peaks[0]) != self.plot_size[0] * self.plot_size[1]:
            for i in range(len(peaks[0])):
                num = self.touch_tracker.update_touch((peaks[1][i], peaks[0][i]))
                if num != -1:
                    cv2.drawMarker(color, (peaks[1][i], peaks[0][i]), color_list[num], markerType=cv2.MARKER_CROSS,
                                   markerSize=20, thickness=2,
                                   line_type=cv2.LINE_8)
            self.touch_tracker.end_frame()

        self._call_draw_event(color_labels)

        self.disp_img = color_labels
        self.disp2_img = (self.plot_img * 255).astype(np.uint8)
        self.disp3_img = cv2.resize(calc * 255, (self.plot_size[1], self.plot_size[0]), interpolation=cv2.INTER_NEAREST)


class TouchTracker:

    EVENT_TOUCH_UPDATE = 1
    EVENT_TOUCH_UP = 2

    def __init__(self):
        self.touch_dict = {}
        self.updated_id = {}
        self.threshold = 40
        self.max_detection = 10
        self.touch_callback = None

    def call_touch_event(self, tid, point, event):
        if self.touch_callback is None:
            return

        self.touch_callback(tid, point, event)

    def add_point(self, point):
        """
        空きIDを検索し，挿入する
        :param point: タッチ座標
        :return: 割り当てたID
        """
        for i in range(self.max_detection):
            if i not in self.touch_dict:
                self.update_point(point, i)
                return i
        return -1

    def update_point(self, point, num):
        """
        タッチ座標を更新する
        :param point: タッチ座標
        :param num: ID
        :return: None
        """
        self.touch_dict[num] = point
        self.updated_id[num] = True
        self.call_touch_event(num, point, self.EVENT_TOUCH_UPDATE)

    def end_frame(self):
        """
        更新されなかったIDを解放
        :return: None
        """
        clear_ids = []
        for i in range(self.max_detection):
            if i not in self.updated_id and i in self.touch_dict:
                self.touch_dict.pop(i)
                self.call_touch_event(i, (-1, -1), self.EVENT_TOUCH_UP)
                clear_ids.append(i)
        self.updated_id.clear()
        return clear_ids

    def update_touch(self, point):
        """
        タッチ座標を検索し，新規であれば挿入
        タッチ検出の最大値を超えれば-1が返る
        :param point: タッチ座標
        :return: ID
        """
        min_id = -1
        min_distance = 1000
        for num, p in self.touch_dict.items():
            distance = math.sqrt(((point[0] - p[0]) ** 2) + ((point[1] - p[1]) ** 2))
            if distance < self.threshold and\
                    distance < min_distance and\
                    num not in self.updated_id:
                # 閾値以下で，最短距離のタッチ座標を検索
                min_distance = distance
                min_id = num

        if min_id == -1:
            # 見つからなかった場合は新規に挿入
            num = self.add_point(point)
            return num
        else:
            # 見つかった場合は更新
            self.update_point(point, min_id)
            return min_id
