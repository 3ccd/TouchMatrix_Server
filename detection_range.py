import time

import numpy as np
import cv2
import matplotlib.pyplot as plt

from classes import calibration, connection


srarr = np.zeros((2, 1))


def on_press(event):
    global srarr
    if event.key == 'k':
        print('press')
        start = data1.argmax()
        end = data2.argmax()
        x = data1[start:end].copy()
        xmax = x.max()
        x = x * (1.0 / xmax)
        y = np.linspace(0, 1, x.shape[0])

        marg = np.stack([x, y])
        print(marg.shape)
        print(srarr.shape)
        tmp = np.concatenate([srarr, marg], 1)
        print(tmp.shape)
        srarr = tmp

        ax1.scatter(y, x)
    if event.key == 's':
        np.savez('sr_plot', srarr)


if __name__ == '__main__':
    # Sharing Data
    t_frame = connection.TmFrame()

    # create instance
    t_calibration = calibration.Calibration(t_frame, False)
    t_server = connection.SerialServer(t_frame, "COM3",
                                       baud=403200)

    fig, (ax, ax1) = plt.subplots(1, 2)
    fig.canvas.mpl_connect('key_press_event', on_press)

    data1 = np.zeros(100)
    data2 = np.zeros(100)
    x = np.arange(0, 100, 1)

    lines, = ax.plot(x, data1, color="red")
    lines2, = ax.plot(x, data2, color="green")
    ax.set_ylim((0.0, 0.2))
    ax1.set_ylim((0.0, 1.0))

    time.sleep(2)
    t_server.start_server()
    time.sleep(2)

    t_calibration.load_data()

    d1_mean = np.zeros(5)
    d2_mean = np.zeros(5)

    while True:
        if not t_calibration.is_calibration_available():
            break

        data = t_calibration.get_calibrated_data()

        d1_mean = np.roll(d1_mean, -1)
        d1_mean[-1] = data[60]

        d2_mean = np.roll(d2_mean, -1)
        d2_mean[-1] = data[61]

        data1 = np.roll(data1, -1)
        data1[-1] = d1_mean.mean()

        data2 = np.roll(data2, -1)
        data2[-1] = d2_mean.mean()

        lines.set_data(x, data1)
        lines2.set_data(x, data2)

        plt.pause(.06)

    t_server.stop()
