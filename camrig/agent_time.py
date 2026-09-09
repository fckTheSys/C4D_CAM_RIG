"""Exact rational host times, avoiding BaseTime's frame overload rounding."""
from fractions import Fraction
import math
import c4d

def time_at(value, fps=1):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('INVALID_TIME: expected a finite number')
    if fps <= 0:
        raise ValueError('INVALID_TIME: fps must be positive')
    seconds = Fraction(str(value)) / fps
    seconds = seconds.limit_denominator(120000000)
    return c4d.BaseTime(seconds.numerator, seconds.denominator)
