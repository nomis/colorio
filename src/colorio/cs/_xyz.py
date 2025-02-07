"""
XYZ colorspace.

https://en.wikipedia.org/wiki/CIE_1931_color_space
"""
import numpy as np
from numpy.typing import ArrayLike

from .._exceptions import ColorioError
from ._color_space import ColorSpace


class XYZ(ColorSpace):
    name = "XYZ"
    labels = ("X", "Y", "Z")
    k0 = None

    def __init__(self, scaling: float):
        if scaling not in [1, 100]:
            raise ColorioError("scaling needs to be 1 or 100.")

        self.scaling = scaling

    def from_xyz100(self, xyz: ArrayLike) -> np.ndarray:
        xyz = np.asarray(xyz)
        if self.scaling == 100:
            return xyz

        return xyz / 100

    def to_xyz100(self, xyz: ArrayLike) -> np.ndarray:
        xyz = np.asarray(xyz)
        if self.scaling == 100:
            return xyz
        return xyz * 100


class XYZ1(XYZ):
    name = "XYZ1"

    def __init__(self):
        super().__init__(1)


class XYZ100(XYZ):
    name = "XYZ100"

    def __init__(self):
        super().__init__(100)
