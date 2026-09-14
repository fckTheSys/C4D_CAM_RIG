"""Pure effect contracts; these tests do not prove Cinema 4D evaluation order."""
import math
import unittest

try:
    from . import effects_math as fx
except ImportError:
    import effects_math as fx


class NoiseTests(unittest.TestCase):
    def test_arbitrary_order_and_repeat_are_identical(self):
        times = [-104.125, -1.0, -0.0001, 0.0, 0.123456, 12.875, 10000.5]
        expected = {t: fx.noise(t, 83) for t in times}
        for t in reversed(times):
            self.assertEqual(fx.noise(t, 83), expected[t])
        self.assertNotEqual(fx.noise(0.123456, 83), fx.noise(0.123456, 84))

    def test_bounds_including_negative_coordinates(self):
        for seed in (-912, 0, 42):
            for index in range(-1000, 1001):
                self.assertLessEqual(abs(fx.noise(index / 37.0, seed)), 1.0)

    def test_lattice_has_continuous_value_slope_and_curvature(self):
        h = 0.0001
        for seed in (0, 71):
            for knot in range(-5, 6):
                f0 = fx.noise(knot, seed)
                fm, fp = fx.noise(knot - h, seed), fx.noise(knot + h, seed)
                self.assertAlmostEqual(fm, f0, delta=3e-10)
                self.assertAlmostEqual(fp, f0, delta=3e-10)
                self.assertAlmostEqual((fp - fm) / (2 * h), 0.0, delta=1e-6)
                self.assertAlmostEqual((fp - 2 * f0 + fm) / h**2, 0.0, delta=0.01)

    def test_invalid_input_is_rejected(self):
        for x in (math.inf, -math.inf, math.nan):
            with self.assertRaises(ValueError):
                fx.noise(x, 1)
        for seed in (True, 1.5, '1'):
            with self.assertRaises(ValueError):
                fx.noise(0, seed)


class SpringTests(unittest.TestCase):
    def assertVectorAlmostEqual(self, actual, expected, places=10):
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=places)

    def test_artist_parameter_range_and_clamp(self):
        self.assertEqual(fx.parameters(-10, -10), fx.parameters(0, 0))
        self.assertEqual(fx.parameters(110, 110), fx.parameters(100, 100))
        self.assertAlmostEqual(fx.parameters(0, 0)[0], math.pi)
        self.assertAlmostEqual(fx.parameters(100, 100)[0], math.pi * 10)
        self.assertEqual(fx.parameters(100, 100)[1], 1.0)

    def test_equilibrium_and_zero_time(self):
        p, v = (12.0, -4.0, 8.0), (0.0, 0.0, 0.0)
        for damping in (0, 65, 100):
            args = fx.parameters(60, damping)
            actual = fx.step_vector(p, v, p, p, 2.0, *args)
            self.assertVectorAlmostEqual(actual[0], p)
            self.assertVectorAlmostEqual(actual[1], v)
            self.assertEqual(fx.step_vector(p, v, p, (100, 100, 100), 0, *args), (p, v))

    def test_linear_target_steady_lag(self):
        omega, zeta = fx.parameters(60, 65)
        target0, velocity, dt = (2.0, -6.0, 0.0), (10.0, -5.0, 3.0), 0.37
        target1 = tuple(x + speed * dt for x, speed in zip(target0, velocity))
        position = tuple(x - 2 * zeta * speed / omega for x, speed in zip(target0, velocity))
        p, v = fx.step_vector(position, velocity, target0, target1, dt, omega, zeta)
        self.assertVectorAlmostEqual(p, tuple(x - 2 * zeta * speed / omega for x, speed in zip(target1, velocity)))
        self.assertVectorAlmostEqual(v, velocity)

    def test_partitioned_linear_motion_matches_single_step(self):
        zero, end = (0.0, 0.0, 0.0), (100.0, -50.0, 20.0)
        for damping in (0, 65, 100):
            args = fx.parameters(60, damping)
            expected = fx.step_vector(zero, zero, zero, end, 1.0, *args)
            p, v = zero, zero
            for index in range(120):
                t0 = tuple(x * index / 120 for x in end)
                t1 = tuple(x * (index + 1) / 120 for x in end)
                p, v = fx.step_vector(p, v, t0, t1, 1 / 120, *args)
            self.assertVectorAlmostEqual(p, expected[0])
            self.assertVectorAlmostEqual(v, expected[1])

    def test_critical_damping_converges_without_overshoot(self):
        target, p, v = (1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
        args = fx.parameters(60, 100)
        previous = 0.0
        for _ in range(600):
            p, v = fx.step_vector(p, v, target, target, 1 / 120, *args)
            self.assertTrue(all(math.isfinite(x) for x in p + v))
            self.assertGreaterEqual(p[0], previous - 1e-14)
            self.assertLessEqual(p[0], 1.0 + 1e-14)
            previous = p[0]
        self.assertVectorAlmostEqual(p, target)
        self.assertVectorAlmostEqual(v, (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
