import json
import pathlib

import numpy as np

from . import observers

# The "standard" 2 degree observer (CIE 1931). From
# <https://github.com/njsmith/colorspacious/blob/master/colorspacious/illuminants.py>
whitepoints_cie1931 = {
    "A": np.array([109.850, 100, 35.585]),
    "C": np.array([98.074, 100, 118.232]),
    "D50": np.array([96.422, 100, 82.521]),
    "D55": np.array([95.682, 100, 92.149]),
    "D65": np.array([95.047, 100, 108.883]),
    "D75": np.array([94.972, 100, 122.638]),
}

# The "supplementary" 10 degree observer (CIE 1964). From
# <https://github.com/njsmith/colorspacious/blob/master/colorspacious/illuminants.py>
whitepoints_cie1964 = {
    "A": np.array([111.144, 100, 35.200]),
    "C": np.array([97.285, 100, 116.145]),
    "D50": np.array([96.720, 100, 81.427]),
    "D55": np.array([95.799, 100, 90.926]),
    "D65": np.array([94.811, 100, 107.304]),
    "D75": np.array([94.416, 100, 120.641]),
}


def spectrum_to_xyz100(spectrum, observer):
    """Computes the tristimulus values XYZ from a given spectrum for a given observer
    via

      X_i = sum_lambda spectrum_i(lambda) * observer_i(lambda) delta_lambda.

    The technical report CIE Standard Illuminants for Colorimetry, 1999, section 7
    ("Recommendations concerning the calculation of tristimulus values and chromaticity
    coordinates"), gives a recommendation on how to perform the computation:

    > The CIE Standard (CIE, 1986a) on standard colorimetric observers recommends that
    > the CIE tristimulus values of a colour stimulus be obtained by multiplying at each
    > wavelength the value of the colour stimulus function phi_lambda(lambda) by that of
    > each of the CIE colour-matching functions and integrating each set of products
    > over the wavelength range corresponding to the entire visible spectrum, 360 nm to
    > 830 nm. The integration can be carried out by numerical summation at wavelength
    > intervals, delta lmbda, equal to 1 nm.

    Note that the above sum is supposed to approximate the integral

      int_lambda spectrum_i(lambda) * observer_i(lambda) dlambda.

    It gets a little tricky when asking what the correct value is for monochromatic
    light. Mathematically, one would insert a scaled delta distribution for spectrum_i
    to get a * observer_i(lambda0). It would be easy to assume that you do the same in
    the corresponding sum above, but there you get

      a * observer_i(lambda0) * delta_lambda.

    So just using a unity vector for spectrum_i in the sum does _not_ correspond to
    monochromatic light, but rather light of a very small bandwidth (between
    lambda0 - delta_lambda and lambda0 + delta_lambda).

    To get a more consistent view on things, it is useful to look at observer_i as a
    piecewise linear function, and the spectrum vector as a piecewise constant function.
    The above sum accurately represents the integral of the product of the two.

    Note that any constant factor (like delta_lambda) gets canceled out in x and y (of
    xyY), so being careless might not be punished in all applications.
    """
    lambda_o, data_o = observer
    lambda_s, data_s = spectrum

    # form the union of lambdas
    lmbda = np.sort(np.unique(np.concatenate([lambda_o, lambda_s])))

    # The technical document prescribes that the integration be performed over
    # the wavelength range corresponding to the entire visible spectrum, 360 nm
    # to 830 nm.
    assert lmbda[0] < 361e-9
    assert lmbda[-1] > 829e-9

    # interpolate data
    idata_o = np.array([np.interp(lmbda, lambda_o, dt) for dt in data_o])
    # The technical report specifies the interpolation techniques, too:
    # ```
    # Use one of the four following methods to calculate needed but unmeasured
    # values of phi(l), R(l) or tau(l) within the range of measurements:
    #   1) the third-order polynomial interpolation (Lagrange) from the four
    #      neighbouring data points around the point to be interpolated, or
    #   2) cubic spline interpolation formula, or
    #   3) a fifth order polynomial interpolation formula from the six
    #      neighboring data points around the point to be interpolated, or
    #   4) a Sprague interpolation (see Seve, 2003).
    # ```
    # Well, don't do that but simply use linear interpolation now. We only use the
    # midpoint rule for integration anyways.
    idata_s = np.interp(lmbda, lambda_s, data_s)

    # step sizes
    delta = np.zeros(len(lmbda))
    diff = lmbda[1:] - lmbda[:-1]
    delta[1:] += diff
    delta[:-1] += diff
    delta /= 2

    values = np.dot(idata_o, idata_s * delta)

    return values * 100


def white_point(illuminant, observer=observers.cie_1931_2()):
    """From <https://en.wikipedia.org/wiki/White_point>:
    The white point of an illuminant is the chromaticity of a white object under the
    illuminant.
    """
    values = spectrum_to_xyz100(illuminant, observer)
    # normalize for relative luminance, Y=100
    values /= values[1]
    values *= 100
    return values


