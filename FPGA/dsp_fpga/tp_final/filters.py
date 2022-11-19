from PyQt5.QtWidgets import QWidget, QLabel, QDoubleSpinBox, QVBoxLayout, QHBoxLayout
import numpy as np
import cv2
import random
import bisect
from PyQt5.QtCore import Qt
from skimage.transform import downscale_local_mean
from PIL import Image

class Filter(QWidget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.hw   = False

    def apply(self, img):
        return img

class HWFilter(Filter):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.hw   = True

    def get_kernel(self):
        return np.array([1])

class Identity(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__('Identity', *args, **kwargs)

    def apply(self, img):
        return img

class GaussianBlur(HWFilter):
    MAX_KERNEL_SIZE = 11

    def __init__(self, *args, **kwargs):
        super().__init__('Gaussian blur', *args, **kwargs)

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
        # Armar el kernel en función de int(self.spinbox.value())
        return np.array([
            [1, 4, 7, 10, 7, 4, 1],
            [4, 12, 26, 33, 26, 12, 4],
            [7, 26, 55, 71, 55, 26, 7],
            [10, 33, 71, 91, 71, 33, 10],
            [7, 26, 55, 71, 55, 26, 7],
            [4, 12, 26, 33, 26, 12, 4],
            [1, 4, 7, 10, 7, 4, 1],
        ])

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

        res = np.zeros(img.shape, dtype = np.uint8)
        for dim in range(img.shape[2]):
            _img = img[:, :, dim]

            _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)

            # Getting the dimensions of the image
            row , col = _img.shape

            # Randomly pick some pixels in the
            # image for coloring them white
            tot = len(_img.reshape(-1))
            number_of_pixels = random.randint(int(self.MIN_CHANGE*tot), int(self.MAX_CHANGE*tot))
            for i in range(number_of_pixels):

                # Pick a random y coordinate
                y_coord=random.randint(0, row - 1)

                # Pick a random x coordinate
                x_coord=random.randint(0, col - 1)

                # Color that pixel to white
                _img[y_coord][x_coord] = 255

            # Randomly pick some pixels in
            # the image for coloring them black
            number_of_pixels = random.randint(int(self.MIN_CHANGE*tot), int(self.MAX_CHANGE*tot))
            for i in range(number_of_pixels):

                # Pick a random y coordinate
                y_coord=random.randint(0, row - 1)

                # Pick a random x coordinate
                x_coord=random.randint(0, col - 1)

                # Color that pixel to black
                _img[y_coord][x_coord] = 0

            res[:, :, dim] += _img


        if res.shape[2] == 1:
            res = res.reshape(*res.shape[:2])
    
        res = res.astype(float)

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
        self.tol.setMinimum(1)
        self.tol.setMaximum(255)
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

    def adapt_min_vin(self, new_max):
        self.vin_min.setMaximum(max(0, self.vin_max.value() - 1))

    def adapt_max_vin(self, new_min):
        self.vin_max.setMinimum(min(self.vin_min.value() + 1, 255))

    def adapt_min_vout(self, new_max):
        self.vout_min.setMaximum(max(0, self.vout_max.value() - 1))

    def adapt_max_vout(self, new_min):
        self.vout_max.setMinimum(min(self.vout_min.value() + 1, 255))

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
        vin = [int(self.vin_min.value()), int(self.vin_max.value())]
        vout = [int(self.vout_min.value()), int(self.vout_max.value())]
        tol = int(self.tol.value())

        for dim in range(img.shape[2]):
            _img = img[:, :, dim]
            _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)

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
            dst = vd

            res[:, :, dim] += _img

        if res.shape[2] == 1:
            res = res.reshape(*res.shape[:2])
    
        res = res.astype(float)
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

# class BrightnessEnhancer(Filter):
#     def __init__(self, *args, **kwargs):
#         super().__init__('Brightness Enhancer', *args, **kwargs)

#         self.main_layout = QVBoxLayout(self)
#         self.factor      = QDoubleSpinBox(self)

#         self.factor.setMinimum(0)
#         self.factor.setMaximum(1)
#         self.factor.setSingleStep(0.05)

#         self.main_layout.addWidget(self.factor, alignment = Qt.AlignCenter)

#     def apply(self, img):
#         try:
#             if len(img.shape) not in [2, 3]:
#                 print("Invalid image shape")
#                 return img

#             if len(img.shape) == 2:
#                 img = img.reshape(*img.shape, 1)

#             res = []

#             for dim in range(img.shape[2]):
#                 _img = img[:, :, dim]
#                 _img = ((_img - _img.min()) / abs(_img - _img.min()).max() * 255).astype(np.uint8)

#                 res.append(encancher.enhance(factor))
#                 def brightness_enhancer(im, factor= 0.5):
#   im_output = enhancer.enhance(factor)
#   return im_output

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
            
            elif img.shape[2] > 3:
                res = img[:, :, :3]

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
            