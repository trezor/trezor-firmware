"""
tune_spans.py - tune the temperature span of each calibration curve for an operating range.

    python tune_spans.py --logs @logs.txt [--range 0 35] [--method both|lut|poly] [--out models/spans.json]
    then fit with it:   python soc_ocv_lut.py fit --logs @logs.txt --spans models/spans.json

Each calibration curve (one per temperature set point) applies fully over a span [t_lo, t_hi];
across the gaps between spans the neighbouring curves are blended linearly. A span must lie inside
the temperatures actually measured during that set point's runs (2nd..98th percentile, 0.5 C grid).

Objective: leave-one-cell-out error of the points whose MEASURED temperature lies in the operating
range (+-1 C), estimated at that measured temperature, with every 5 C band weighted equally so the
many points at 25-30 C do not drown the rest. Search: coordinate descent over the set points, all
(t_lo, t_hi) pairs on the grid, three passes; a change is kept only if it lowers the error, so
curves that do not matter for the range stay at their measured median.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from ocv_common import blend_spans, load_ocv_points
from soc_ocv_lut import DEFAULT_POINTS, OcvLut
from soc_ocv_poly import DEFAULT_DEGREE, OcvPoly

MARGIN_C = 1.0
BAND_C = 5.0


def loco_curve_estimates(pts: pd.DataFrame, fit) -> np.ndarray:
    """(n, K): every point estimated by each set point's curve, fitted without the point's cell."""
    groups = sorted(pts.T_set.unique())
    est = np.zeros((len(pts), len(groups)))
    for cell in pts.cell.unique():
        idx = np.flatnonzero(pts.cell.to_numpy() == cell)
        model = fit(pts[pts.cell != cell])
        for k, (lo, hi) in enumerate(zip(model._lo, model._hi)):
            est[idx, k] = model.estimate(pts.ocv.to_numpy()[idx], np.full(len(idx), 0.5 * (lo + hi)))
    return est


class Objective:
    def __init__(self, pts: pd.DataFrame, rng: tuple[float, float], estimates: list[np.ndarray]):
        t = pts.T_meas.to_numpy()
        self.sel = (t >= rng[0] - MARGIN_C) & (t <= rng[1] + MARGIN_C)
        if not self.sel.any():
            raise SystemExit(f"no OCV point measured within {rng[0]}..{rng[1]} C")
        self.t, self.truth = t[self.sel], pts.soc.to_numpy()[self.sel]
        self.band = np.floor((np.clip(self.t, rng[0], rng[1] - 1e-9) - rng[0]) / BAND_C).astype(int)
        self.est = [e[self.sel] for e in estimates]

    def band_mae(self, lo, hi, which: int) -> pd.Series:
        e = np.abs(blend_spans(lo, hi, self.est[which].T, self.t) - self.truth)
        return pd.Series(e).groupby(self.band).mean()

    def __call__(self, lo, hi) -> float:
        return float(np.mean([self.band_mae(lo, hi, k).mean() for k in range(len(self.est))]))


def tune(pts, rng, methods, passes: int = 3):
    groups = sorted(pts.T_set.unique())
    q = pts.groupby("T_set").T_meas.quantile([0.02, 0.5, 0.98]).unstack()
    fits = {"lut": lambda tr: OcvLut.fit(tr, DEFAULT_POINTS, spans="measured"),
            "poly": lambda tr: OcvPoly.fit(tr, DEFAULT_DEGREE, spans="measured")}
    obj = Objective(pts, rng, [loco_curve_estimates(pts, fits[m]) for m in methods])
    lo = np.array([round(q.loc[g, 0.5] * 2) / 2 for g in groups])
    hi = lo.copy()
    for _ in range(passes):
        changed = False
        for k, g in enumerate(groups):
            grid = np.arange(np.ceil(q.loc[g, 0.02] * 2) / 2, np.floor(q.loc[g, 0.98] * 2) / 2 + 0.01, 0.5)
            grid = np.union1d(grid, [lo[k], hi[k]])
            best = (obj(lo, hi), lo[k], hi[k])
            for a in grid:
                for b in grid[grid >= a]:
                    l2, h2 = lo.copy(), hi.copy()
                    l2[k], h2[k] = a, b
                    if any(not (l2[i] <= h2[i] < l2[i + 1]) for i in range(len(groups) - 1)):
                        continue
                    v = obj(l2, h2)
                    if v < best[0] - 1e-9 or (abs(v - best[0]) <= 1e-9 and b - a < best[2] - best[1]):
                        best = (v, a, b)
            if (best[1], best[2]) != (lo[k], hi[k]):
                lo[k], hi[k], changed = best[1], best[2], True
        if not changed:
            break
    return {g: (float(lo[k]), float(hi[k])) for k, g in enumerate(groups)}, obj, q


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", nargs="+", required=True, help="globs, paths or @list.txt")
    ap.add_argument("--range", nargs=2, type=float, default=[0.0, 35.0], metavar=("T_MIN", "T_MAX"))
    ap.add_argument("--method", choices=("both", "lut", "poly"), default="both")
    ap.add_argument("--out", default="spans.json")
    args = ap.parse_args()
    pts = load_ocv_points(args.logs).reset_index(drop=True)
    methods = ["lut", "poly"] if args.method == "both" else [args.method]
    spans, obj, q = tune(pts, tuple(args.range), methods)
    groups = sorted(spans)
    setp = (np.array(groups, float), np.array(groups, float))
    med = (np.array([q.loc[g, 0.5] for g in groups]), np.array([q.loc[g, 0.5] for g in groups]))
    tuned = (np.array([spans[g][0] for g in groups]), np.array([spans[g][1] for g in groups]))
    print(f"operating range {args.range[0]:g}..{args.range[1]:g} C, {obj.sel.sum()} OCV points, methods {methods}")
    print(f"{'set point':>9}  {'measured 2-98 %':>16}  tuned span")
    for g in groups:
        print(f"{g:>7g} C  {q.loc[g, 0.02]:6.1f} .. {q.loc[g, 0.98]:5.1f} C  {spans[g][0]:g} .. {spans[g][1]:g} C")
    for name, (lo, hi) in (("set points", setp), ("measured medians", med), ("tuned spans", tuned)):
        bands = [obj.band_mae(lo, hi, k) for k in range(len(methods))]
        lab = " | ".join(f"{m}: " + ", ".join(f"{args.range[0] + BAND_C * b:g}-{args.range[0] + BAND_C * (b + 1):g} C "
                                                 f"{v:.2f}" for b, v in s.items()) for m, s in zip(methods, bands))
        print(f"{name:17s} objective {obj(lo, hi):.3f} % | {lab}")
    with open(args.out, "w") as f:
        json.dump({str(g): list(s) for g, s in spans.items()}, f, indent=1)
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