def planckian_radiator(temperature):
    lmbda = 1.0e-9 * np.arange(300, 831)
    # light speed
    c = 299792458.0
    # Plank constant
    h = 6.62607004e-34
    # Boltzmann constant
    k = 1.38064852e-23
    c1 = 2 * np.pi * h * c ** 2
    c2 = h * c / k
    return lmbda, c1 / lmbda ** 5 / (np.exp(c2 / lmbda / temperature) - 1)


def a(interval=1.0e-9):
    """CIE Standard Illuminants for Colorimetry, 1999:
    CIE standard illuminant A is intended to represent typical, domestic,
    tungsten-filament lighting. Its relative spectral power distribution is that of a
    Planckian radiator at a temperature of approximately 2856 K. CIE standard illuminant
    A should be used in all applications of colorimetry involving the use of
    incandescent lighting, unless there are specific reasons for using a different
    illuminant.
    """
    # https://en.wikipedia.org/wiki/Standard_illuminant#Illuminant_A
    lmbda = np.arange(300e-9, 831e-9, interval)
    c2 = 1.435e-2
    color_temp = 2848
    np.exp(c2 / (color_temp * 560e-9))
    vals = (
        100
        * (560e-9 / lmbda) ** 5
        * (
            (np.exp(c2 / (color_temp * 560e-9)) - 1)
            / (np.exp(c2 / (color_temp * lmbda)) - 1)
        )
    )
    return lmbda, vals


def d(nominal_temperature: float):
    """CIE D-series illuminants.

    The technical report `Colorimetry, 3rd edition, 2004` gives the data for D50, D55,
    and D65 explicitly, but also explains how it's computed for S0, S1, S2. Values are
    given at 5nm resolution in the document, but really every other value is just
    interpolated. Hence, only provide 10 nm data here.
    """
    # From CIE 15:2004. Colorimetry, 3rd edition, 2004 (page 69, note 5):
    #
    # The method required to calculate the values for the relative spectral power
    # distributions of illuminants D50, D55, D65, and D75, in Table T.1 is as follows
    #   1. Multiply the nominal correlated colour temperature (5000 K, 5500 K, 6500 K or
    #   7500 K) by 1,4388/1,4380.
    #   2. Calculate XD and YD using the equations given in the text.
    #   3. Calculate M1 and M2 using the equations given in the text.
    #   4. Round M1 and M2 to three decimal places.
    #   5. Calculate S(lambda) every 10 nm by
    #        S(lambda) = S0(lambda) + M1 S1(lambda) + M2 S2(lambda)
    #      using values of S0(lambda), S1(lambda) and S2(lambda) from Table T.2.
    #   6. Interpolate the 10 nm values of S(lambda) linearly to obtain values at
    #   intermediate wavelengths.
    tcp = 1.4388e-2 / 1.4380e-2 * nominal_temperature

    if 4000 <= tcp <= 7000:
        xd = ((-4.6070e9 / tcp + 2.9678e6) / tcp + 0.09911e3) / tcp + 0.244063
    else:
        assert 7000 < tcp <= 25000
        xd = ((-2.0064e9 / tcp + 1.9018e6) / tcp + 0.24748e3) / tcp + 0.237040

    yd = (-3.000 * xd + 2.870) * xd - 0.275

    m1 = (-1.3515 - 1.7703 * xd + 5.9114 * yd) / (0.0241 + 0.2562 * xd - 0.7341 * yd)
    m2 = (+0.0300 - 31.4424 * xd + 30.0717 * yd) / (0.0241 + 0.2562 * xd - 0.7341 * yd)

    m1 = np.around(m1, decimals=3)
    m2 = np.around(m2, decimals=3)

    this_dir = pathlib.Path(__file__).resolve().parent
    with open(this_dir / "data/illuminants/d.json") as f:
        data = json.load(f)

    print(data)
    lmbda = np.linspace(*data["lambda"], data["num"])
    s = np.asarray(data["s"])

    return lmbda, s[0] + m1 * s[1] + m2 * s[2]


def d50():
    """CIE illuminant D50, mid-morning/mid-afternoon daylight, at 10nm resolution."""
    return d(5000)


def d55():
    """CIE illuminant D55, mid-morning/mid-afternoon daylight, at 10nm resolution."""
    return d(5500)


def d65():
    """CIE standard illuminant D65, sampled at 10nm intervals."""
    return d(6500)


def d75():
    """CIE illuminant D75"""
    return d(7500)


def e():
    """This is a hypothetical reference radiator. All wavelengths in CIE illuminant E
    are weighted equally with a relative spectral power of 100.0.
    """
    lmbda = 1.0e-9 * np.arange(300, 831)
    data = np.full(lmbda.shape, 100.0)
    return lmbda, data


def f2():
    this_dir = pathlib.Path(__file__).resolve().parent
    with open(this_dir / "data/illuminants/f2.json") as f:
        data = json.load(f)
    return np.linspace(*data["lambda"], data["num"]), np.array(data["values"])
