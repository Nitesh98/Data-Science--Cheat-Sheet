"""
Small, dependency-free statistics library shared across portfolio projects.
No scipy/numpy available in this environment -- these are hand-implemented
so the experiment analysis is genuinely computed, not called from a library
as a black box.

Implements: normal CDF/inverse-CDF, two-proportion z-test, Welch's t-test
(normal-approximated p-value, valid for the large sample sizes used here),
and a two-proportion sample-size calculator for experiment design.
"""
import math


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    """Inverse normal CDF (probit) via Acklam's rational approximation.
    Accurate to ~1.15e-9 -- more than sufficient for power/sample-size calcs."""
    if not (0 < p < 1):
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


def two_proportion_ztest(x1, n1, x2, n2):
    """x1,x2 = successes, n1,n2 = trials. Returns dict with p1, p2, diff, se,
    z-stat, two-sided p-value, and a 95% CI on the difference (p2 - p1)."""
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se_pool if se_pool > 0 else 0.0
    p_value = 2 * (1 - norm_cdf(abs(z)))
    se_unpooled = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    ci = (p2 - p1 - 1.96 * se_unpooled, p2 - p1 + 1.96 * se_unpooled)
    return {"p1": p1, "p2": p2, "diff": p2 - p1, "relative_lift_pct": 100 * (p2 - p1) / p1,
            "z": z, "p_value": p_value, "ci_95": ci}


def welch_ttest(sample1, sample2):
    """Welch's t-test for unequal variances. p-value via normal approximation
    (valid here: both samples are in the thousands, so t -> normal)."""
    n1, n2 = len(sample1), len(sample2)
    m1, m2 = sum(sample1) / n1, sum(sample2) / n2
    v1 = sum((x - m1) ** 2 for x in sample1) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in sample2) / (n2 - 1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    t = (m2 - m1) / se if se > 0 else 0.0
    p_value = 2 * (1 - norm_cdf(abs(t)))
    ci = (m2 - m1 - 1.96 * se, m2 - m1 + 1.96 * se)
    return {"mean1": m1, "mean2": m2, "diff": m2 - m1, "t": t, "p_value": p_value, "ci_95": ci}


def sample_size_two_proportions(baseline_p, mde_relative, alpha=0.05, power=0.80):
    """Per-group sample size needed to detect a relative MDE on a baseline
    conversion rate, two-sided test."""
    p1 = baseline_p
    p2 = baseline_p * (1 + mde_relative)
    z_alpha = norm_ppf(1 - alpha / 2)
    z_beta = norm_ppf(power)
    pooled_var = p1 * (1 - p1) + p2 * (1 - p2)
    n = ((z_alpha + z_beta) ** 2 * pooled_var) / (p2 - p1) ** 2
    return math.ceil(n)
