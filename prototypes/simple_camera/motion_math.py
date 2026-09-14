"""Stateless motion primitives; seconds, centimetres and radians unless named.

Prototype quadrature uses a fixed zero-origin time grid. It approximates smooth
functions; callers must split discontinuities and check convergence as needed.
No host imports, caches, RNG state or previous-frame state.
"""
import math


def _finite(value, name):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(name + ' must be finite')
    return value


def integrate(fn, start, end, step=1.0 / 120.0):
    """Signed composite trapezoid integral on the grid k*step, partial edges.

    At most one million intervals per call; this prototype deliberately refuses
    excessive work rather than silently lowering the requested resolution.
    """
    start = _finite(start, 'start')
    end = _finite(end, 'end')
    step = _finite(step, 'step')
    if step <= 0:
        raise ValueError('step must be positive')
    if start == end:
        return 0.0
    low, high = sorted((start, end))
    if (high - low) / step > 1000000:
        raise ValueError('integration interval cap exceeded')
    sign = 1.0 if end > start else -1.0
    previous_x = low
    previous_y = _finite(fn(low), 'integrand')
    pieces = []
    # The same absolute grid is used for every requested endpoint/order.
    index = math.floor(low / step) + 1
    while index * step < high:
        x = index * step
        if x > previous_x:
            y = _finite(fn(x), 'integrand')
            pieces.append((x - previous_x) * (previous_y * 0.5 + y * 0.5))
            previous_x, previous_y = x, y
        index += 1
    y = _finite(fn(high), 'integrand')
    pieces.append((high - previous_x) * (previous_y * 0.5 + y * 0.5))
    return _finite(sign * math.fsum(pieces), 'integral')


def _lattice(index, seed):
    # SplitMix64 finalizer, using explicit integer arithmetic, never hash().
    mask = (1 << 64) - 1
    value = (index + seed * 0x9E3779B97F4A7C15) & mask
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & mask
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & mask
    value ^= value >> 31
    return 2.0 * (value >> 11) / float((1 << 53) - 1) - 1.0


def noise(x, seed):
    """C2 smooth value noise in [-1,1]; integer seed, arbitrary signed x."""
    x = _finite(x, 'x')
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError('seed must be an integer')
    index = math.floor(x)
    fraction = x - index
    blend = fraction ** 3 * (fraction * (fraction * 6.0 - 15.0) + 10.0)
    left, right = _lattice(index, seed), _lattice(index + 1, seed)
    return max(-1.0, min(1.0, left + (right - left) * blend))


def walk(phase, speed, strength, amplitude, lean_deg, softness):
    """Return lateral cm, vertical cm, camera-local roll radians.

    One step advances phase by pi; left/right pair is 2*pi. Speed is nonnegative
    horizontal cm/s. Strength is a nonnegative multiplier (1=full), amplitude and
    lean are nonnegative peak scales. Softness is [0,1], 1 giving a sinusoidal bob.
    A smoothstep speed gate rises from zero to full between 0 and 100 cm/s.
    """
    phase = _finite(phase, 'phase')
    values = [_finite(value, name) for value, name in
              ((speed, 'speed'), (strength, 'strength'), (amplitude, 'amplitude'),
               (lean_deg, 'lean_deg'), (softness, 'softness'))]
    speed, strength, amplitude, lean_deg, softness = values
    if any(value < 0 for value in values) or softness > 1:
        raise ValueError('motion scales must be nonnegative; softness must be in [0,1]')
    if strength == 0 or speed == 0:
        return 0.0, 0.0, 0.0
    ratio = min(speed / 100.0, 1.0)
    gain = strength * ratio * ratio * (3.0 - 2.0 * ratio)
    lateral = math.sin(phase)
    harmonic = 0.25 * (1.0 - softness)
    vertical = (math.cos(2.0 * phase) + harmonic * math.cos(4.0 * phase)) / (1.0 + harmonic)
    result = (amplitude * gain * lateral, amplitude * gain * vertical,
              math.radians(lean_deg) * gain * lateral)
    return tuple(_finite(value, 'walk output') for value in result)
