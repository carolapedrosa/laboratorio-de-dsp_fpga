from PyQt5.QtWidgets import QWidget, QDoubleSpinBox, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class Filter(QWidget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def get_params(self):
        return []

class Identity(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Identity', *args, **kwargs)
        self.main_layout = QVBoxLayout(self)

    def get_params(self):
        return []

class GaussianBlur(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Gaussian blur', *args, **kwargs)

        self.main_layout = QVBoxLayout(self)
        self.spinbox     = QDoubleSpinBox(self)
        self.text        = QLabel(self, text = 'Coefficient')

        self.main_layout.addWidget(self.text,    alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.spinbox, alignment = Qt.AlignCenter)

    def get_params(self):
        return [self.spinbox.value()]