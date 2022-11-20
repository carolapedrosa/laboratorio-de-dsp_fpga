from dsp_fpga.tp_final.canvas import Canvas
from dsp_fpga.tp_final.uart import Uart
from dsp_fpga.tp_final.file import open_file, save_file

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QFrame, QProgressBar
from dsp_fpga.tp_final.filters import *

import numpy as np
from matplotlib.pyplot import imsave

from threading import Thread
from time import sleep

class Gui(QWidget):

    KERNEL_SIZE    = 11
    MAX_IMG_WIDTH  = 200
    MAX_IMG_HEIGHT = 200
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

        self.alive = True
        self.pvalue = 0
        self.pshow = False
        self.t = Thread(target = self.progress_updater)
        self.t.start()

    def open_serial(self):
        try:
            if hasattr(self, 'uart') and self.uart is not None:
                self.uart.close()

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
        self.info_layout         = QVBoxLayout(self.filter_frame)
        self.iconfig_layout      = QHBoxLayout()
        self.progress            = QProgressBar(self)
        self.filters             = [
            Identity            (self.filter_frame),
            GaussianBlur        (self.filter_frame),
            Negative            (self.filter_frame),
            SaltnPepper         (self.filter_frame),
            Median              (self.filter_frame),
            Histogram           (self.filter_frame),
            ImAdjust            (self.filter_frame),
            BitPlaneSlicing     (self.filter_frame),
            BrightnessEnhancer  (self.filter_frame),
            ColorLimitation     (self.filter_frame),
            Downsampler         (self.filter_frame),
            Logarithmic         (self.filter_frame),
            RidgeDetection      (self.filter_frame),
            Sharpen             (self.filter_frame),
            BoxBlur             (self.filter_frame),
            RadonDirect         (self.filter_frame),
            RadonInverse        (self.filter_frame),
            MotionBlur          (self.filter_frame),
            Wiener              (self.filter_frame),
            MotionBlurSw        (self.filter_frame),
        ]

    def setup_widgets(self):
        self.main_layout    .addWidget(self.canvas,           alignment = Qt.AlignCenter)
        self.plot_layout    .addWidget(self.clear_fig_button, alignment = Qt.AlignCenter)
        self.plot_layout    .addWidget(self.open_file_button, alignment = Qt.AlignCenter)
        self.config_layout  .addWidget(self.filter_frame,     alignment = Qt.AlignCenter)
        self.iconfig_layout .addWidget(self.filter_options,   alignment = Qt.AlignCenter)

        self.main_layout    .addLayout(self.plot_layout)
        self.main_layout    .addLayout(self.config_layout)

        first = 1
        for filter in sorted(self.filters):
            if first:
                self.pshow = filter.hw
                filter.show()
            else:
                filter.hide()

            first = 0
            self.iconfig_layout.addWidget(filter, alignment = Qt.AlignCenter)
            self.filter_options.addItem(filter.name)
            filter.hide()

        self.iconfig_layout .addWidget(self.apply_filter_button, alignment = Qt.AlignCenter)
        self.iconfig_layout .addWidget(self.save_filtered      , alignment = Qt.AlignCenter)
        self.info_layout    .addLayout(self.iconfig_layout)
        self.info_layout    .addWidget(self.progress)

        self.progress       .setMinimum(0)
        self.progress       .setMaximum(100)
        self.filters[0]     .show()
        self.filter_frame   .setLineWidth(2)
        self.filter_frame   .setFrameStyle(1)

    def connect_callbacks(self):
        self.open_file_button   .clicked.connect(self.open_image)
        self.clear_fig_button   .clicked.connect(self.canvas.clear)
        self.filter_options     .currentTextChanged.connect(self.updated)
        self.apply_filter_button.clicked.connect(self.apply_filter)
        self.save_filtered      .clicked.connect(self.save_filtered_callback)

    def open_image(self):
        filename = open_file(filter = "PNG (*.png);;JPEG (*.jpg *.jpeg);;TIFF (*.tif)")

        if filename:
            self.canvas.clear()
            self.canvas.plot(0, filename, interpolation='nearest', aspect='auto')

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key.Key_Escape:
            self.alive = False
            self.t.join()
            self.close()
        return super().keyPressEvent(a0)

    def progress_updater(self):
        while self.alive:
            if self.pshow:
                self.progress.show()
            else:
                self.progress.hide()
            sleep(.1)
            self.progress.setValue(self.pvalue)

    def updated(self, name):
        for filter in self.filters:
            if name == filter.name:
                self.currfilt = filter
                filter.show()
            else:
                filter.hide()

        self.pvalue = 0
        self.pshow = self.currfilt.hw

    def apply_filter(self):
        img = self.canvas.images[0]
        if img is not None:
            img = img.copy()
            for filter in self.filters:
                if filter.name == self.filter_options.currentText():
                    break

            if len(img.shape) not in [2, 3]:
                print("Wrong image format")
                return

            self.pvalue = 0

            if filter.hw:
                if len(img.shape) == 2:
                    img = img.reshape(*img.shape, 1)

                res = []
                img = (self.normalize(img) * 255).astype(np.uint8)
                kernel = filter.get_kernel()

                print('Using kernel:')
                print(kernel)

                for dim in range(img.shape[2]):
                    r = self.hw_filter(img[:, :, dim], kernel)
                    self.pvalue = int((dim + 1) / img.shape[2] * 100)
                    if r is None:
                        return

                    res.append(r)
                    res[-1] = res[-1].reshape(*res[-1].shape, 1)

                res = np.concatenate(tuple(res), axis = -1).astype(float)

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
            cmap = None
            if len(self.canvas.images[1].shape) < 3:
                cmap = 'gray'

            imsave(filename, self.canvas.images[1], cmap = cmap)

    def send_data(self, values, n):
        ret = 0
        for _v in values:
            v = int(_v)
            for i in range(n):
                ret = self.uart.send((v >> (i << 3)) & 0xFF)
                if ret != 0:
                    raise IOError("Failed to connect with serial device")
        return ret

    @staticmethod
    def normalize(img):
        return (img - img.min()) / abs(img - img.min()).max()
    
    def hw_filter(self, img, kernel):
        self.open_serial()

        if self.uart is None:
            return None

        if img.shape[0] > self.MAX_IMG_HEIGHT or img.shape[1] > self.MAX_IMG_WIDTH:
            print("Image is too big for hardware implementation")
            return

        try:
            if (
                len(kernel.shape) != 2 or
                kernel.shape[0] != kernel.shape[1] or
                kernel.shape[0] > self.KERNEL_SIZE
            ):
                print("Wrong kernel format")
                return
            if(self.send_data([kernel.shape[0]], 1)) != 0:
                return
            if (self.send_data(kernel.reshape(-1), 2)) != 0:
                return
            if (self.send_data(img.shape, 2)) != 0:
                return
            if (self.send_data(img.reshape(-1), 1) != 0):
                return
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