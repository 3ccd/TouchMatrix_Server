import time

import numpy as np
import cv2
import matplotlib.pyplot as plt

from classes import calibration, connection, analyzer

if __name__ == "__main__":
    # Sharing Data
    t_frame = connection.TmFrame()

    # create instance
    t_calibration = calibration.Calibration(t_frame, False)
    t_server = connection.SerialServer(t_frame, "COM3",
                                       baud=403200)

    fig, ax = plt.subplots(1, 1)

    data1 = np.zeros(100)
    data2 = np.zeros(100)
    x = np.arange(0, 100, 1)

    lines, = ax.plot(x, data1, color="red")
    lines2, = ax.plot(x, data2, color="green")
    ax.set_ylim((0.0, 0.2))

    time.sleep(2)
    t_server.start_server()
    time.sleep(2)

    t_calibration.load_data()

    while True:
        if not t_calibration.is_calibration_available():
            break

        data = t_calibration.get_calibrated_data()

        data1 = np.roll(data1, -1)
        data1[99] = data[60]

        data2 = np.roll(data2, -1)
        data2[99] = data[61]

        lines.set_data(x, data1)
        lines2.set_data(x, data2)

        plt.pause(.01)

        pos = analyzer.intr(data)

        bilinear = cv2.resize(pos, (64, 64), interpolation=cv2.INTER_LINEAR)
        bilinear = cv2.resize(bilinear, (640, 640), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("bilinear", bilinear)

        nearest = cv2.resize(pos, (640, 640), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("nearest", nearest)

        bicubic = cv2.resize(pos, (64, 64), interpolation=cv2.INTER_CUBIC)
        bicubic = cv2.blur(bicubic, ksize=(5, 5))
        bicubic = cv2.resize(bicubic, (640, 640), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("bicubic", bicubic)
        cv2.waitKey(10)

    t_server.stop()
