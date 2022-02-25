import tkinter as tk
from PIL import Image, ImageTk, ImageOps

import numpy as np

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure


class TmView(tk.Tk):
    def __init__(self, analyzer, server, visualizer, client):
        self.analyzer = analyzer
        self.server = server
        self.visualizer = visualizer
        self.client = client

        super().__init__()
        self.title("TouchMatrix Viewer")

        self.view_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        self.control_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        self.cal_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        self.setting_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        self.demo_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)
        self.figure_frame = tk.Frame(self, pady=10, padx=10, relief=tk.GROOVE, bd=2)

        self.view_frame.grid(row=0, column=0, columnspan=5)
        self.control_frame.grid(row=1, column=0)
        self.figure_frame.grid(row=1, column=1)
        self.cal_frame.grid(row=1, column=2)
        self.setting_frame.grid(row=1, column=3)
        self.demo_frame.grid(row=1, column=4)

        self.canvas = tk.Canvas(self.view_frame, height=300, width=600)
        self.canvas.grid(row=0, column=0)
        self.canvas2 = tk.Canvas(self.view_frame, height=300, width=600)
        self.canvas2.grid(row=0, column=1)

        self.server_start_button = tk.Button(self.control_frame, text="Start Server", command=self.server.start_server,
                                             width=20)
        self.analyze_start_button = tk.Button(self.control_frame, text="Start Analyze", command=self.analyzer.start,
                                              width=20)
        self.read_button = tk.Button(self.control_frame, text="Read Image", command=self.__update_image, width=20)
        self.cal_lower_button = tk.Button(self.cal_frame, text="Lower", command=self.analyzer.calibration_lower,
                                          width=20)
        self.cal_upper_button = tk.Button(self.cal_frame, text="Upper", command=self.analyzer.calibration_upper,
                                          width=20)
        self.save_cal_button = tk.Button(self.cal_frame, text="Save", command=self.analyzer.save_data, width=20)
        self.load_cal_button = tk.Button(self.cal_frame, text="Load", command=self.analyzer.load_data, width=20)
        self.linear_button = tk.Button(self.setting_frame, text="Linear", command=lambda: self.analyzer.set_curve(0),
                                       width=20)
        self.gamma_button = tk.Button(self.setting_frame, text="Gamma", command=lambda: self.analyzer.set_curve(1),
                                      width=20)
        self.s_button = tk.Button(self.setting_frame, text="S Curve", command=lambda: self.analyzer.set_curve(2),
                                  width=20)
        self.clip_button = tk.Button(self.setting_frame, text="Clip", command=lambda: self.analyzer.set_curve(3),
                                     width=20)
        threshold = tk.StringVar()
        self.threshold_entry = tk.Entry(self.setting_frame, textvariable=threshold, width=20)
        self.threshold_button = tk.Button(self.setting_frame, text="Set Threshold",
                                          command=lambda: self.analyzer.set_threshold(threshold.get()),
                                          width=20)
        grad_size = tk.StringVar()
        grad_sd = tk.StringVar()
        self.gs_entry = tk.Entry(self.setting_frame, textvariable=grad_size, width=20)
        self.gsd_entry = tk.Entry(self.setting_frame, textvariable=grad_sd, width=20)
        self.grad_button = tk.Button(self.setting_frame, text="Set Grad",
                                     command=lambda: self.analyzer.set_grad(int(grad_size.get()), int(grad_sd.get())),
                                     width=20)

        c_param = tk.StringVar()
        self.param_entry = tk.Entry(self.setting_frame, textvariable=c_param, width=20)
        self.param_button = tk.Button(self.setting_frame, text="Set Curve",
                                      command=lambda: self.analyzer.set_curve_param(float(c_param.get())), width=20)

        self.demo_list = tk.Listbox(self.demo_frame)
        self.demo_list.bind('<<ListboxSelect>>', self.__select_demo)
        self.demo_start_button = tk.Button(self.demo_frame, text="START", command=self.visualizer.start, width=20)
        self.client_start_button = tk.Button(self.demo_frame, text="Client Start", command=self.client.start_client
                                             , width=20)

        self.server_start_button.pack()
        self.analyze_start_button.pack()
        self.cal_lower_button.pack()
        self.cal_upper_button.pack()
        self.save_cal_button.pack()
        self.load_cal_button.pack()
        self.read_button.pack()
        self.linear_button.pack()
        self.gamma_button.pack()
        self.s_button.pack()
        self.clip_button.pack()
        self.threshold_entry.pack()
        self.threshold_button.pack()
        self.gs_entry.pack()
        self.gsd_entry.pack()
        self.grad_button.pack()
        self.param_entry.pack()
        self.param_button.pack()
        self.demo_list.pack()
        self.demo_start_button.pack()
        self.client_start_button.pack()

        self.contents = list()
        self.figure_canvas = None
        self.figure_length = 100
        self.figure_data = np.zeros(self.figure_length, np.uint16)
        self.fig = None
        self.ax = None

        self.init_figure()
        self.tim = 0
        self.update_figure()

    def get_sensor_data(self, index):
        if self.analyzer.latest_data is None:
            return 0
        return self.analyzer.latest_data[index]

    def add_sensor_data(self, data, data_array):
        data_array = np.roll(data_array, -1)
        data_array[self.figure_length - 1] = data
        return data_array

    def update_figure(self):
        self.figure_data = self.add_sensor_data(self.get_sensor_data(60), self.figure_data)

        self.ax.cla()
        self.ax.grid()
        self.ax.set_ylim([25000, 40000])
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

    def __update_image(self):
        if self.analyzer.disp_img is None:
            self.view_frame.after(100, self.__update_image)
            return

        self.disp_image(self.analyzer.disp_img)
        self.disp2_image(self.analyzer.disp2_img)

        self.view_frame.after(20, self.__update_image)

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
