"""Pure, deterministic second order spring math. No Cinema 4D dependency."""
import math

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
    y = position - target0
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
    return y1 + target1, w1 + slope

def step_vector(position, velocity, target0, target1, dt, omega, zeta):
    values = [step_scalar(position[i], velocity[i], target0[i], target1[i], dt, omega, zeta) for i in range(3)]
    return tuple(v[0] for v in values), tuple(v[1] for v in values)
