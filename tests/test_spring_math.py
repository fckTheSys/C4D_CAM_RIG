"""Host-Python regression tests for the Cinema 4D-independent spring solver."""
import math
import unittest
import ast
from pathlib import Path

from camrig.spring_math import SPRING_HZ, parameters, step_scalar, step_vector


class SpringMathTests(unittest.TestCase):
    def test_linear_forcing_against_independent_rk4(self):
        for damping in (0, 65, 100):
            omega, zeta = parameters(60, damping)
            p, v = 0.0, 0.0
            def rhs(t, x, velocity):
                return velocity, -2*zeta*omega*velocity - omega**2*(x-t)
            h = 1/10000
            for i in range(10000):
                t = i*h
                a,b = rhs(t,p,v)
                c,d = rhs(t+h/2,p+h*a/2,v+h*b/2)
                e,f = rhs(t+h/2,p+h*c/2,v+h*d/2)
                g,k = rhs(t+h,p+h*e,v+h*f)
                p += h*(a+2*c+2*e+g)/6
                v += h*(b+2*d+2*f+k)/6
            actual = (0., 0.)
            for i in range(120):
                actual = step_scalar(*actual,i/120,(i+1)/120,1/120,omega,zeta)
            self.assertAlmostEqual(actual[0],p,places=9)
            self.assertAlmostEqual(actual[1],v,places=9)

    def test_subinterval_composition_and_embedded_parity(self):
        source = Path(__file__).resolve().parents[1]/'camrig/tag_embedded.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        ns = {'math': math}
        funcs = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_spring_step_scalar']
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'embedded-math','exec'),ns)
        for damping in (0,65,100):
            omega,zeta = parameters(60,damping)
            for fraction in (.00001,.3,.99999):
                dt=1/120
                middle=3+(7-3)*fraction
                partial=step_scalar(1,2,3,middle,dt*fraction,omega,zeta)
                combined=step_scalar(*partial,middle,7,dt*(1-fraction),omega,zeta)
                full=step_scalar(1,2,3,7,dt,omega,zeta)
                for a,b in zip(combined,full): self.assertAlmostEqual(a,b,places=9)
                self.assertEqual(full,ns['_spring_step_scalar'](1,2,3,7,dt,omega,zeta))
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

    def test_stationary_target_remains_at_rest(self):
        for response in (0, 60, 100):
            for damping in (0, 65, 100):
                omega, zeta = parameters(response, damping)
                self.assertEqual(step_scalar(42, 0, 42, 42, 1/120, omega, zeta), (42, 0))


if __name__ == "__main__":
    unittest.main()
