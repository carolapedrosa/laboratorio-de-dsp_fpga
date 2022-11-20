import serial

class Uart:

    def __init__(self, port, baudrate, timeout):
        self.timeout  = timeout
        self.port     = port
        self.baudrate = baudrate
        self.open()

    def send(self, data):
        if isinstance(data, (bytes, tuple)):
            data = list(data)

        elif isinstance(data, int):
            data = [data]

        else:
            raise ValueError("Invalid data: {} is not allowed".format(type(data)))

        try:
            self.dev.write(bytes(data))
        except:
            print("Write operation failed")
            return -1

        return 0

    def receive(self, n):
        if not isinstance(n, int):
            raise ValueError("Invalid number of bytes: {} is not allowed".format(type(n)))

        if n <= 0:
            return []

        try:
            res = list(self.dev.read(n))
        except:
            res = []

        if len(res) != n:
            print("Read operation faied")
            return None

        return res

    def close(self):
        try:
            if self.dev is not None:
                self.dev.reset_input_buffer()
                self.dev.reset_output_buffer()
                self.dev.close()
        except:
            pass

    def open(self):
        if hasattr(self, 'dev') and self.dev is not None:
            self.dev.open()
        else:
            try:
                self.dev = serial.Serial(self.port, self.baudrate, timeout = self.timeout)
            except:
                self.dev = None

    def __del__(self):
        self.close()