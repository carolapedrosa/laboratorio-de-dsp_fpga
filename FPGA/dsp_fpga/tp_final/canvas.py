from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.pyplot import imread

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from copy import deepcopy
import numpy as np

class Canvas(QWidget):

    def __init__(self, naxes, *args, titles = None, distribution = 'h', **kwargs):
        super().__init__(*args, **kwargs)

        def get_ax(i):
            if distribution == 'h':
                arg = (1, naxes, i + 1)
            else:
                arg = (naxes, 1, i + 1)

            return self.figure.add_subplot(*arg)

        self.Canvas     = QVBoxLayout(self)
        self.figure     = Figure(tight_layout = True)
        self.fcanvas    = FigureCanvas(self.figure)
        self.axes       = [get_ax(i) for i in range(naxes)]
        self.ini_titles = deepcopy(titles) or [''] * naxes
        self.titles     = deepcopy(self.ini_titles)
        self.images     = [None] * naxes

        self.Canvas.addWidget(NavigationToolbar(self.fcanvas, self), alignment = Qt.AlignCenter)
        self.Canvas.addWidget(self.fcanvas)

        self.clear()

    def plot(self, which, image, *args, **kwargs):
        if isinstance(which, (tuple, list)):
            which = list(which)
        else:
            which = [which]

        if isinstance(image, str):
            img = imread(image)
        else:
            img = image

        if 'cmap' in kwargs:
            cmap = kwargs.pop('cmap')
        else:
            if len(np.asarray(img).shape) < 3:
                cmap = 'gray'
            else:
                cmap = None

        for w in which:
            self.setup_ax(w, clear_title = False)
            self.axes[w].imshow(img, *args, cmap = cmap, **kwargs)
            self.images[w] = img

        self.fcanvas.draw()

    def clear(self):
        for i in range(len(self.axes)):
            self.setup_ax(i)

        self.fcanvas.draw()
        self.images = [None] * len(self.axes)

    def setup_ax(self, i, clear_title = True):
        self.axes[i].clear()
        self.axes[i].axis('off')

        if clear_title:
            self.titles[i] = self.ini_titles[i]

        self.axes[i].set_title(self.titles[i])

    def save(self, filename):
        self.figure.savefig(filename)

    def change_title(self, which, title):
        self.titles[which] = title