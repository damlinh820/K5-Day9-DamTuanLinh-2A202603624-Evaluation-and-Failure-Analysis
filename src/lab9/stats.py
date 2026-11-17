"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge) or not human:
        raise ValueError("labels must be nonempty and aligned")
    out = dict(tp=0, fp=0, fn=0, tn=0)
    for h, j in zip(human, judge):
        if h not in ("PASS", "FAIL") or j not in ("PASS", "FAIL"):
            raise ValueError("labels must be PASS or FAIL")
        out[("t" if h == j else "f") + ("p" if j == POS else "n")] += 1
    return out


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    c = confusion(human, judge)
    return (c['tp'] / (c['tp'] + c['fp']) if c['tp'] + c['fp'] else 0.0,
            c['tp'] / (c['tp'] + c['fn']) if c['tp'] + c['fn'] else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    c = confusion(human, judge)
    n = sum(c.values())
    observed = (c['tp'] + c['tn']) / n
    expected = ((c['tp'] + c['fn']) * (c['tp'] + c['fp'])
                + (c['tn'] + c['fp']) * (c['tn'] + c['fn'])) / n**2
    if expected == 1:
        raise ValueError("kappa undefined: expected agreement is 1")
    return (observed - expected) / (1 - expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite probabilities")
    denominator = sensitivity + specificity - 1
    if denominator <= 0:
        raise ValueError("judge must be better than chance for prevalence correction")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / denominator))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.size == 0 or x.shape != y.shape:
        raise ValueError("bootstrap requires aligned nonempty vectors")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("bootstrap requires finite values")
    if not 0 < confidence < 1 or not isinstance(n_resamples, int) or n_resamples < 1:
        raise ValueError("invalid bootstrap configuration")
    delta = float(np.mean(x - y))
    if np.array_equal(x, y):
        return 0.0, 0.0, 0.0
    if x.size == 1:
        raise ValueError("a confidence interval requires at least two items")
    result = bootstrap((x, y), lambda a, b, axis: np.mean(a - b, axis=axis),
                       paired=True, vectorized=True, method="percentile",
                       n_resamples=n_resamples, confidence_level=confidence,
                       rng=np.random.default_rng(rng))
    return delta, float(result.confidence_interval.low), float(result.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_counts(n, c, k)
    return 1 - math.comb(n - c, k) / math.comb(n, k) if n - c >= k else 1.0


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_counts(n, c, k)
    return math.comb(c, k) / math.comb(n, k) if c >= k else 0.0


def _validate_counts(n: int, c: int, k: int) -> None:
    if any(type(v) is not int for v in (n, c, k)) or not (n >= 1 and 0 <= c <= n and 1 <= k <= n):
        raise ValueError("require integers n >= 1, 0 <= c <= n and 1 <= k <= n")
