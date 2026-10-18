"""Formula and example registry.

Each entry records the exact expression, symbol meanings, domain/assumptions,
exceptional cases, a derivation/reference, and a `check` function. Run
`/opt/mvenv/bin/python registry/verify.py` to execute every check and write
verify/REPORT.md.

Verification kinds:
  symbolic  — sympy proves an identity / solves exactly (a proof for the stated domain)
  exact     — exact rational/algebraic computation of a specific example
  numeric   — floating-point sampling: SUPPORTING EVIDENCE ONLY, never a proof
"""
import sympy as sp

x, y, h, k, a, b, m, t = sp.symbols("x y h k a b m t", real=True)
f = sp.Function("f")

ENTRIES = []


def entry(**kw):
    def deco(fn):
        kw["check"] = fn
        ENTRIES.append(kw)
        return fn
    return deco


# ------------------------------------------------------------------ C01.7 transformations
@entry(id="F.TR.01", expr="g(x) = f(x - h) + k", section="C01.7",
       symbols="f: given real function; h, k: real constants",
       domain="dom g = {x : x - h ∈ dom f} = dom f shifted right by h",
       exceptions="none for real h, k; NOTE sign: x - h with h>0 moves the graph RIGHT",
       reference="Point-mapping: (p, f(p)) on f  ↦  (p+h, f(p)+k) on g",
       kind="symbolic")
def _tr01():
    p = sp.Symbol("p", real=True)
    g = lambda X: f(X - h) + k
    return sp.simplify(g(p + h) - (f(p) + k)) == 0


@entry(id="F.TR.02", expr="g(x) = a·f(x)", section="C01.7",
       symbols="a: real non-zero constant",
       domain="dom g = dom f",
       exceptions="a<0 also reflects in the x-axis; a=0 collapses graph to y=0 (not a stretch)",
       reference="(p, f(p)) ↦ (p, a f(p))", kind="symbolic")
def _tr02():
    # concrete consequence: for a != 0 the x-intercepts of a*F equal those of F
    F = x**2 - 4 * x + 3
    an = sp.Symbol("an", real=True, nonzero=True)
    return sp.solveset(an * F, x, sp.S.Reals) == sp.solveset(F, x, sp.S.Reals)


@entry(id="F.TR.03", expr="g(x) = f(b x)", section="C01.7",
       symbols="b: real non-zero constant",
       domain="dom g = {x : b x ∈ dom f}",
       exceptions="b>1 compresses horizontally by factor b (not stretches); b<0 also reflects in y-axis",
       reference="(p, f(p)) ↦ (p/b, f(p))", kind="symbolic")
def _tr03():
    p = sp.Symbol("p", real=True)
    bb = sp.Symbol("bb", real=True, nonzero=True)
    return sp.simplify(f(bb * (p / bb)) - f(p)) == 0


@entry(id="F.TR.04", expr="|f(x)|  and  f(|x|)", section="C01.7",
       symbols="f real-valued",
       domain="dom |f| = dom f;  dom f(|x|) = {x : |x| ∈ dom f}",
       exceptions="|f| reflects only the parts BELOW the x-axis; f(|x|) discards x<0 part and mirrors x≥0 part (even function)",
       reference="definition of |·|", kind="symbolic")
def _tr04():
    F = x**2 - 4 * x + 3
    G = F.subs(x, sp.Abs(x))
    even = sp.simplify(G.subs(x, -x) - G) == 0
    # |F| differs from F exactly where F < 0: that set must be (1, 3) (the flipped arch)
    flip_region = sp.solveset(F < 0, x, sp.S.Reals) == sp.Interval.open(1, 3)
    return even and flip_region


@entry(id="E.C01.7.1", expr="#real solutions of |x² - 4x + 3| = k", section="C01.7",
       symbols="k real parameter",
       domain="x ∈ R",
       exceptions="k<0: 0;  k=0: 2;  0<k<1: 4;  k=1: 3;  k>1: 2",
       reference="Branch x²-4x+3 = k has D₁=4(1+k); branch x²-4x+3 = -k has D₂=4(1-k); "
                 "branches can share a root only if k=-k, i.e. k=0",
       kind="symbolic + exact")
