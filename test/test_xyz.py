# -*- coding: utf-8 -*-
#
import numpy
import pytest

import colorio


@pytest.mark.parametrize('xyz', [
    numpy.random.rand(3),
    numpy.random.rand(3, 7),
    ])
def test_conversion(xyz):
    colorspace = colorio.XYZ()
    out = colorspace.to_xyz(colorspace.from_xyz(xyz))
    assert numpy.all(abs(xyz - out) < 1.0e-14)
    return
