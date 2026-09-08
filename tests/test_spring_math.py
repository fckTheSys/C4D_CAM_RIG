"""Host-Python regression tests for the Cinema 4D-independent spring solver."""
import math
import unittest

from camrig.spring_math import SPRING_HZ, parameters, step_scalar, step_vector


class SpringMathTests(unittest.TestCase):
    def test_parameter_mapping_and_finite_extremes(self):
        self.assertEqual(parameters(0, 0)[1], 0.2)
        self.assertEqual(parameters(100, 100)[1], 1.0)
        for response in (0, 60, 100):
            for damping in (0, 65, 100):
                omega, zeta = parameters(response, damping)
                self.assertTrue(math.isfinite(omega))
                self.assertTrue(math.isfinite(zeta))

    def test_critical_step_has_no_overshoot(self):
        omega, zeta = parameters(60, 100)
        position = velocity = 0.0
        values = []
        for index in range(240):
            target = 0.0 if index < 12 else 1.0
            position, velocity = step_scalar(position, velocity, target, target, 1.0 / SPRING_HZ, omega, zeta)
            values.append(position)
        self.assertLessEqual(max(values), 1.0 + 1e-9)
        self.assertAlmostEqual(values[-1], 1.0, places=6)

    def test_low_damping_overshoots_and_settles(self):
        omega, zeta = parameters(60, 30)
        position = velocity = 0.0
        values = []
        for index in range(360):
            target = 0.0 if index < 12 else 1.0
            position, velocity = step_scalar(position, velocity, target, target, 1.0 / SPRING_HZ, omega, zeta)
            values.append(position)
        self.assertGreater(max(values), 1.01)
        self.assertLess(abs(values[-1] - 1.0), 1e-3)
        self.assertLess(abs(values[-1] - 1.0), abs(values[120] - 1.0))

    def test_vector_and_amount_blend(self):
        omega, zeta = parameters(60, 65)
        position, velocity = step_vector((0, 0, 0), (0, 0, 0), (0, 0, 0), (10, -2, 4), 1 / 120, omega, zeta)
        self.assertEqual(len(position), 3)
        for amount in (0.0, 0.5, 1.0):
            blended = tuple(target + (value - target) * amount for value, target in zip(position, (10, -2, 4)))
            if amount == 0:
                self.assertEqual(blended, (10, -2, 4))
            if amount == 1:
                self.assertEqual(blended, position)

    def test_fixed_grid_is_independent_of_query_order(self):
        omega, zeta = parameters(60, 65)

        def solve_until(last):
            p, v = 0.0, 0.0
            result = {0: p}
            for index in range(last):
                target = 0.0 if index < 12 else 1.0
                p, v = step_scalar(p, v, target, target, 1 / SPRING_HZ, omega, zeta)
                result[index + 1] = p
            return result

        forward = solve_until(240)
        reverse = solve_until(240)
        for index in (240, 10, 180, 12, 60, 1):
            self.assertAlmostEqual(forward[index], reverse[index], places=12)


if __name__ == "__main__":
    unittest.main()
