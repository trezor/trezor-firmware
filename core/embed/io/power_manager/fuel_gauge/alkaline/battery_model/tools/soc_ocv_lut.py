"""
soc_ocv_lut.py - state of charge from OCV and temperature with a reduced lookup table.

    python soc_ocv_lut.py fit --logs LOG [LOG ...] --out models/lut_model.json [--points 20] [--spans tuned]
    python soc_ocv_lut.py estimate --model models/lut_model.json --ocv 1.32 1.45 --temp 10
    python soc_ocv_lut.py c --model models/lut_model.json > soc_lut_tables.h

Fit, per temperature set point (taken from the log file names): isotonic regression of SoC on
OCV over all cells - the best monotone fit, so a higher voltage never reads as less charge -
sampled at N points spread evenly over that temperature's OCV range (default N = 20: one
uint16 SoC value per point, plus the start voltage and step; 20 points give the same accuracy on
unseen cells as 40, see compare_ocv_methods.py).

Each table applies fully over a temperature span [t_lo, t_hi] (ocv_common.TUNED_SPANS, tuned for
the 0-35 C operating range: the "25 C" table covers 19-30 C, the others are points at their
measured temperature).

estimate(ocv, temp):
  1. inside a table, interpolate linearly along OCV (OCV outside a table's range clamps to its
     end value, i.e. 0 % or 100 %)
  2. temp inside a span: that table; between two spans: linear blend of the two neighbouring
     tables; colder or hotter than all spans: the nearest table
ocv and temp may be scalars or arrays.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from ocv_common import blend_spans, check_spans, load_ocv_points, node_spans

DEFAULT_POINTS = 20


def isotonic_increasing(y: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators: least-squares non-decreasing fit to y (in the given order)."""
    vals, wts, cnts = [], [], []
    for yi in np.asarray(y, float):
        vals.append(yi)
        wts.append(1.0)
        cnts.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, c2 = vals.pop(), wts.pop(), cnts.pop()
            v1, w1, c1 = vals.pop(), wts.pop(), cnts.pop()
            vals.append((v1 * w1 + v2 * w2) / (w1 + w2))
            wts.append(w1 + w2)
            cnts.append(c1 + c2)
    return np.repeat(vals, cnts)


def monotone_curve(ocv, soc) -> tuple[np.ndarray, np.ndarray]:
    """Isotonic fit of soc on ocv, returned at the unique OCV values."""
    order = np.argsort(np.asarray(ocv, float), kind="stable")
    x = np.asarray(ocv, float)[order]
    y = isotonic_increasing(np.asarray(soc, float)[order])
    ux, inv = np.unique(x, return_inverse=True)
    return ux, np.bincount(inv, weights=y) / np.bincount(inv)


