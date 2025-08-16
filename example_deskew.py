"""旋正倾斜图片，并保存
"""
import re
import numpy as np
from skimage import io
from skimage.color import rgb2gray
from skimage.transform import rotate

from deskew import determine_skew

in_path = '2.jpg'
out_path = re.sub(r'\.[^\.]+$', '_dsk.jpg', in_path)
image = io.imread(in_path)
grayscale = rgb2gray(image)
angle = determine_skew(grayscale)
rotated = rotate(image, angle, resize=True) * 255
io.imsave(out_path, rotated.astype(np.uint8))
