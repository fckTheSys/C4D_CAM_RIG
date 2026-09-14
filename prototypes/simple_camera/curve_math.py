"""Pure Bezier value-extremum times for native animation curve segments."""
import math


def cubic_extrema_times(t0, t1, y0, y1, dt_right, dy_right, dt_left, dy_left):
    """Return interior stationary-value times of a time/value cubic Bezier.

    Tangents are signed offsets from their respective endpoint. Time handles
    must stay inside the segment. Constant-valued cubics return no breakpoints.
    No sampling is used, including for very short segments or narrow reversals.
    """
    values = tuple(float(v) for v in
                   (t0, t1, y0, y1, dt_right, dy_right, dt_left, dy_left))
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Bezier controls must be finite')
    t0, t1, y0, y1, dt_right, dy_right, dt_left, dy_left = values
    if t1 <= t0:
        raise ValueError('Segment end time must exceed start time')
    x1, x2 = t0 + dt_right, t1 + dt_left
    if not (t0 <= x1 <= t1 and t0 <= x2 <= t1):
        raise ValueError('Time handles must lie inside the segment')
    # Scale differences before forming coefficients to avoid discriminant
    # overflow and make the quadratic/linear decision relative to value scale.
    d0 = dy_right
    d1 = (y1-y0) + dy_left-dy_right
    d2 = -dy_left
    scale = max(abs(d0), abs(d1), abs(d2))
    if not math.isfinite(scale):
        raise ValueError('Bezier value range is too large')
    if scale == 0:
        return []
    d0, d1, d2 = d0/scale, d1/scale, d2/scale
    a, b, c = d0-2*d1+d2, 2*(d1-d0), d0
    epsilon = 32*math.ulp(1.0)
    if abs(a) <= epsilon * max(abs(b), abs(c)):
        roots = [] if b == 0 else [-c/b]
    else:
        discriminant = b*b-4*a*c
        slack = epsilon*(b*b + abs(4*a*c))
        if discriminant < -slack:
            roots = []
        elif discriminant <= 0:
            roots = [-b/(2*a)]
        else:
            # Stable quadratic formula preserves roots close to endpoints.
            q = -0.5*(b+math.copysign(math.sqrt(discriminant), b))
            roots = [q/a, c/q] if q else [-b/(2*a)]
    result = []
    for u in sorted(roots):
        if not 0 < u < 1:
            continue
        v = 1-u
        # Relative coordinates reduce loss of precision for large time origins.
        t = t0 + 3*v*v*u*(x1-t0) + 3*v*u*u*(x2-t0) + u*u*u*(t1-t0)
        if t0 < t < t1 and (not result or t != result[-1]):
            result.append(t)
    return result
