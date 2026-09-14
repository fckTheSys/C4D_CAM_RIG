"""Deterministic, bounded polyline arc mapping; no host dependencies.

Rows are (native_parameter, cumulative_3d_distance, cumulative_xz_distance).
Tolerance is expressed in the point callback's distance units. Adaptive sampling
cannot prove an error bound for an arbitrary adversarial callback; callers must
use smooth curves and check ``converged`` before trusting the approximation.
"""
import bisect
import math


class ArcTable:
    """Approximate a smooth curve with distance and parameter error checks."""

    MAX_SAMPLES = 131073
    MIN_DEPTH = 4

    def __init__(self, point, tolerance=0.001, max_depth=18):
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("tolerance must be finite and positive")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 0 <= max_depth <= 24:
            raise ValueError("max_depth must be an integer from 0 through 24")
        self._point = point
        self.tolerance = tolerance
        self.diagnostics = []
        cache = {}

        def sample(u):
            if u not in cache:
                p = tuple(float(x) for x in point(u))
                if len(p) != 3 or not all(math.isfinite(x) for x in p):
                    raise ValueError("point callback must return three finite coordinates")
                cache[u] = p
            return cache[u]

        def distance(a, b):
            return math.dist(a, b)

        leaves = [(0.0, sample(0.0))]

        def subdivide(a, b, pa, pb, depth):
            if len(cache) + 3 > self.MAX_SAMPLES:
                if "sample_cap" not in self.diagnostics:
                    self.diagnostics.append("sample_cap")
                leaves.append((b, pb))
                return
            us = [a + (b - a) * f for f in (0.25, 0.5, 0.75)]
            ps = [pa] + [sample(u) for u in us] + [pb]
            chord = distance(pa, pb)
            poly = sum(distance(ps[i], ps[i + 1]) for i in range(4))
            horizontal = sum(math.hypot(ps[i+1][0]-ps[i][0], ps[i+1][2]-ps[i][2]) for i in range(4))
            horizontal_chord = math.hypot(pb[0]-pa[0], pb[2]-pa[2])
            # Chord excess alone misses a perfectly straight, unevenly
            # parameterized cubic. Compare positions to linear-u predictions.
            mapping_error = max(distance(ps[i], tuple(pa[j] + (pb[j]-pa[j]) * i/4 for j in range(3))) for i in (1, 2, 3))
            needs_split = (depth < self.MIN_DEPTH or
                           poly - chord > tolerance * (b-a) / 4 or
                           horizontal - horizontal_chord > tolerance * (b-a) / 4 or
                           mapping_error > tolerance / 4)
            if needs_split and depth < max_depth:
                subdivide(a, us[1], pa, ps[2], depth + 1)
                subdivide(us[1], b, ps[2], pb, depth + 1)
            else:
                if needs_split and "max_depth" not in self.diagnostics:
                    self.diagnostics.append("max_depth")
                leaves.append((b, pb))

        subdivide(0.0, 1.0, sample(0.0), sample(1.0), 0)
        self.rows = [(0.0, 0.0, 0.0)]
        s = h = 0.0
        previous = leaves[0][1]
        for u, p in leaves[1:]:
            s += distance(previous, p)
            h += math.hypot(p[0] - previous[0], p[2] - previous[2])
            self.rows.append((u, s, h))
            previous = p
        self.length = s
        self.sample_count = len(cache)
        self.converged = not self.diagnostics
        if s == 0.0:
            self.diagnostics.append("zero_length")
        self.diagnostics = tuple(self.diagnostics)
        self._distances = [row[1] for row in self.rows]

    def _segment(self, fraction):
        f = float(fraction)
        if not math.isfinite(f):
            raise ValueError("fraction must be finite")
        f = min(1.0, max(0.0, f))
        if self.length == 0.0 or f == 0.0:
            return 0, 0.0
        if f == 1.0:
            return len(self.rows)-2, 1.0
        s = self.length * f
        i = min(len(self.rows)-2, bisect.bisect_right(self._distances, s)-1)
        width = self.rows[i+1][1] - self.rows[i][1]
        return i, (s-self.rows[i][1])/width if width else 0.0

    def parameter(self, fraction):
        """Native u at clamped 3D arc fraction; a zero-length curve returns 0."""
        i, t = self._segment(fraction)
        return self.rows[i][0] + t * (self.rows[i+1][0]-self.rows[i][0])

    def point_at(self, fraction):
        return tuple(self._point(self.parameter(fraction)))

    def horizontal_distance(self, fraction):
        """Cumulative XZ travel at a 3D arc fraction (not net displacement)."""
        i, t = self._segment(fraction)
        return self.rows[i][2] + t * (self.rows[i+1][2]-self.rows[i][2])
