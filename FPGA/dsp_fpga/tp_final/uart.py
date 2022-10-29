from functools import   reduce
from operator  import   xor
from warnings  import   warn
import serial
import time

class Uart:

    frames  = {
        'crc_error' : [0x0, 0x1, 0x2, 0x3],
        'cmd_reset' : [0x1, 0x2, 0x3, 0x4],
        'cmd_alive' : [0x2, 0x3, 0x4, 0x5],
        'cmd_tximg' : [0x3, 0x4, 0x5, 0x6],
        'cmd_rximg' : [0x4, 0x5, 0x6, 0x7],
    }

    def __init__(self, port, baudrate, timeout):
        self.timeout = timeout
        self.dev     = serial.Serial(port, baudrate, timeout = timeout)

    @property
    def crc_len():
        return 1

    @staticmethod
    def crc(data):
        return reduce(xor, data)

    @staticmethod
    def send_image_frame(image):
        if not hasattr(image, 'shape'):
            warn("Attempting to send invalid image")
            return None

        h, w = image.shape
        res = Uart.frames['cmd_tximg'] + [h, w]
        for row in image:
            res += row

        return res

    @staticmethod
    def recv_image_frame(h, w):
        return Uart.frames['cmd_rximg'] + [h, w]

    def send_data(self, data):
        if isinstance(data, (bytes, tuple)):
            data = list(data)

        elif isinstance(data, int):
            data = [data]

        else:
            raise ValueError("Invalid data: {} is not allowed".format(type(data)))

        self.dev.write(bytes(data + self.crc(data)))

    def read_data(self, n):
        if not isinstance(n, int):
            raise ValueError("Invalid number of bytes: {} is not allowed".format(type(n)))

        if n <= 0:
            return []

        res = list(self.dev.read(n + self.crc_len))

        if len(res) != n:
            if res == self.frames['crc_error']:
                warn("Device received CRC error, verify serial connection")
                return None
            else:
                warn("Read operation timed out, possibly serial port is not correctly configured")
                return None

        if int.from_bytes(res[-self.crc_len:], 'little') != self.crc(res[:-self.crc_len]):
            warn("Received bad CRC, verify serial connection")
            return None

        return res[:-self.crc_len]

    def check_presence(self, retry = 10):
        for _ in range(retry):
            time.sleep(self.timeout)
            self.send_data(self.frames['cmd_alive'])
            res = self.read_data(len(self.frames['cmd_alive']))

            if res is not None and res == self.frames['cmd_alive']:
                return True

        return False

    def send_image(self, image):
        return self.send_data(self.send_image_frame(image))

    def recv_image(self, h, w):
        if self.send_data(self.recv_image_frame(h, w)) is not None:
            return self.read_data(h * w)
