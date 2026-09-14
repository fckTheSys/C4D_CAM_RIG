"""Independent mathematical checks, runnable with Python unittest."""
import importlib.util
import math
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location('simple_camera_motion_math',
                                             Path(__file__).with_name('motion_math.py'))
motion = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(motion)


class IntegrationTests(unittest.TestCase):
    def test_affine_partial_edges_and_reverse(self):
        a, b = -0.123, 1.017
        expected = (b*b + 3*b) - (a*a + 3*a)
        self.assertAlmostEqual(motion.integrate(lambda t: 2*t+3, a, b), expected, places=12)
        self.assertEqual(motion.integrate(lambda t: 2*t+3, b, a),
                         -motion.integrate(lambda t: 2*t+3, a, b))

    def test_quadratic_convergence_against_antiderivative(self):
        expected = 1.013 ** 3 / 3
        coarse = abs(motion.integrate(lambda t: t*t, 0, 1.013, .02) - expected)
        fine = abs(motion.integrate(lambda t: t*t, 0, 1.013, .01) - expected)
        self.assertLess(fine, coarse * .27)
        self.assertLess(fine, 0.000018)

    def test_reverse_travel_integrates_positive_distance(self):
        # Position t*(1-t) reverses at .5: total travel is .5, net travel zero.
        self.assertAlmostEqual(motion.integrate(lambda t: abs(1-2*t), 0, 1), .5, places=12)

    def test_invalid_input(self):
        for step in (0, -1, math.nan):
            with self.assertRaises(ValueError):
                motion.integrate(lambda t: 1, 0, 1, step)
        with self.assertRaises(ValueError):
            motion.integrate(lambda t: math.inf, 0, 1)


class NoiseTests(unittest.TestCase):
    def test_random_access_seed_and_bounds(self):
        points = [i / 17 for i in range(-200, 201)]
        expected = {x: motion.noise(x, 57) for x in points}
        for x in reversed(points):
            self.assertEqual(motion.noise(x, 57), expected[x])
            self.assertLessEqual(abs(expected[x]), 1)
        self.assertNotEqual(motion.noise(.31, 57), motion.noise(.31, 58))

    def test_continuity_at_integer_boundaries(self):
        for x in range(-5, 6):
            self.assertLess(abs(motion.noise(x-1e-5, 9)-motion.noise(x+1e-5, 9)), 1e-10)


class WalkTests(unittest.TestCase):
    def test_zero_and_rest(self):
        self.assertEqual(motion.walk(.8, 100, 0, 5, 2, .5), (0, 0, 0))
        self.assertEqual(motion.walk(.8, 0, 1, 5, 2, .5), (0, 0, 0))

    def test_step_and_pair_periods(self):
        first = motion.walk(.7, 100, 1, 5, 2, .4)
        step = motion.walk(.7+math.pi, 100, 1, 5, 2, .4)
        pair = motion.walk(.7+2*math.pi, 100, 1, 5, 2, .4)
        self.assertAlmostEqual(first[1], step[1], places=12)
        self.assertAlmostEqual(first[0], -step[0], places=12)
        self.assertAlmostEqual(first[2], -step[2], places=12)
        for a, b in zip(first, pair):
            self.assertAlmostEqual(a, b, places=12)

    def test_speed_gate_and_units(self):
        full = motion.walk(math.pi/2, 100, 1, 5, 90, 1)
        half = motion.walk(math.pi/2, 50, 1, 5, 90, 1)
        self.assertAlmostEqual(full[2], math.pi/2)
        for a, b in zip(full, half):
            self.assertAlmostEqual(a*.5, b)
        self.assertEqual(full, motion.walk(math.pi/2, 200, 1, 5, 90, 1))

    def test_validation(self):
        for arguments in ((0, -1, 1, 1, 1, .5), (0, 1, 1, 1, 1, 2),
                          (math.nan, 1, 1, 1, 1, .5)):
            with self.assertRaises(ValueError):
                motion.walk(*arguments)


if __name__ == '__main__':
    unittest.main()
