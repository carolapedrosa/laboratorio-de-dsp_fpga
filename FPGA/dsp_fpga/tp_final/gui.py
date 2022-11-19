from dsp_fpga.tp_final.canvas import Canvas
from dsp_fpga.tp_final.uart import Uart
from dsp_fpga.tp_final.file import open_file, save_file

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QFrame
from dsp_fpga.tp_final.filters import *

import numpy as np
from matplotlib.pyplot import imsave

class Gui(QWidget):

    KERNEL_SIZE    = 7
    MAX_IMG_WIDTH  = 256
    MAX_IMG_HEIGHT = 256
    RESPONSE_BYTES = 3

    def __init__(self, port, baudrate, timeout, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.port     = port
        self.baudrate = baudrate
        self.timeout  = timeout

        self.open_serial()
        self.create_layouts()
        self.create_widgets()
        self.setup_widgets()
        self.connect_callbacks()

    def open_serial(self):
        try:
            self.uart = Uart(self.port, self.baudrate, self.timeout)
        except Exception as e:
            print(e)
            self.uart = None
            print("Hardware error: Failed to open serial port")

    def create_layouts(self):
        self.main_layout    = QVBoxLayout(self)
        self.plot_layout    = QHBoxLayout()
        self.config_layout  = QHBoxLayout()

    def create_widgets(self):
        self.canvas              = Canvas(2, self, titles = ['Original', 'Filtered'])
        self.clear_fig_button    = QPushButton('Clear plot', self)
        self.open_file_button    = QPushButton('New plot', self)
        self.apply_filter_button = QPushButton('Apply filter', self)
        self.save_filtered       = QPushButton('Save filtered image', self)
        self.filter_frame        = QFrame(self)
        self.filter_options      = QComboBox(self.filter_frame)
        self.iconfig_layout      = QHBoxLayout(self.filter_frame)
        self.filters             = [
            Identity        (self.filter_frame),
            GaussianBlur    (self.filter_frame),
            Negative        (self.filter_frame),
            SaltnPepper     (self.filter_frame),
            Median          (self.filter_frame),
            Histogram       (self.filter_frame),
            ImAdjust        (self.filter_frame),
            BitPlaneSlicing (self.filter_frame),
            ColorLimitation (self.filter_frame),
            Downscaler      (self.filter_frame),
            Logarithmic     (self.filter_frame),
        ]

    def setup_widgets(self):
        self.main_layout    .addWidget(self.canvas,           alignment = Qt.AlignCenter)
        self.plot_layout    .addWidget(self.clear_fig_button, alignment = Qt.AlignCenter)
        self.plot_layout    .addWidget(self.open_file_button, alignment = Qt.AlignCenter)
        self.config_layout  .addWidget(self.filter_frame,     alignment = Qt.AlignCenter)
        self.iconfig_layout .addWidget(self.filter_options,   alignment = Qt.AlignCenter)

        self.main_layout    .addLayout(self.plot_layout)
        self.main_layout    .addLayout(self.config_layout)

        for filter in self.filters:
            self.iconfig_layout.addWidget(filter, alignment = Qt.AlignCenter)
            self.filter_options.addItem(filter.name)
            filter.hide()

        self.iconfig_layout .addWidget(self.apply_filter_button, alignment = Qt.AlignCenter)
        self.iconfig_layout .addWidget(self.save_filtered      , alignment = Qt.AlignCenter)

        self.filters[0].show()
        self.filter_frame.setLineWidth(2)
        self.filter_frame.setFrameStyle(1)

    def connect_callbacks(self):
        self.open_file_button   .clicked.connect(self.open_image)
        self.clear_fig_button   .clicked.connect(self.canvas.clear)
        self.filter_options     .currentIndexChanged.connect(self.update_config)
        self.apply_filter_button.clicked.connect(self.apply_filter)
        self.save_filtered      .clicked.connect(self.save_filtered_callback)

    def open_image(self):
        filename = open_file(filter = "PNG (*.png);;JPEG (*.jpg *.jpeg);;TIFF (*.tif)")

        if filename:
            self.canvas.clear()
            self.canvas.plot(0, filename, interpolation='nearest', aspect='auto')

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key.Key_Escape: self.close()
        return super().keyPressEvent(a0)

    def update_config(self):
        for filter in self.filters:
            if filter.name == self.filter_options.currentText():
                filter.show()
            else:
                filter.hide()

    def apply_filter(self):
        img = self.canvas.images[0]
        if img is not None:
            for filter in self.filters:
                if filter.name == self.filter_options.currentText():
                    break

            if filter.hw:
                if len(img.shape) > 3:
                    print("Wrong image format")

                elif len(img.shape) == 3:
                    if img.shape[2] <= 3:
                        res = np.zeros(img.shape)
                    else:
                        res = np.zeros(img.shape[:2] + (3,))
                        img = img[:, :, :3]
                else:
                    img = img.reshape(*img.shape, 1)
                    res = np.zeros(img.shape + (1,))

                img = (self.normalize(img) * 255).astype(np.uint8)

                for dim in range(img.shape[2]):
                    r = self.hw_filter(img[:, :, dim], filter)
                    if r is None:
                        return
                    res[:, :, dim] += r

                if res.shape[2] == 1:
                    res = res.reshape(res.shape[:2])

                res = self.normalize(res)

            else:
                res = filter.apply(img)

            if res is not None:
                filter_name = self.filter_options.currentText()
                self.canvas.change_title(1, 'Filtered with: {}'.format(filter_name))
                self.canvas.plot(1, res, interpolation='nearest', aspect='auto')
            else:
                print("Skipping, result got lost!")

    def save_filtered_callback(self):
        if self.canvas.images[1] is None:
            print("Missing filtered image")
            return

        filename = save_file()
        if filename:
            imsave(filename, self.canvas.images[1])

    def send_data(self, values, n):
        for _v in values:
            v = int(_v)
            for i in range(n):
                self.uart.send((v >> (i << 3)) & 0xFF)

    @staticmethod
    def normalize(img):
        return (img - img.min()) / abs(img - img.min()).max()
    
    def hw_filter(self, img, filter):
        if self.uart is None:
            self.open_serial()

        if self.uart is None:
            return None

        if img.shape[0] > self.MAX_IMG_HEIGHT or img.shape[1] > self.MAX_IMG_WIDTH:
            print("Image is too big for hardware implementation")
            return

        try:
            kernel = filter.get_kernel()
            self.send_data([kernel.shape[0]], 1)
            self.send_data(kernel.reshape(-1), 2)
            self.send_data(img.shape, 2)
            self.send_data(img.reshape(-1), 1)
        except IOError:
            self.uart = None
            print("Serial port disconnected")
            return
        except Exception as e:
            print(e)
            return

        _res = self.uart.receive(len(img.reshape(-1)) * self.RESPONSE_BYTES)
        if _res is not None:
            res = []
            for i in range(0, len(_res), self.RESPONSE_BYTES):
                v = int.from_bytes(_res[i : i + self.RESPONSE_BYTES], 'little')
                v -= (v & (1 << ((self.RESPONSE_BYTES << 3) - 1))) << 1
                res.append(v)
            res = np.reshape(res, img.shape)
        else:
            res = None

        return res