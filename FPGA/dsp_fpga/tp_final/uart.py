import serial

class Uart:

    def __init__(self, port, baudrate, timeout):
        self.timeout  = timeout
        self.port     = port
        self.badurate = baudrate
        self.dev      = serial.Serial(port, baudrate, timeout = timeout)

    def send(self, data):
        if isinstance(data, (bytes, tuple)):
            data = list(data)

        elif isinstance(data, int):
            data = [data]

        else:
            raise ValueError("Invalid data: {} is not allowed".format(type(data)))

        try:
            self.dev.write(bytes(data))
        except serial.SerialException:
            return -1

        return 0

    def receive(self, n):
        if not isinstance(n, int):
            raise ValueError("Invalid number of bytes: {} is not allowed".format(type(n)))

        if n <= 0:
            return []

        try:
            res = list(self.dev.read(n))
        except serial.SerialException as e:
            print(e)
            res = []

        if len(res) != n:
            print("Read operation timed out, possibly serial port is not correctly configured")
            return None

        return res

    def close(self):
        try:
            self.dev.reset_input_buffer()
            self.dev.reset_output_buffer()
            self.dev.close()
        except serial.PortNotOpenError:
            pass

    def open(self):
        if hasattr(self, 'dev'):
            self.dev.open()
        else:
            self.dev = serial.Serial(self.port, self.baudrate, timeout = self.timeout)

    def __del__(self):
        self.close()