import math
import time
import threading
import numpy as np
import cv2
from scipy.ndimage import maximum_filter

from classes.tracker import Touch, Blob


def intr(sensor_data):
    pos = np.zeros((16, 16))
    line_start_x = [5, 4, 4, 3, 3, 2, 2, 1, 1, 0, 0]
    line_start_y = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5]
    for i in range(121):
        line = int(i / 11)
        cnt = i % 11
        pos[line_start_x[line] + cnt, line_start_y[line] + cnt] = sensor_data[i]

    return pos


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


def detect_touch(img, mask_blobs, threshold=0.1):
    """
    グラデーション画像の局所最大値を計算
    :param img: グラデーション画像
    :param threshold: threshold
    :return: 局所最大値を持つ画素の座標
    """
    tmp_img = img.copy()
    for blob in mask_blobs:
        tmp_img[blob.point1[1]:blob.point2[1], blob.point1[0]:blob.point2[0]] = 0.0
    tmp_img[tmp_img > 0.9] = 0.0
    tmp_img[tmp_img < 0.05] = 0.0  # ノイズの除去

    local_max = maximum_filter(tmp_img, footprint=np.ones((10, 10)), mode="constant")
    detected_peaks = np.ma.array(tmp_img, mask=~(tmp_img == local_max))

    tmp = np.ma.array(detected_peaks, mask=~(detected_peaks >= detected_peaks.max() * threshold))
    peaks_index = np.where(~tmp.mask)

    touches = []
    if len(peaks_index[0]) > 5000:
        return touches

    for i in range(len(peaks_index[0])):
        touches.append(Touch([peaks_index[1][i].item(), peaks_index[0][i].item()]))
        if i > 10:
            break
    return touches


def detect_object(img, threshold=0.1):
    """
    判別分析を用いた二値化
    :param img: グラデーション画像
    :param threshold: threshold
    :return: 二値化画像
    """
    tmp_img = img.copy()
    tmp_img[tmp_img < threshold] = 0.0

    tmp8bit = (tmp_img * 255).astype(np.uint8)  # 8bitのスケールへ変換
    ret, tmp = cv2.threshold(tmp8bit, 0, 255, cv2.THRESH_OTSU)

    retval, labels, stats, centroids = cv2.connectedComponentsWithStats(tmp)  # Labeling

    # blobを抽出
    blobs = []
    for i in range(1, len(centroids)):
        coordinate = stats[i]
        center = centroids[i]
        left_top = (coordinate[0].item(), coordinate[1].item())
        right_bottom = (coordinate[0].item() + coordinate[2].item(), coordinate[1].item() + coordinate[3].item())
        shape = tmp[left_top[1]:left_top[1] + right_bottom[1], left_top[0]:left_top[0] + right_bottom[0]]

        if right_bottom[1] - left_top[1] > 100 and right_bottom[0] - left_top[1] > 100:
            blobs.append(Blob(center, left_top, right_bottom, shape))

    return blobs


class Analyzer(threading.Thread):

    def __init__(self, calibration, touch_tracker, blob_tracker):
        """
        アナライザクラスのコンストラクタ
        :param calibration: Calibrationインスタンス
        """
        super().__init__(target=self.__call)

        self.calibration = calibration
        self.touch_tracker = touch_tracker
        self.blob_tracker = blob_tracker

        self.running = True

        self.curve_type = 0
        self.threshold = 0.3
        self.gamma = 0.7
        self.gain = 1.0

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

        self.time_stamp = 0.0
        self.prev_time_stamp = -1.0

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

    def get_rate(self):
        return 1.0 / (self.time_stamp - self.prev_time_stamp)

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
            self.prev_time_stamp = self.time_stamp
            self.time_stamp = time.time()
            time.sleep(0.01)

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

        calc = self.calibration.get_calibrated_data()
        # calc = self.update_filter(tmp)

        # tone curve
        if self.curve_type == 1:
            calc = (calc ** self.gamma)
        if self.curve_type == 2:
            calc = (np.sin(np.pi * (calc - 0.1)) + 1) / 2
        if self.curve_type == 3:
            calc = (calc * 3)
        calc[calc > 1.0] = 1.0

        intr(calc)

        calc = np.insert(calc, self.led_insert_pos, 0)
        calc = np.reshape(calc, (11, 22))

        self.__plot(calc)

        tmpx = self.over_scan + self.plot_size[0]
        tmpy = self.over_scan + self.plot_size[1]

        mask_blobs = detect_object(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy], 0.5)
        touches = detect_touch(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy], mask_blobs, 0.05)
        blobs = detect_object(self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy], 0.1)

        # touch handling
        for touch in touches:
            self.touch_tracker.update(touch)
        self.touch_tracker.end_frame()

        # blob handling
        for blob in blobs:
            self.blob_tracker.update(blob)
        self.blob_tracker.end_frame()

        self.disp_img = self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy] * 255
        self.disp2_img = self.plot_img[self.over_scan:tmpx, self.over_scan:tmpy] * 255
        self.disp3_img = cv2.resize((calc * 700).astype(np.uint8), (320, 160), interpolation=cv2.INTER_NEAREST)
        self.disp4_img = cv2.resize((calc * 255).astype(np.uint8), (320, 160), interpolation=cv2.INTER_NEAREST)

