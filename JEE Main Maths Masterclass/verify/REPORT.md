# Formula / example verification report

Generated 2026-10-18 00:49 by `registry/verify.py` (sympy). 11/11 checks pass.

`numeric` checks are supporting evidence only — not proofs.

| ID | Expression | Section | Domain / assumptions | Exceptions | Derivation / reference | Method | Result |
|---|---|---|---|---|---|---|---|
| F.TR.01 | g(x) = f(x - h) + k | C01.7 | dom g = {x : x - h ∈ dom f} = dom f shifted right by h | none for real h, k; NOTE sign: x - h with h>0 moves the graph RIGHT | Point-mapping: (p, f(p)) on f  ↦  (p+h, f(p)+k) on g | symbolic | PASS |
| F.TR.02 | g(x) = a·f(x) | C01.7 | dom g = dom f | a<0 also reflects in the x-axis; a=0 collapses graph to y=0 (not a stretch) | (p, f(p)) ↦ (p, a f(p)) | symbolic | PASS |
| F.TR.03 | g(x) = f(b x) | C01.7 | dom g = {x : b x ∈ dom f} | b>1 compresses horizontally by factor b (not stretches); b<0 also reflects in y-axis | (p, f(p)) ↦ (p/b, f(p)) | symbolic | PASS |
| F.TR.04 | \|f(x)\|  and  f(\|x\|) | C01.7 | dom \|f\| = dom f;  dom f(\|x\|) = {x : \|x\| ∈ dom f} | \|f\| reflects only the parts BELOW the x-axis; f(\|x\|) discards x<0 part and mirrors x≥0 part (even function) | definition of \|·\| | symbolic | PASS |
| E.C01.7.1 | #real solutions of \|x² - 4x + 3\| = k | C01.7 | x ∈ R | k<0: 0;  k=0: 2;  0<k<1: 4;  k=1: 3;  k>1: 2 | Branch x²-4x+3 = k has D₁=4(1+k); branch x²-4x+3 = -k has D₂=4(1-k); branches can share a root only if k=-k, i.e. k=0 | symbolic + exact | PASS |
| E.C01.7.2 | y = 2 - \|x - 1\|: vertex (1, 2), range (-∞, 2] | C01.7 | x ∈ R | not differentiable at x = 1 (corner) | \|x-1\| ≥ 0 with equality iff x=1 | symbolic | PASS |
| E.C01.7.3 | dom √(x - 2) = [2, ∞), range [0, ∞) | C01.7 | x - 2 ≥ 0 | endpoint x=2 INCLUDED (closed dot) | F.TR.01 with h=2, k=0 | symbolic | PASS |
| E.C01.7.4 | vertex of y = (x - 2)² + 1 is (2, 1); range [1, ∞) | C01.7 | x ∈ R | — | F.TR.01 applied to x² | symbolic | PASS |
| E.C00.1 | y = m x is tangent to y = x² + 1  ⇔  m = ±2 (touch points x = ±1) | C00/C02/C11 | m ∈ R | \|m\|<2: no intersection; \|m\|>2: two intersections | x² - m x + 1 = 0 has D = m² - 4 | symbolic | PASS |
| E.C00.2 | area between y = x² + 1 and y = 3x equals 5√5/6 | C00/C13 | between intersection points x = (3 ± √5)/2 | line is ABOVE the parabola between the roots (3x - x² - 1 ≥ 0 there) | ∫(3x - x² - 1)dx between roots = D^{3/2}/(6a²) with D = 5, a = 1 | symbolic | PASS |
| E.C00.3 | m uniform on {-3,…,3}: P(line meets parabola) = 4/7 | C00/C20 | 7 outcomes | 'meets' includes tangency (m = ±2) | meet ⇔ m² - 4 ≥ 0 | exact | PASS |
