import time

import numpy as np


def generate_test_data():
    # tmp = np.linspace(0.02, 1.0, 121)
    tmp = np.random.rand(121)
    return tmp


class Calibration:
    def __init__(self, tm_frame, test_mode=False):
        self.tm_frame = tm_frame

        self.cal_min = None
        self.cal_max = None
        self.range = None

        self.sample_count = 10

        self.test = test_mode

    def get_calibrated_data(self):
        if not self.is_calibration_available():
            return None

        if self.test:
            return generate_test_data()

        data = self.get_sensor_data()

        # replace out-of-range values (lower)
        data[data < self.cal_min] = self.cal_min[data < self.cal_min]
        offset = data - self.cal_min

        # replace out-of-range values (upper)
        offset[offset > self.range] = self.range[offset > self.range]

        # normalize
        calc = (offset / self.range)
        calc[calc > 1.0] = 1.0

        return calc

    def get_range(self):
        return self.range

    def get_sensor_data(self):
        if self.test:
            return np.zeros(121)
        if self.tm_frame.n_array is None:
            print('Error: No Sensor data available (Check the connection to the Raspberry Pi)')
            return
        return self.tm_frame.n_array

    def is_calibration_available(self):
        if self.test:
            return True
        if self.range is None:
            return False
        return True

    def calibration_lower(self):
        tmp = np.zeros((121, self.sample_count), dtype=np.uint16)
        for i in range(self.sample_count):
            tmp[:, i] = self.get_sensor_data()
            time.sleep(0.1)
        self.cal_min = tmp.max(axis=1)

        print(self.cal_min)

    def calibration_upper(self):
        tmp = np.zeros((121, self.sample_count), dtype=np.uint16)
        for i in range(self.sample_count):
            tmp[:, i] = self.get_sensor_data()
            time.sleep(0.1)
        self.cal_max = tmp.max(axis=1)

        print(self.cal_max)
        self.calc_range()

    def calc_range(self):
        if self.cal_min is None:
            print('Error: Lower Calibration required')
            return
        if self.cal_max is None:
            print('Error: Upper Calibration required')
            return

        tmp = self.cal_max - self.cal_min

        # error = np.where(tmp == 0)  # ERROR DETECTOR
        # if error.shape[0] > 0:
        #     print('Error: sensor ')
        #     print(error)
        #     return

        self.range = tmp
        print(self.range)

    def save_data(self):
        if self.is_calibration_available():
            np.savez("./cal_data", self.cal_min, self.cal_max, self.range)
            print('Info: Calibration data is saved as "cal_data.npz"')
        else:
            print('Error: Calibration required')

    def load_data(self):
        data = None

        try:
            data = np.load("./cal_data.npz")
        except FileNotFoundError:
            print('Calibration file not found')
            return

        print('Info: Calibration data loaded')
        print(data.files)
        self.cal_min = data['arr_0']
        self.cal_max = data['arr_1']
        self.range = data['arr_2']
