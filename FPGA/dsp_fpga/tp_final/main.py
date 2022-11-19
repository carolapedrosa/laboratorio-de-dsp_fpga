import os
import sys
from PyQt5.QtWidgets import QApplication
from dsp_fpga.tp_final.gui import Gui

if __name__ == "__main__":
    os.environ['PATH'] += ':/usr/intelFPGA_lite/21.1/quartus/bin/'
    app = QApplication(sys.argv)
    window = Gui('/dev/ttyUSB0', 230400, 10)
    window.show()
    sys.exit(app.exec())
