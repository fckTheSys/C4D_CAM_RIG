import math
import unittest

from curve_math import cubic_extrema_times


class CubicExtremaTests(unittest.TestCase):
    def test_horizontal(self):
        self.assertEqual(cubic_extrema_times(0, 1, 7, 7, .2, 0, -.2, 0), [])

    def test_monotonic(self):
        self.assertEqual(cubic_extrema_times(0, 1, 0, 1, .2, .1, -.2, -.1), [])

    def test_single_peak_linear_derivative(self):
        result = cubic_extrema_times(0, 1, 0, 0, 1/3, 1, -1/3, 1)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], .5)

    def test_narrow_two_reversals(self):
        # Both reversals fit between neighboring 120 Hz integration samples.
        start, duration = .001, .0001
        result = cubic_extrema_times(start, start+duration, 0, 0,
                                     duration/3, 1, -duration/3, -1)
        self.assertEqual(len(result), 2)
        expected = [(3-math.sqrt(3))/6, (3+math.sqrt(3))/6]
        for actual, u in zip(result, expected):
            self.assertAlmostEqual(actual, start+duration*u, places=14)

    def test_nonlinear_time_handles(self):
        # y extremum at u=.5; x(.5) is not the time midpoint.
        result = cubic_extrema_times(10, 14, 0, 0, .1, 1, -3, 1)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], 10+.375*.1+.375*1+.125*4)

    def test_endpoint_roots_excluded(self):
        self.assertEqual(cubic_extrema_times(0, 1, 0, 1, 0, 0, 0, 0), [])

    def test_scaled_values(self):
        base = cubic_extrema_times(0, 1, 0, 0, .3, 1, -.3, -1)
        self.assertEqual(base, cubic_extrema_times(0, 1, 0, 0, .3, 1e150, -.3, -1e150))
        self.assertEqual(base, cubic_extrema_times(0, 1, 0, 0, .3, 1e-150, -.3, -1e-150))

    def test_invalid_controls(self):
        for dt_right, dt_left in ((-.1, -.2), (1.1, -.2), (.2, .1), (.2, -1.1)):
            with self.assertRaises(ValueError):
                cubic_extrema_times(0, 1, 0, 1, dt_right, .1, dt_left, -.1)
        for end in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                cubic_extrema_times(0, end, 0, 1, .2, .1, -.2, -.1)


if __name__ == '__main__':
    unittest.main()
