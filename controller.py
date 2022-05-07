import tkinter as tk
from PIL import Image, ImageTk, ImageOps

import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import sys


class StdoutRedirector(object):
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self, string):
        self.text_space.insert('end', string)
        self.text_space.see('end')

    def flush(self, *args):
        pass


class TmView(tk.Tk):
    def __init__(self, analyzer, server, visualizer, client, calibration):
        self.analyzer = analyzer
        self.server = server
        self.visualizer = visualizer
        self.client = client
        self.calibration = calibration

        super().__init__()
        self.title("TouchMatrix Viewer")

        self.setting_frame = None
        self.demo_frame = None
        self.view_frame = None
        self.figure_frame = None

        self.canvas = None
        self.canvas2 = None
        self.demo_list = None

        self.init_control_frame()
        self.init_setting_frame()
        self.init_view_frame()
        self.init_cal_frame()
        self.init_demo_frame()
        self.init_stdout_frame()

        self.img_type = 0

        self.contents = list()
        self.figure_canvas = None
        self.figure_length = 100
        self.figure_data = np.zeros(self.figure_length, np.uint16)
        self.fig = None
        self.ax = None

        self.init_figure()
        self.tim = 0
        self.update_figure()

        self.blank_image = np.zeros((160, 320, 3), dtype=np.uint8)

        self.update()
        self.__update_image()

    def test(self, *args):
        print('changed')

    def init_demo_frame(self):
        demo_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        demo_frame.grid(row=1, column=4, sticky=tk.N + tk.SW)
        self.demo_list = tk.Listbox(demo_frame, width=40)
        self.demo_list.bind('<<ListboxSelect>>', self.__select_demo)
        self.demo_list.pack()

    def init_stdout_frame(self):
        stdout_frame = tk.Frame(self, pady=10, padx=10)
        stdout_frame.grid(row=3, column=0, columnspan=5, sticky=tk.W + tk.SE)

        stdout_area = tk.Text(stdout_frame, height=7, width=150)
        stdout_area.pack(fill='x')
        sys.stdout = StdoutRedirector(stdout_area)

    def init_setting_frame(self):
        setting_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        setting_frame.grid(row=1, column=3, sticky=tk.N + tk.SW)

        linear_button = tk.Button(setting_frame, text="Linear", command=lambda: self.analyzer.set_curve(0), width=20)
        gamma_button = tk.Button(setting_frame, text="Gamma", command=lambda: self.analyzer.set_curve(1), width=20)

        threshold_label = tk.Label(setting_frame, text="Threshold")
        grad_label = tk.Label(setting_frame, text="SD")
        gamma_label = tk.Label(setting_frame, text="Gamma")

        threshold = tk.StringVar(value=self.analyzer.threshold)
        threshold_entry = tk.Entry(setting_frame, textvariable=threshold, width=10)
        threshold_entry.bind('<Return>', lambda arg: self.analyzer.set_threshold(threshold.get()))
        grad_sd = tk.StringVar(value=self.analyzer.sd)
        gsd_entry = tk.Entry(setting_frame, textvariable=grad_sd, width=10)
        gsd_entry.bind('<Return>', lambda arg: self.analyzer.set_grad(100, int(grad_sd.get())))

        c_param = tk.StringVar(value=self.analyzer.gamma)
        param_entry = tk.Entry(setting_frame, textvariable=c_param, width=10)
        param_entry.bind('<Return>', lambda arg: self.analyzer.set_curve_param(float(c_param.get())))

        linear_button.grid(row=0, column=0, columnspan=2)
        gamma_button.grid(row=1, column=0, columnspan=2)
        threshold_label.grid(row=2, column=0)
        threshold_entry.grid(row=2, column=1)
        gamma_label.grid(row=3, column=0)
        param_entry.grid(row=3, column=1)
        grad_label.grid(row=4, column=0)
        gsd_entry.grid(row=4, column=1)

    def init_control_frame(self):
        control_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        control_frame.grid(row=1, column=0, sticky=tk.N + tk.SE)

        start_button = tk.Button(control_frame, text="Start Receiving", command=self.server.start_server, width=20)
        client_start_button = tk.Button(control_frame, text="Start Sending", command=self.client.start_client,
                                        width=20)

        lp_label = tk.Label(control_frame, text="Local IP Address")
        tp_label = tk.Label(control_frame, text="Target IP Address")
        local_ip = tk.StringVar(value=self.server.ip)
        target_ip = tk.StringVar(value=self.client.ip)
        local_ip_entry = tk.Entry(control_frame, textvariable=local_ip, width=15)
        target_ip_entry = tk.Entry(control_frame, textvariable=target_ip, width=15)
        local_ip_entry.bind('<Return>', lambda arg: self.server.set_addr(local_ip.get(), 7000))
        target_ip_entry.bind('<Return>', lambda arg: self.client.set_addr(target_ip.get(), 9000))

        lp_label.grid(row=0, column=0)
        local_ip_entry.grid(row=0, column=1)
        start_button.grid(row=1, column=0, columnspan=2, pady=5)

        tp_label.grid(row=2, column=0)
        target_ip_entry.grid(row=2, column=1)
        client_start_button.grid(row=3, column=0, columnspan=2, pady=5)

    def init_view_frame(self):
        self.view_frame = tk.Frame(self, pady=10, padx=10)
        self.view_frame.grid(row=0, column=0, columnspan=5)

        self.canvas = tk.Canvas(self.view_frame, height=300, width=600)
        self.canvas2 = tk.Canvas(self.view_frame, height=300, width=600)

        self.canvas.grid(row=0, column=0)
        self.canvas2.grid(row=0, column=1)

    def init_cal_frame(self):
        cal_frame = tk.Frame(self, padx=10, pady=10, relief=tk.GROOVE, bd=2)
        cal_frame.grid(row=1, column=2, sticky=tk.N + tk.SW)

        self.figure_frame = tk.Frame(cal_frame, pady=10, padx=10)
        control_frame = tk.Frame(cal_frame)
        cal_lower_button = tk.Button(control_frame, text="Lower", command=self.calibration.calibration_lower, width=20)
        cal_upper_button = tk.Button(control_frame, text="Upper", command=self.calibration.calibration_upper, width=20)
        save_cal_button = tk.Button(control_frame, text="Save", command=self.calibration.save_data, width=20)
        load_cal_button = tk.Button(control_frame, text="Load", command=self.calibration.load_data, width=20)
        change_button = tk.Button(control_frame, text="Toggle Image", command=self._change_image, width=20)

        self.figure_frame.grid(row=0, column=0, sticky=tk.N)
        control_frame.grid(row=0, column=1, sticky=tk.N)
        cal_lower_button.pack()
        cal_upper_button.pack()
        save_cal_button.pack()
        load_cal_button.pack()
        change_button.pack()

    def _change_image(self):
        if self.img_type == 0:
            self.img_type = 1
        else:
            self.img_type = 0

    def get_sensor_data(self, index):
        if not self.calibration.is_calibration_available():
            return 0
        return self.calibration.get_sensor_data()[index]

    def get_calibrate_data(self, index):
        if not self.calibration.is_calibration_available():
            return 0, 60000
        cal_min = self.calibration.cal_min[index]
        cal_max = self.calibration.cal_max[index]

        return cal_min, cal_max

    def add_sensor_data(self, data, data_array):
        data_array = np.roll(data_array, -1)
        data_array[self.figure_length - 1] = data
        return data_array

    def update_figure(self):
        self.figure_data = self.add_sensor_data(self.get_sensor_data(60), self.figure_data)
        fr_min, fr_max = self.get_calibrate_data(60)

        self.ax.cla()
        self.ax.grid()
        self.ax.set_ylim([fr_min, fr_max])
        self.ax.plot(self.figure_data)

        self.figure_canvas.draw()

        self.figure_frame.after(500, self.update_figure)

    def init_figure(self):
        self.fig = Figure(figsize=(3, 2))
        self.figure_canvas = FigureCanvasTkAgg(self.fig, master=self.figure_frame)

        self.ax = self.fig.add_subplot(111)
        self.ax.grid()
        self.ax.set_ylim([0, 65000])
        self.ax.plot(self.figure_data)

        self.figure_canvas.get_tk_widget().pack()

    def insert_contents(self, content):
        self.contents.append(content)
        self.demo_list.insert('end', content.name)

    def __select_demo(self, event):
        self.visualizer.set_content(self.contents[event.widget.curselection()[0]])
        if not self.visualizer.running:
            self.visualizer.start()

    def __update_image(self):
        if self.analyzer.disp_img is None:
            self.disp_image(self.blank_image)
            self.disp2_image(self.blank_image)
            self.view_frame.after(1000, self.__update_image)
            return

        self.disp_image(self.analyzer.disp_img)
        if self.img_type == 0:
            self.disp2_image(self.analyzer.disp2_img)
        else:
            self.disp2_image(self.analyzer.disp3_img)

        self.view_frame.after(10, self.__update_image)

    def disp_image(self, img):
        # NumPyのndarrayからPillowのImageへ変換
        pil_image = Image.fromarray(img)

        # キャンバスのサイズを取得
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 画像のアスペクト比（縦横比）を崩さずに指定したサイズ（キャンバスのサイズ）全体に画像をリサイズする
        pil_image = ImageOps.pad(pil_image, (canvas_width, canvas_height))

        # PIL.ImageからPhotoImageへ変換する
        self.photo_image = ImageTk.PhotoImage(image=pil_image)

        # 画像の描画
        self.canvas.create_image(
            canvas_width / 2,  # 画像表示位置(Canvasの中心)
            canvas_height / 2,
            image=self.photo_image  # 表示画像データ
        )

    def disp2_image(self, img):
        # NumPyのndarrayからPillowのImageへ変換
        pil_image = Image.fromarray(img)

        # キャンバスのサイズを取得
        canvas_width = self.canvas2.winfo_width()
        canvas_height = self.canvas2.winfo_height()

        # 画像のアスペクト比（縦横比）を崩さずに指定したサイズ（キャンバスのサイズ）全体に画像をリサイズする
        pil_image = ImageOps.pad(pil_image, (canvas_width, canvas_height))

        # PIL.ImageからPhotoImageへ変換する
        self.photo_image2 = ImageTk.PhotoImage(image=pil_image)

        # 画像の描画
        self.canvas2.create_image(
            canvas_width / 2,  # 画像表示位置(Canvasの中心)
            canvas_height / 2,
            image=self.photo_image2  # 表示画像データ
        )
