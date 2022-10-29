from dsp_fpga.tp_final.canvas import Canvas
from dsp_fpga.tp_final.uart import Uart
from dsp_fpga.tp_final.file import open_file

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QFrame
from dsp_fpga.tp_final.filters import GaussianBlur, Identity

class Gui(QWidget):
    def __init__(self, port, baudrate, timeout, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.uart = Uart(timeout, port, baudrate)

        self.create_layouts()
        self.create_widgets()
        self.setup_widgets()
        self.connect_callbacks()

    def create_layouts(self):
        self.main_layout    = QVBoxLayout(self)
        self.plot_layout    = QHBoxLayout()
        self.config_layout  = QHBoxLayout()

    def create_widgets(self):
        self.canvas              = Canvas(2, self, titles = ['Original', 'Filtered'])
        self.clear_fig_button    = QPushButton('Clear plot', self)
        self.open_file_button    = QPushButton('New plot', self)
        self.apply_filter_button = QPushButton('Apply filter', self)
        self.filter_frame        = QFrame(self)
        self.filter_options      = QComboBox(self.filter_frame)
        self.iconfig_layout      = QHBoxLayout(self.filter_frame)
        self.filters             = [
            Identity(self.filter_frame),
            GaussianBlur(self.filter_frame),
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

        self.filters[0].show()
        self.filter_frame.setLineWidth(2)
        self.filter_frame.setFrameStyle(1)

    def connect_callbacks(self):
        self.open_file_button   .clicked.connect(self.open_image)
        self.clear_fig_button   .clicked.connect(self.canvas.clear)
        self.filter_options     .currentIndexChanged.connect(self.update_config)
        self.apply_filter_button.clicked.connect(self.apply_filter)

    def open_image(self):
        filename = open_file(filter = "JPEG (*.jpg *.jpeg);;TIFF (*.tif);;PNG (*.png)")

        if filename:
            self.canvas.plot(0, filename)

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
        if self.canvas.images[0] is not None:
            # if not self.uart.check_presence():
            #     print("Hardware error: Failed to detect serial port")
            #     return

            # self.uart.send_image(self.canvas.images[0])
            # res = self.uart.recv_image(*self.canvas.images[0].shape)
            res = self.canvas.images[0]

            if res is not None:
                filter_name = self.filter_options.currentText()
                self.canvas.change_title(1, 'Filtered with: {}'.format(filter_name))
                self.canvas.plot(1, res)