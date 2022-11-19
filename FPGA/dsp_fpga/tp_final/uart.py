import serial

class Uart:

    def __init__(self, port, baudrate, timeout):
        self.timeout = timeout
        self.dev     = serial.Serial(port, baudrate, timeout = timeout)

    def send(self, data):
        if isinstance(data, (bytes, tuple)):
            data = list(data)

        elif isinstance(data, int):
            data = [data]

        else:
            raise ValueError("Invalid data: {} is not allowed".format(type(data)))

        self.dev.write(bytes(data))

    def receive(self, n):
        if not isinstance(n, int):
            raise ValueError("Invalid number of bytes: {} is not allowed".format(type(n)))

        if n <= 0:
            return []

        res = list(self.dev.read(n))

        if len(res) != n:
            print("Read operation timed out, possibly serial port is not correctly configured")
            return None

        return res