def _e1():
    def count(kv):
        s = sp.solveset(sp.Abs(x**2 - 4 * x + 3) - kv, x, sp.S.Reals)
        if s is sp.S.EmptySet:
            return 0
        return len(s) if isinstance(s, sp.FiniteSet) else None
    table = {-1: 0, 0: 2, sp.Rational(1, 2): 4, 1: 3, 2: 2, sp.Rational(99, 100): 4, sp.Rational(101, 100): 2}
    exact_ok = all(count(kv) == c for kv, c in table.items())
    # symbolic: discriminants of the two branches
    D1 = sp.discriminant(x**2 - 4 * x + 3 - k, x)
    D2 = sp.discriminant(x**2 - 4 * x + 3 + k, x)
    sym_ok = sp.expand(D1 - 4 * (1 + k)) == 0 and sp.expand(D2 - 4 * (1 - k)) == 0
    return exact_ok and sym_ok


@entry(id="E.C01.7.2", expr="y = 2 - |x - 1|: vertex (1, 2), range (-∞, 2]", section="C01.7",
       symbols="—", domain="x ∈ R", exceptions="not differentiable at x = 1 (corner)",
       reference="|x-1| ≥ 0 with equality iff x=1", kind="symbolic")
def _e2():
    Y = 2 - sp.Abs(x - 1)
    rng = sp.calculus.util.function_range(Y, x, sp.S.Reals)
    return rng == sp.Interval(-sp.oo, 2) and Y.subs(x, 1) == 2


@entry(id="E.C01.7.3", expr="dom √(x - 2) = [2, ∞), range [0, ∞)", section="C01.7",
       symbols="√ = principal (non-negative) square root", domain="x - 2 ≥ 0",
       exceptions="endpoint x=2 INCLUDED (closed dot)", reference="F.TR.01 with h=2, k=0",
       kind="symbolic")
def _e3():
    d = sp.calculus.util.continuous_domain(sp.sqrt(x - 2), x, sp.S.Reals)
    r = sp.calculus.util.function_range(sp.sqrt(x - 2), x, d)
    return d == sp.Interval(2, sp.oo) and r == sp.Interval(0, sp.oo)


@entry(id="E.C01.7.4", expr="vertex of y = (x - 2)² + 1 is (2, 1); range [1, ∞)", section="C01.7",
       symbols="—", domain="x ∈ R", exceptions="—", reference="F.TR.01 applied to x²", kind="symbolic")
def _e4():
    Y = (x - 2)**2 + 1
    return sp.solve(sp.diff(Y, x), x) == [2] and sp.calculus.util.function_range(Y, x, sp.S.Reals) == sp.Interval(1, sp.oo)


# ------------------------------------------------------------------ C00 opening problem
@entry(id="E.C00.1", expr="y = m x is tangent to y = x² + 1  ⇔  m = ±2 (touch points x = ±1)", section="C00/C02/C11",
       symbols="m: slope of a line through the origin", domain="m ∈ R",
       exceptions="|m|<2: no intersection; |m|>2: two intersections",
       reference="x² - m x + 1 = 0 has D = m² - 4", kind="symbolic")
def _h1():
    D = sp.discriminant(x**2 - m * x + 1, x)
    sols = sp.solve(sp.Eq(D, 0), m)
    tang = all(sp.diff(x**2 + 1, x).subs(x, s / 2) == s for s in sols)  # slope of curve = m at touch point
    return sorted(sols) == [-2, 2] and tang


@entry(id="E.C00.2", expr="area between y = x² + 1 and y = 3x equals 5√5/6", section="C00/C13",
       symbols="—", domain="between intersection points x = (3 ± √5)/2",
       exceptions="line is ABOVE the parabola between the roots (3x - x² - 1 ≥ 0 there)",
       reference="∫(3x - x² - 1)dx between roots = D^{3/2}/(6a²) with D = 5, a = 1", kind="symbolic")
def _h2():
    r1, r2 = sorted(sp.solve(x**2 - 3 * x + 1, x), key=lambda v: float(v))
    A = sp.integrate(3 * x - x**2 - 1, (x, r1, r2))
    mid_positive = (3 * x - x**2 - 1).subs(x, sp.Rational(3, 2)) > 0
    return sp.simplify(A - 5 * sp.sqrt(5) / 6) == 0 and mid_positive


@entry(id="E.C00.3", expr="m uniform on {-3,…,3}: P(line meets parabola) = 4/7", section="C00/C20",
       symbols="m integer, equally likely", domain="7 outcomes",
       exceptions="'meets' includes tangency (m = ±2)", reference="meet ⇔ m² - 4 ≥ 0", kind="exact")
def _h3():
    fav = [mv for mv in range(-3, 4) if mv**2 - 4 >= 0]
    return sp.Rational(len(fav), 7) == sp.Rational(4, 7)
