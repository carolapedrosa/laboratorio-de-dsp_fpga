from PyQt5.QtWidgets import QWidget, QLabel, QDoubleSpinBox, QVBoxLayout, QHBoxLayout
import numpy as np
import cv2
import random
import bisect
from PyQt5.QtCore import Qt
from skimage.transform import downscale_local_mean
from PIL import Image, ImageEnhance

class Filter(QWidget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.hw   = False

    def apply(self, img):
        return img

    def __le__(self, other):
        return self.name <= other.name

    def __lt__(self, other):
        return self.name < other.name

    def __ge__(self, other):
        return self.name >= other.name

    def __gt__(self, other):
        return self.name > other.name

class HWFilter(Filter):
    MAX_KERNEL_SIZE = 11

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.hw   = True

        self.main_layout = QVBoxLayout(self)
        self.label       = QLabel(self, text = 'Kernel size')
        self.spinbox     = QDoubleSpinBox(self)

        self.main_layout.addWidget(self.label, alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.spinbox, alignment = Qt.AlignCenter)

        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(self.MAX_KERNEL_SIZE)
        self.spinbox.setSingleStep(1)

        self.last = 1

        self.spinbox.valueChanged.connect(self.set_new)

    def set_new(self, new):
        if new < self.last:
            if not new%1:
                self.last = max(1, new - 1)
                self.spinbox.setValue(self.last)
            else:
                self.last = new
        elif new > self.last:
            if not new%1:
                self.last = min(self.MAX_KERNEL_SIZE, new + 1)
                self.spinbox.setValue(self.last)
            else:
                self.last = new

    def get_kernel(self):
        return np.array([1])

class Identity(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Identity', *args, **kwargs)

    def apply(self, img):
        return img

class GaussianBlur(HWFilter):
    def __init__(self, *args, **kwargs):
        super().__init__('Gaussian blur', *args, **kwargs)
        self.flabel       = QLabel(self, text = 'Sigma')
        self.fspinbox     = QDoubleSpinBox(self)

        self.fspinbox.setMinimum(0.1)
        self.fspinbox.setMaximum(10)
        self.fspinbox.setSingleStep(0.1)

        self.fspinbox.setValue(1)

        self.main_layout.addWidget(self.flabel  , alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.fspinbox, alignment = Qt.AlignCenter)

    @staticmethod
    def gaussian_filter(k, sigma):
        def get_axis(x, y):
            return np.repeat([np.arange(x)], y, axis = 0).astype(float)

        x = get_axis(k, k)
        center = (k - 1)//2
        D = ((x.T - center)**2 + (x - center)**2)
        return 1/(2 * np.pi * sigma**2) * np.exp(-D/(2 * sigma**2))

    def get_kernel(self):
        k = self.gaussian_filter(int(self.spinbox.value()), self.fspinbox.value())
        return (k / abs(k.min())).round().astype(np.uint8)

class BoxBlur(HWFilter):
    def __init__(self, *args, **kwargs):
        super().__init__('Box blur', *args, **kwargs)

    def get_kernel(self):
        k = int(self.spinbox.value())
        return np.ones((k, k), dtype = np.uint8)

class RidgeDetection(HWFilter):
    def __init__(self, *args, **kwargs):
        super().__init__('Ridge Detection', *args, **kwargs)
        self.flabel       = QLabel(self, text = 'Center')
        self.fspinbox     = QDoubleSpinBox(self)

        self.fspinbox.setMinimum(0)
        self.fspinbox.setMaximum(255)
        self.fspinbox.setSingleStep(1)

        self.main_layout.addWidget(self.flabel  , alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.fspinbox, alignment = Qt.AlignCenter)

    def get_kernel(self):
        k = int(self.spinbox.value())
        res = np.full((k, k), -1)
        res[k//2, k//2] = int(self.fspinbox.value())
        return res

class Sharpen(HWFilter):
    def __init__(self, *args, **kwargs):
        super().__init__('Sharpen', *args, **kwargs)
        self.flabel       = QLabel(self, text = 'Center')
        self.fspinbox     = QDoubleSpinBox(self)

        self.fspinbox.setMinimum(0)
        self.fspinbox.setMaximum(255)
        self.fspinbox.setSingleStep(1)

        self.main_layout.addWidget(self.flabel  , alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.fspinbox, alignment = Qt.AlignCenter)

    def get_kernel(self):
        k = int(self.spinbox.value())

        res = np.full((k, k), -1)
        res[0, 0] = res[k-1, 0] = res[0, k-1] = res[k-1, k-1] = 0
        res[k//2, k//2] = int(self.fspinbox.value())
        return res

class Negative(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Negative', *args, **kwargs)

    def apply(self, img):
        norm = ((img - img.min()) / abs(img - img.min()).max() * 255).astype(np.uint8)
        
        if len(img.shape) == 1:
            print("Invalid image shape")
            return img

        if len(img.shape) == 2:
            return 255 - norm
        elif img.shape[2] <= 3:
            return 255 - norm
        else:
            return 255 - norm[:, :, :-1]

class SaltnPepper(Filter):

    MIN_CHANGE = 0.05
    MAX_CHANGE = 0.25

    def __init__(self, *args, **kwargs):
        super().__init__('Salt and pepper', *args, **kwargs)

    def apply(self, img):
        if len(img.shape) not in [2, 3]:
            print("Invalid image shape")
            return img

        if len(img.shape) == 2:
            img = img.reshape(*img.shape, 1)

        res = []
        row , col = img.shape[:2]

        tot = row * col
        number_of_pixels = random.randint(int(self.MIN_CHANGE*tot), int(self.MAX_CHANGE*tot))

        windices = [
            (random.randint(0, row-1), random.randint(0, col-1)) for _ in range(number_of_pixels)
        ]
        bindices = [
            (random.randint(0, row-1), random.randint(0, col-1)) for _ in range(number_of_pixels)
        ]

        for dim in range(img.shape[2]):
            _img = img[:, :, dim]
            if not abs(_img - _img.min()).max():
                continue

            _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)

            if dim >= 3:
                res.append(_img.reshape(*_img.shape, 1))
                continue

            for y_coord, x_coord in windices:
                # Color that pixel to white
                _img[y_coord][x_coord] = 255

            for y_coord, x_coord in bindices:
                # Color that pixel to black
                _img[y_coord][x_coord] = 0

            res.append(_img)
            res[-1] = res[-1].reshape(*res[-1].shape, 1)


        res = np.concatenate(tuple(res), axis = -1).astype(float)
        if res.shape[2] == 1:
            res = res.reshape(*res.shape[:2])
    
        return (res - res.min()) / abs(res - res.min()).max()

class Median(Filter):

    MAX_KERNEL_SIZE = 5

    def __init__(self, *args, **kwargs):
        super().__init__('Median', *args, **kwargs)

        self.main_layout = QVBoxLayout(self)
        self.label       = QLabel(self, text = 'Kernel size')
        self.spinbox     = QDoubleSpinBox(self)

        self.main_layout.addWidget(self.label, alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.spinbox, alignment = Qt.AlignCenter)

        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(self.MAX_KERNEL_SIZE)
        self.spinbox.setSingleStep(1)

        self.last = 1

        self.spinbox.valueChanged.connect(self.set_new)

    def set_new(self, new):
        if new < self.last:
            if not new%1:
                self.last = max(1, new - 1)
                self.spinbox.setValue(self.last)
            else:
                self.last = new
        elif new > self.last:
            if not new%1:
                self.last = min(self.MAX_KERNEL_SIZE, new + 1)
                self.spinbox.setValue(self.last)
            else:
                self.last = new

    def apply(self, img):
        try:
            return cv2.medianBlur(img, int(self.spinbox.value()))
        except Exception as e:
            print(e)
            return img

class Histogram(Filter):

    def __init__(self, *args, **kwargs):
        super().__init__('Histogram', *args, **kwargs)

    def apply(self, img):
        try:
            if len(img.shape) not in [2, 3]:
                print("Invalid image shape")
                return img

            if len(img.shape) == 2:
                img = img.reshape(*img.shape, 1)

            res = []

            for dim in range(img.shape[2]):
                _img = img[:, :, dim]
                if not abs(_img - _img.min()).max():
                    continue
                _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)

                res.append(np.hstack((_img, cv2.equalizeHist(_img))))
                res[-1] = res[-1].reshape(*res[-1].shape, 1)

            res = np.concatenate(tuple(res), axis = -1).astype(float)
            return (res - res.min()) / abs(res - res.min()).max()

        except Exception as e:
            print(e)
            return img

class ImAdjust(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('ImAdjust', *args, **kwargs)

        self.main_layout = QVBoxLayout(self)

        self.vinlayout      = QHBoxLayout()

        self.vinmin_layout  = QVBoxLayout()
        self.vin_min_label  = QLabel(self, text = r'Vin min')
        self.vin_min        = QDoubleSpinBox(self)
        self.vin_min.setMinimum(0)
        self.vin_min.setMaximum(255)
        self.vin_min.setSingleStep(1)
        self.vinmin_layout.addWidget(self.vin_min_label, alignment = Qt.AlignCenter)
        self.vinmin_layout.addWidget(self.vin_min, alignment = Qt.AlignCenter)

        self.vinmax_layout  = QVBoxLayout()
        self.vin_max_label  = QLabel(self, text = r'Vin max')
        self.vin_max        = QDoubleSpinBox(self)
        self.vin_max.setMinimum(1)
        self.vin_max.setMaximum(255)
        self.vin_max.setSingleStep(1)
        self.vinmax_layout.addWidget(self.vin_max_label, alignment = Qt.AlignCenter)
        self.vinmax_layout.addWidget(self.vin_max, alignment = Qt.AlignCenter)

        self.vinlayout.addLayout(self.vinmin_layout)
        self.vinlayout.addLayout(self.vinmax_layout)

        self.voutlayout  = QHBoxLayout()

        self.voutmin_layout  = QVBoxLayout()
        self.vout_min_label  = QLabel(self, text = r'Vout min')
        self.vout_min        = QDoubleSpinBox(self)
        self.vout_min.setMinimum(0)
        self.vout_min.setMaximum(255)
        self.vout_min.setSingleStep(1)
        self.voutmin_layout.addWidget(self.vout_min_label, alignment = Qt.AlignCenter)
        self.voutmin_layout.addWidget(self.vout_min, alignment = Qt.AlignCenter)
        
        self.voutmax_layout  = QVBoxLayout()
        self.vout_max_label  = QLabel(self, text = r'Vout max')
        self.vout_max        = QDoubleSpinBox(self)
        self.vout_max.setMinimum(1)
        self.vout_max.setMaximum(255)
        self.vout_max.setSingleStep(1)
        self.voutmax_layout.addWidget(self.vout_max_label, alignment = Qt.AlignCenter)
        self.voutmax_layout.addWidget(self.vout_max, alignment = Qt.AlignCenter)

        self.voutlayout.addLayout(self.voutmin_layout)
        self.voutlayout.addLayout(self.voutmax_layout)

        self.tollayout   = QVBoxLayout()
        self.tol_label   = QLabel(self, text = 'Tol')
        self.tol         =  QDoubleSpinBox(self) 
        self.tol.setMinimum(0)
        self.tol.setMaximum(100)
        self.tol.setSingleStep(1)
        self.tollayout.addWidget(self.tol_label, alignment = Qt.AlignCenter)
        self.tollayout.addWidget(self.tol, alignment = Qt.AlignCenter)

        self.main_layout.addLayout(self.vinlayout)
        self.main_layout.addLayout(self.voutlayout)
        self.main_layout.addLayout(self.tollayout)

        self.vin_min.valueChanged.connect(self.adapt_max_vin)
        self.vin_max.valueChanged.connect(self.adapt_min_vin)

        self.vout_min.valueChanged.connect(self.adapt_max_vout)
        self.vout_max.valueChanged.connect(self.adapt_min_vout)

        self.tol.valueChanged.connect(self.toggle_vin)

    def adapt_min_vin(self, new_max):
        self.vin_min.setMaximum(max(0, self.vin_max.value() - 1))

    def adapt_max_vin(self, new_min):
        self.vin_max.setMinimum(min(self.vin_min.value() + 1, 255))

    def adapt_min_vout(self, new_max):
        self.vout_min.setMaximum(max(0, self.vout_max.value() - 1))

    def adapt_max_vout(self, new_min):
        self.vout_max.setMinimum(min(self.vout_min.value() + 1, 255))

    def toggle_vin(self, new_value):
        if new_value > 0:
            self.vin_min_label.hide()
            self.vin_min.hide()
            self.vin_max_label.hide()
            self.vin_max.hide()
        else:
            self.vin_min_label.show()
            self.vin_min.show()
            self.vin_max_label.show()
            self.vin_max.show()

    def apply(self, img):
        # def imadjust(src, tol=1, vin=[0,255], vout=(0,255)):
        # src : input one-layer image (numpy array)
        # tol : tolerance, from 0 to 100.
        # vin  : src image bounds
        # vout : dst image bounds
        # return : output img

        if len(img.shape) not in [2, 3]:
            print("Invalid image shape")
            return img

        if len(img.shape) == 2:
            img = img.reshape(*img.shape, 1)

        res = np.zeros(img.shape, dtype = np.uint8)

        res = []

        for dim in range(img.shape[2]):
            _img = img[:, :, dim]
            if not abs(_img - _img.min()).max():
                continue
            _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)

            vin = [int(self.vin_min.value()), int(self.vin_max.value())]
            vout = [int(self.vout_min.value()), int(self.vout_max.value())]
            tol = int(self.tol.value())

            tol = max(0, min(100, tol))

            if tol > 0:
                # Compute in and out limits
                # Histogram
                hist = np.histogram(_img, bins=list(range(256)),range=(0,255))[0]

                # Cumulative histogram
                cum = hist.copy()
                for i in range(1, 255): cum[i] = cum[i - 1] + hist[i]

                # Compute bounds
                total = _img.shape[0] * _img.shape[1]
                low_bound = total * tol / 100
                upp_bound = total * (100 - tol) / 100
                vin[0] = bisect.bisect_left(cum, low_bound)
                vin[1] = bisect.bisect_left(cum, upp_bound)

            # Stretching
            scale = (vout[1] - vout[0]) / (vin[1] - vin[0])
            vs = _img-vin[0]
            vs[_img<vin[0]]=0
            vd = vs*scale+0.5 + vout[0]
            vd[vd>vout[1]] = vout[1]

            res.append(vd)
            res[-1] = res[-1].reshape(*res[-1].shape, 1)

        res = np.concatenate(tuple(res), axis = -1).astype(float)

        if res.shape[2] == 1:
            res = res.reshape(*res.shape[:2])

        return (res - res.min()) / abs(res - res.min()).max()

class BitPlaneSlicing(Filter):

    def __init__(self, *args, **kwargs):
        super().__init__('Bit plane slicing', *args, **kwargs)

    def apply(self, img):
        try:
            if len(img.shape) not in [2, 3]:
                print("Invalid image shape")
                return img

            if len(img.shape) == 2:
                img = img.reshape(*img.shape, 1)

            res = []

            for dim in range(img.shape[2]):
                _img = img[:, :, dim]
                if not abs(_img - _img.min()).max():
                    continue
                _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)

                lst = []
                for i in range(img.shape[0]):
                    for j in range(img.shape[1]):
                        lst.append(np.binary_repr(_img[i][j] ,width=8)) # width = no. of bits

                # We have a list of strings where each string represents binary pixel value. To extract bit planes we need to iterate over the strings and store the characters corresponding to bit planes into lists.
                # Multiply with 2^(n-1) and reshape to reconstruct the bit image.
                eight_bit_img = (np.array([int(i[0]) for i in lst],dtype = np.uint8) * 128).reshape(*_img.shape)
                seven_bit_img = (np.array([int(i[1]) for i in lst],dtype = np.uint8) * 64).reshape(*_img.shape)
                six_bit_img = (np.array([int(i[2]) for i in lst],dtype = np.uint8) * 32).reshape(*_img.shape)
                five_bit_img = (np.array([int(i[3]) for i in lst],dtype = np.uint8) * 16).reshape(*_img.shape)
                four_bit_img = (np.array([int(i[4]) for i in lst],dtype = np.uint8) * 8).reshape(*_img.shape)
                three_bit_img = (np.array([int(i[5]) for i in lst],dtype = np.uint8) * 4).reshape(*_img.shape)
                two_bit_img = (np.array([int(i[6]) for i in lst],dtype = np.uint8) * 2).reshape(*_img.shape)
                one_bit_img = (np.array([int(i[7]) for i in lst],dtype = np.uint8) * 1).reshape(*_img.shape)

                #Concatenate these images for ease of display using cv2.hconcat()
                finalr = cv2.hconcat([eight_bit_img,seven_bit_img,six_bit_img,five_bit_img])
                finalv =cv2.hconcat([four_bit_img,three_bit_img,two_bit_img,one_bit_img])

                # Vertically concatenate
                final = cv2.vconcat([finalr,finalv])
                res.append(final)
                res[-1] = res[-1].reshape(*res[-1].shape, 1)

            res = np.concatenate(tuple(res), axis = -1).astype(float)
            return (res - res.min()) / abs(res - res.min()).max()

        except Exception as e:
            print(e)
            return img

class BrightnessEnhancer(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Brightness Enhancer', *args, **kwargs)

        self.main_layout = QVBoxLayout(self)
        self.factor      = QDoubleSpinBox(self)

        self.factor.setMinimum(0)
        self.factor.setMaximum(1)
        self.factor.setSingleStep(0.05)

        self.main_layout.addWidget(self.factor, alignment = Qt.AlignCenter)

    def apply(self, img):
        try:
            if len(img.shape) not in [2, 3]:
                print("Invalid image shape")
                return img

            if len(img.shape) == 2:
                res = img.reshape(*img.shape, 1)

            else:
                res = img

            res = ((res - res.min()) / abs(res - res.min()).max() * 255).astype(np.uint8)
            return ImageEnhance.Brightness(Image.fromarray(res)).enhance(self.factor.value())

        except Exception as e:
            print(e)
            return img

class ColorLimitation(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Color Limitation', *args, **kwargs)

        self.main_layout = QVBoxLayout(self)
        self.ncolors     = QDoubleSpinBox(self)
        self.label       = QLabel(self, text = 'N Colors')

        self.ncolors.setMinimum(1)
        self.ncolors.setMaximum(255)
        self.ncolors.setSingleStep(1)

        self.main_layout.addWidget(self.label, alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.ncolors, alignment = Qt.AlignCenter)

    def apply(self, img):
        try:
            if len(img.shape) not in [2, 3]:
                print("Invalid image shape")
                return img

            if len(img.shape) == 2:
                res = img.reshape(*img.shape, 1)

            else:
                res = img

            res = ((res - res.min()) / abs(res - res.min()).max() * 255).astype(np.uint8)
            
            return Image.fromarray(res).quantize(int(self.ncolors.value()))

        except Exception as e:
            print(e)
            return img

class Downscaler(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Downscaler', *args, **kwargs)

        self.main_layout = QVBoxLayout(self)
        self.factor      = QDoubleSpinBox(self)
        self.label       = QLabel(self, text = 'Factor')

        self.factor.setMinimum(1)
        self.factor.setMaximum(100)
        self.factor.setSingleStep(1)

        self.main_layout.addWidget(self.label, alignment = Qt.AlignCenter)
        self.main_layout.addWidget(self.factor, alignment = Qt.AlignCenter)

    def apply(self, img):
        try:
            if len(img.shape) not in [2, 3]:
                print("Invalid image shape")
                return img

            if len(img.shape) == 2:
                img = img.reshape(*img.shape, 1)

            res = []

            factor = int(self.factor.value())
            for dim in range(img.shape[2]):
                _img = img[:, :, dim]
                _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)
                res.append(downscale_local_mean(_img, factors=(factor, factor)).astype(int))
                res[-1] = res[-1].reshape(*res[-1].shape, 1)

            res = np.concatenate(tuple(res), axis = -1).astype(float)
            return (res - res.min()) / abs(res - res.min()).max()

        except Exception as e:
            print(e)
            return img

class Logarithmic(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Logarithmic', *args, **kwargs)

    def apply(self, img):
        try:
            if len(img.shape) not in [2, 3]:
                print("Invalid image shape")
                return img

            if len(img.shape) == 2:
                img = img.reshape(*img.shape, 1)

            res = []

            for dim in range(img.shape[2]):
                _img = img[:, :, dim]
                _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(float)
                 # Apply log transformation method
                c = 255 / np.log(1 + np.max(_img))

                log_image = c * (np.log(_img + 1))

                # Specify the data type so that
                # float value will be converted to int
                res.append(np.array(log_image, dtype = np.uint8))
                res[-1] = res[-1].reshape(*res[-1].shape, 1)

            res = np.concatenate(tuple(res), axis = -1).astype(float)
            return (res - res.min()) / abs(res - res.min()).max()

        except Exception as e:
            print(e)
            return img
