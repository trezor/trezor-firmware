"""
soc_ocv_poly.py - state of charge from OCV and temperature with polynomials.

    python soc_ocv_poly.py fit --logs LOG [LOG ...] --out models/poly_model.json [--degree 4] [--spans tuned]
    python soc_ocv_poly.py estimate --model models/poly_model.json --ocv 1.32 1.45 --temp 10
    python soc_ocv_poly.py c --model models/poly_model.json > soc_poly_coefs.h

Temperature handling (chosen by cross-validation, see compare_ocv_methods.py and README):
ONE POLYNOMIAL PER CALIBRATED TEMPERATURE. Each applies fully over a temperature span [t_lo, t_hi]
(ocv_common.TUNED_SPANS, tuned for the 0-35 C operating range); between spans the SoC values of the
two neighbouring polynomials are blended linearly, outside all spans the nearest is held. A single
2-D polynomial SoC(OCV, T) is more compact, but with four temperatures and curve shapes that
change strongly in the cold it either underfits, or swings between the calibrated temperatures:
held-out-temperature errors were 2-5x larger.

Each polynomial: SoC = sum c_k x^k, x = (2 OCV - (Vmin + Vmax)) / (Vmax - Vmin) in -1..1, fitted
by least squares CONSTRAINED to a non-negative slope over its OCV range (an unconstrained fit
ripples where SoC saturates near 0 % and 100 %, so more voltage could read as less charge).
Default degree 4: best on unseen cells in the 0-35 C operating range (degree 5 is better only at
45 C; use --degree 5 for hot use). estimate(ocv, temp): OCV is
clamped to each polynomial's range (no extrapolation), SoC to 0..100 %. ocv and temp may be
scalars or arrays. Fitting needs scipy; estimating only numpy.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from ocv_common import blend_spans, check_spans, load_ocv_points, node_spans

DEFAULT_DEGREE = 4
MAX_DEGREE = 10


def fit_curve(ocv, soc, degree: int, monotone: bool = True) -> dict:
    """Least-squares polynomial in normalised OCV, with slope >= 0 enforced at 201 points."""
    v, y = np.asarray(ocv, float), np.asarray(soc, float) / 100.0
    vmin, vmax = float(v.min()), float(v.max())
    x = (2.0 * v - (vmin + vmax)) / (vmax - vmin)
    a = np.vander(x, degree + 1, increasing=True)
    c, *_ = np.linalg.lstsq(a, y, rcond=None)
    if monotone and degree >= 2:
        from scipy.optimize import minimize
        xg = np.linspace(-1.0, 1.0, 201)
        dmat = np.hstack([np.zeros((xg.size, 1)), np.vander(xg, degree, increasing=True) * np.arange(1, degree + 1)])
        h, g = a.T @ a, a.T @ y
        res = minimize(lambda q: 0.5 * q @ h @ q - g @ q, c, jac=lambda q: h @ q - g, method="SLSQP",
                       constraints=[{"type": "ineq", "fun": lambda q: dmat @ q, "jac": lambda q: dmat}],
                       options={"maxiter": 1000, "ftol": 1e-14})
        if not res.success:
            raise RuntimeError(f"monotone fit of degree {degree} failed: {res.message}")
        c = res.x
    return {"vmin": vmin, "vmax": vmax, "coef": [float(100.0 * q) for q in c], "degree": int(degree)}


def eval_curve(node: dict, ocv) -> np.ndarray:
    v = np.clip(np.asarray(ocv, float), node["vmin"], node["vmax"])
    x = (2.0 * v - (node["vmin"] + node["vmax"])) / (node["vmax"] - node["vmin"])
    y = np.zeros_like(x)
    for c in reversed(node["coef"]):                       # Horner
        y = y * x + c
    return np.clip(y, 0.0, 100.0)


def worst_dip(node: dict) -> float:
    """Largest drop of the output below its running maximum over the range, % SoC (0 = monotone)."""
    y = eval_curve(node, np.linspace(node["vmin"], node["vmax"], 4000))
    return float(np.max(np.maximum.accumulate(y) - y))


def select_degree(g, max_degree: int = MAX_DEGREE) -> int:
    """'auto': lowest degree within 2 % of the best leave-one-cell-out RMSE at this temperature."""
    cells = g["cell"].unique()
    if len(cells) < 2:
        return DEFAULT_DEGREE
    rmse = {}
    for d in range(1, max_degree + 1):
        e = [eval_curve(fit_curve(g[g.cell != c].ocv, g[g.cell != c].soc, d), g[g.cell == c].ocv) - g[g.cell == c].soc
             for c in cells]
        e = np.concatenate([np.asarray(x) for x in e])
        rmse[d] = float(np.sqrt(np.mean(e ** 2)))
    best = min(rmse.values())
    return min(d for d, r in rmse.items() if r <= 1.02 * best)


class OcvPoly:
    """nodes: {temperature: {"vmin": V, "vmax": V, "coef": [c0..cd] in %, "degree": d}}"""

    def __init__(self, nodes: dict):
        self.nodes = {float(t): nodes[t] for t in sorted(nodes, key=float)}
        self._lo = np.array([n.get("t_lo", t) for t, n in self.nodes.items()], float)
        self._hi = np.array([n.get("t_hi", t) for t, n in self.nodes.items()], float)
        check_spans(list(zip(self._lo, self._hi)))

    @classmethod
    def fit(cls, points, degree=DEFAULT_DEGREE, spans="tuned") -> "OcvPoly":
        span = node_spans(points, spans)
        nodes = {}
        for t, g in points.groupby("T_set"):
            d = select_degree(g) if degree == "auto" else int(degree)
            nodes[t] = fit_curve(g["ocv"], g["soc"], d)
            nodes[t].update(points=int(len(g)), cells=int(g["cell"].nunique()), worst_dip=worst_dip(nodes[t]),
                            t_lo=span[t][0], t_hi=span[t][1])
        return cls(nodes)

    def estimate(self, ocv, temp):
        """SoC in % for OCV in volts at temperature temp in degC (scalars or arrays)."""
        v = np.atleast_1d(np.asarray(ocv, float))
        per_node = np.vstack([eval_curve(n, v) for n in self.nodes.values()])
        soc = blend_spans(self._lo, self._hi, per_node, np.broadcast_to(np.asarray(temp, float), v.shape))
        return float(soc[0]) if np.ndim(ocv) == 0 and np.ndim(temp) == 0 else soc

    def size_bytes(self) -> int:
        """float32 coefficients + Vmin, Vmax + span start and end, per node."""
        return sum(4 * (len(n["coef"]) + 4) for n in self.nodes.values())

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({"method": "polynomial_per_temperature", "nodes": {str(t): n for t, n in self.nodes.items()}}, f,
                      indent=1)

    @classmethod
    def load(cls, path: str) -> "OcvPoly":
        with open(path) as f:
            return cls({float(t): n for t, n in json.load(f)["nodes"].items()})

    def to_c(self) -> str:
        deg = max(n["degree"] for n in self.nodes.values())
        lines = ["/* SoC(OCV) polynomial per temperature - generated by soc_ocv_poly.py", " * x = (2 v - (vmin + vmax)) / "
                 "(vmax - vmin); SoC = sum c[k] x^k (Horner), clamp 0..100 % */",
                 f"#define POLY_TEMPS ({len(self.nodes)}U)", f"#define POLY_COEFS ({deg + 1}U)",
                 "/* temperature span of each polynomial (degC): inside -> that one, between -> linear blend */",
                 "static const float poly_t_lo[POLY_TEMPS] = {" + ", ".join(f"{x:.1f}f" for x in self._lo) + "};",
                 "static const float poly_t_hi[POLY_TEMPS] = {" + ", ".join(f"{x:.1f}f" for x in self._hi) + "};",
                 "static const float poly_vmin[POLY_TEMPS] = {" + ", ".join(f"{n['vmin']:.5f}f" for n in self.nodes.values()) + "};",
                 "static const float poly_vmax[POLY_TEMPS] = {" + ", ".join(f"{n['vmax']:.5f}f" for n in self.nodes.values()) + "};",
                 "static const float poly_coef[POLY_TEMPS][POLY_COEFS] = {"]
        for n in self.nodes.values():
            c = n["coef"] + [0.0] * (deg + 1 - len(n["coef"]))
            lines.append("    {" + ", ".join(f"{x:.6e}f" for x in c) + "},")
        lines.append("};")
        return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit", help="fit one polynomial per temperature")
    f.add_argument("--logs", nargs="+", required=True, help="globs, paths or @list.txt")
    f.add_argument("--out", default="poly_model.json")
    f.add_argument("--degree", default=str(DEFAULT_DEGREE), help="degree, or 'auto' per temperature (default 4)")
    f.add_argument("--spans", default="tuned", help="tuned (default, 0-35 C), setpoint, measured, or spans JSON")
    e = sub.add_parser("estimate", help="SoC for given OCV(s) and temperature(s)")
    e.add_argument("--model", required=True)
    e.add_argument("--ocv", type=float, nargs="+", required=True)
    e.add_argument("--temp", type=float, nargs="+", required=True, help="one value, or one per OCV")
    c = sub.add_parser("c", help="print the coefficients as a C header")
    c.add_argument("--model", required=True)
    args = ap.parse_args()
    if args.cmd == "fit":
        poly = OcvPoly.fit(load_ocv_points(args.logs), args.degree if args.degree == "auto" else int(args.degree),
                           args.spans)
        poly.save(args.out)
        for t, n in poly.nodes.items():
            print(f"{t:6g} C set point: applies {n['t_lo']:g}..{n['t_hi']:g} C, degree {n['degree']} over "
                  f"{n['vmin']:.3f}-{n['vmax']:.3f} V, worst dip {n['worst_dip']:.3f} %, from {n['points']} OCV points "
                  f"of {n['cells']} cells")
        print(f"{poly.size_bytes()} bytes in total; written to {args.out}")
    elif args.cmd == "estimate":
        poly = OcvPoly.load(args.model)
        temps = args.temp if len(args.temp) == len(args.ocv) else args.temp[:1] * len(args.ocv)
        for v, t, s in zip(args.ocv, temps, poly.estimate(args.ocv, temps)):
            print(f"OCV {v:.4f} V at {t:g} C -> SoC {s:.1f} %")
    else:
        print(OcvPoly.load(args.model).to_c(), end="")


if __name__ == "__main__":
    main()
