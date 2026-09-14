"""Independent dense-polyline reference checks in C4D bundled Python."""
import bisect
import math
import unittest

from path_math import ArcTable


def bezier(points):
    def point(u):
        v = 1-u
        weights = (v*v*v, 3*v*v*u, 3*v*u*u, u*u*u)
        return tuple(sum(weights[i]*points[i][j] for i in range(4)) for j in range(3))
    return point


class ArcTableTests(unittest.TestCase):
    def check_dense_reference(self, point):
        n = 100000
        points = [point(i/n) for i in range(n+1)]
        distances = [0.0]
        horizontal = [0.0]
        for a, b in zip(points, points[1:]):
            distances.append(distances[-1] + math.dist(a, b))
            horizontal.append(horizontal[-1] + math.hypot(b[0]-a[0], b[2]-a[2]))
        table = ArcTable(point)
        self.assertTrue(table.converged, table.diagnostics)
        self.assertLess(abs(table.length-distances[-1]), 0.01)
        for k in range(101):
            fraction = k/100
            s = fraction*distances[-1]
            index = min(n-1, max(0, bisect.bisect_right(distances, s)-1))
            ratio = (s-distances[index])/(distances[index+1]-distances[index])
            expected = tuple(points[index][j] + ratio*(points[index+1][j]-points[index][j]) for j in range(3))
            self.assertLess(math.dist(table.point_at(fraction), expected), 0.01)
            expected_h = horizontal[index]+ratio*(horizontal[index+1]-horizontal[index])
            self.assertLess(abs(table.horizontal_distance(fraction)-expected_h), 0.01)

    def test_straight_unequal_cubic(self):
        self.check_dense_reference(bezier(((0,0,0), (0,0,0), (1,0,0), (1000,0,0))))

    def test_curved_nonuniform_cubic(self):
        self.check_dense_reference(bezier(((0,0,0), (1,50,10), (800,-130,700), (900,200,-80))))

    def test_closed_curve_with_coincident_endpoints(self):
        self.check_dense_reference(bezier(((0,0,0), (300,80,400), (-250,-10,300), (0,0,0))))

    def test_endpoints_and_clamp(self):
        table = ArcTable(lambda u: (10*u, 20*u, 0))
        self.assertEqual(table.parameter(-1), 0)
        self.assertEqual(table.parameter(2), 1)
        self.assertEqual(table.point_at(1), (10,20,0))
        self.assertAlmostEqual(table.horizontal_distance(0.5), 5)

    def test_zero_length(self):
        table = ArcTable(lambda u: (4,5,6))
        self.assertEqual(table.length, 0)
        self.assertIn("zero_length", table.diagnostics)
        for fraction in (0, 0.5, 1):
            self.assertEqual(table.parameter(fraction), 0)
            self.assertEqual(table.point_at(fraction), (4,5,6))
            self.assertEqual(table.horizontal_distance(fraction), 0)

    def test_resource_diagnostics(self):
        table = ArcTable(lambda u: (u*u*100, 0, 0), max_depth=1)
        self.assertFalse(table.converged)
        self.assertIn("max_depth", table.diagnostics)
        class SmallTable(ArcTable):
            MAX_SAMPLES = 32
        capped = SmallTable(lambda u: (u*u*100, 0, 0))
        self.assertFalse(capped.converged)
        self.assertIn("sample_cap", capped.diagnostics)
        self.assertLessEqual(capped.sample_count, 32)

    def test_invalid_values(self):
        for tol in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                ArcTable(lambda u: (u,0,0), tolerance=tol)
        with self.assertRaises(ValueError):
            ArcTable(lambda u: (float('inf'),0,0))
        with self.assertRaises(ValueError):
            ArcTable(lambda u: (u,0,0)).parameter(float('nan'))


if __name__ == '__main__':
    unittest.main()
