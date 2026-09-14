"""Portable pure math for CamRig 2 effects; no host or playback state.

Provenance: C2 value noise and finite validation copied from this repository's
prototypes/simple_camera/motion_math.py; analytic spring helpers copied from
camrig/spring_math.py. Keep this module self-contained for embedding in scenes.

Spring arguments use seconds and any consistent positional unit; omega is in
radians/second. parameters() maps artist controls 0..100 to omega and zeta.
step_vector() expects three-component sequences and omega > 0, 0 <= zeta <= 1;
its linear-target analytic solution is valid for those damping regimes.
"""
import math


def _finite(value, name):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(name + ' must be finite')
    return value


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


SPRING_HZ = 120.0

def parameters(response, damping):
    response = min(100.0, max(0.0, float(response)))
    damping = min(100.0, max(0.0, float(damping)))
    omega = 2.0 * math.pi * (0.5 * (10.0 ** (response / 100.0)))
    return omega, 0.2 + 0.8 * damping / 100.0

def step_scalar(position, velocity, target0, target1, dt, omega, zeta):
    """Analytic response to a linearly moving target during one interval."""
    if dt <= 0.0:
        return position, velocity
    slope = (target1 - target0) / dt
    lag = 2.0 * zeta * slope / omega
    y = position - target0 + lag
    w = velocity - slope
    a = omega * zeta
    wd2 = max(0.0, omega * omega - a * a)
    if wd2 > 1e-12:
        wd = math.sqrt(wd2)
        e = math.exp(-a * dt)
        c, s = math.cos(wd * dt), math.sin(wd * dt)
        y1 = e * (y * c + (w + a * y) * s / wd)
        w1 = e * (w * c - (a * w + omega * omega * y) * s / wd)
    else:
        e = math.exp(-a * dt)
        y1 = e * (y + (w + a * y) * dt)
        w1 = e * (w - a * (w + a * y) * dt)
    return y1 + target1 - lag, w1 + slope

def step_vector(position, velocity, target0, target1, dt, omega, zeta):
    values = [step_scalar(position[i], velocity[i], target0[i], target1[i], dt, omega, zeta) for i in range(3)]
    return tuple(v[0] for v in values), tuple(v[1] for v in values)