class OcvLut:
    """nodes: {temperature: {"v0": V, "step": V, "soc": [N values in %], ...}}"""

    def __init__(self, nodes: dict):
        self.nodes = {float(t): nodes[t] for t in sorted(nodes, key=float)}
        self._lo = np.array([n.get("t_lo", t) for t, n in self.nodes.items()], float)
        self._hi = np.array([n.get("t_hi", t) for t, n in self.nodes.items()], float)
        check_spans(list(zip(self._lo, self._hi)))

    # ------------------------------------------------------------ fitting
    @staticmethod
    def fit_node(ocv, soc, n_points: int = DEFAULT_POINTS) -> dict:
        ux, uy = monotone_curve(ocv, soc)
        grid = np.linspace(ux[0], ux[-1], n_points)
        table = np.round(np.clip(np.interp(grid, ux, uy), 0.0, 100.0), 2)
        return {"v0": float(ux[0]), "step": float((ux[-1] - ux[0]) / (n_points - 1)), "soc": table.tolist(),
                "points": int(len(ux)), "cells": None}

    @classmethod
    def fit(cls, points, n_points: int = DEFAULT_POINTS, spans="tuned") -> "OcvLut":
        span = node_spans(points, spans)
        nodes = {}
        for t, g in points.groupby("T_set"):
            nodes[t] = cls.fit_node(g["ocv"], g["soc"], n_points)
            nodes[t].update(points=int(len(g)), cells=int(g["cell"].nunique()), t_lo=span[t][0], t_hi=span[t][1])
        return cls(nodes)

    # ------------------------------------------------------------ estimating
    def _node_curve(self, node: dict, ocv: np.ndarray) -> np.ndarray:
        grid = node["v0"] + node["step"] * np.arange(len(node["soc"]))
        return np.interp(ocv, grid, node["soc"])

    def estimate(self, ocv, temp):
        """SoC in % for OCV in volts at temperature temp in degC (scalars or arrays)."""
        v = np.atleast_1d(np.asarray(ocv, float))
        per_node = np.vstack([self._node_curve(n, v) for n in self.nodes.values()])
        soc = blend_spans(self._lo, self._hi, per_node, np.broadcast_to(np.asarray(temp, float), v.shape))
        return float(soc[0]) if np.ndim(ocv) == 0 and np.ndim(temp) == 0 else soc

    def size_bytes(self) -> int:
        """uint16 SoC per point + float32 start voltage, step, span start and span end, per node."""
        return sum(2 * len(n["soc"]) + 4 * 4 for n in self.nodes.values())

    # ------------------------------------------------------------ files
    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({"method": "lookup_table", "nodes": {str(t): n for t, n in self.nodes.items()}}, f, indent=1)

    @classmethod
    def load(cls, path: str) -> "OcvLut":
        with open(path) as f:
            return cls({float(t): n for t, n in json.load(f)["nodes"].items()})

    def to_c(self) -> str:
        n = len(next(iter(self.nodes.values()))["soc"])
        lines = ["/* SoC(OCV, T) lookup tables - generated by soc_ocv_lut.py */", "#include <stdint.h>",
                 f"#define LUT_TEMPS ({len(self.nodes)}U)", f"#define LUT_POINTS ({n}U)",
                 "/* temperature span of each table (degC): inside -> that table, between -> linear blend */",
                 "static const float lut_t_lo[LUT_TEMPS] = {" + ", ".join(f"{x:.1f}f" for x in self._lo) + "};",
                 "static const float lut_t_hi[LUT_TEMPS] = {" + ", ".join(f"{x:.1f}f" for x in self._hi) + "};",
                 "static const float lut_v0[LUT_TEMPS] = {" + ", ".join(f"{d['v0']:.5f}f" for d in self.nodes.values()) + "};",
                 "static const float lut_step[LUT_TEMPS] = {" + ", ".join(f"{d['step']:.7f}f" for d in self.nodes.values()) + "};",
                 "/* SoC in 0.01 % */", "static const uint16_t lut_soc[LUT_TEMPS][LUT_POINTS] = {"]
        for d in self.nodes.values():
            lines.append("    {" + ", ".join(f"{int(round(s * 100))}U" for s in d["soc"]) + "},")
        lines.append("};")
        return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit", help="build the tables from logs")
    f.add_argument("--logs", nargs="+", required=True, help="globs, paths or @list.txt")
    f.add_argument("--out", default="lut_model.json")
    f.add_argument("--points", type=int, default=DEFAULT_POINTS, help="points per temperature (default 20)")
    f.add_argument("--spans", default="tuned", help="tuned (default, 0-35 C), setpoint, measured, or spans JSON")
    e = sub.add_parser("estimate", help="SoC for given OCV(s) and temperature(s)")
    e.add_argument("--model", required=True)
    e.add_argument("--ocv", type=float, nargs="+", required=True)
    e.add_argument("--temp", type=float, nargs="+", required=True, help="one value, or one per OCV")
    c = sub.add_parser("c", help="print the tables as a C header")
    c.add_argument("--model", required=True)
    args = ap.parse_args()
    if args.cmd == "fit":
        lut = OcvLut.fit(load_ocv_points(args.logs), args.points, args.spans)
        lut.save(args.out)
        for t, n in lut.nodes.items():
            print(f"{t:6g} C set point: applies {n['t_lo']:g}..{n['t_hi']:g} C, {len(n['soc'])} points, "
                  f"{n['v0']:.3f}-{n['v0'] + n['step'] * (len(n['soc']) - 1):.3f} V ({1000 * n['step']:.1f} mV step), "
                  f"from {n['points']} OCV points of {n['cells']} cells")
        print(f"{lut.size_bytes()} bytes in total; written to {args.out}")
    elif args.cmd == "estimate":
        lut = OcvLut.load(args.model)
        temps = args.temp if len(args.temp) == len(args.ocv) else args.temp[:1] * len(args.ocv)
        for v, t, s in zip(args.ocv, temps, lut.estimate(args.ocv, temps)):
            print(f"OCV {v:.4f} V at {t:g} C -> SoC {s:.1f} %")
    else:
        print(OcvLut.load(args.model).to_c(), end="")


if __name__ == "__main__":
    main()
