"""
ocv_common.py - shared log loading for the OCV -> SoC scripts.

Every log is one cell (one *_data_0x4?.csv file). One point is taken per rest period:
  ocv    column 'ocv_voltage': the battery voltage on the last sample of each ~120 s rest,
         as written by the logger's analysis script. Older logs without that column: the last
         sample of every rest (|I| < 5 mA) lasting at least 100 s.
  soc    column 'state_of_charge_pct' on the same row, clipped to 0..100 %. Older logs:
         coulomb count from the first row (100 %) to the last row (0 %).
  T_set  temperature set point from the file name ('_25C_'), used to group logs into models;
  T_meas measured temperature on that row (reported, not used for grouping).

Adding logs for another temperature needs no code change: they form a new temperature node.
Logs can be given as glob patterns, file paths, or @list.txt (one path per line); the same cell
appearing twice (e.g. two exports of one log) is refused.
"""
from __future__ import annotations

import glob
import json
import os
import re

import numpy as np
import pandas as pd

NAME_RE = re.compile(r"AAA_(?P<brand>[A-Za-z]+)_.*?_(?P<temp>-?\d+)C_.*?_data_(?P<addr>0x[0-9A-Fa-f]+)")
REST_MA = 5.0          # rest threshold for logs without 'ocv_voltage'
MIN_REST_S = 100.0     # minimum rest length for those logs


def parse_name(path: str) -> dict:
    m = NAME_RE.search(os.path.basename(path))
    if not m:
        raise ValueError(f"cannot read brand / temperature / address from {path}")
    return dict(brand=m.group("brand"), T_set=float(m.group("temp")), addr=m.group("addr"))


def _points_from_columns(df: pd.DataFrame) -> pd.DataFrame:
    rows = df[df["ocv_voltage"].notna()]
    return pd.DataFrame(dict(ocv=rows["ocv_voltage"].to_numpy(float),
                             soc=np.clip(rows["state_of_charge_pct"].to_numpy(float), 0.0, 100.0),
                             T_meas=rows["temperature_C"].to_numpy(float)))


def _points_from_rests(df: pd.DataFrame) -> pd.DataFrame:
    t = df["timestamp_unix"].to_numpy(float)
    i = df["current_mA"].to_numpy(float)
    v = df["bus_voltage_V"].to_numpy(float)
    q = np.concatenate([[0.0], np.cumsum(0.5 * (i[1:] + i[:-1]) * np.diff(t) / 3600.0)])
    soc = 100.0 * (1.0 - q / q[-1])
    rest = np.abs(i) < REST_MA
    out, k, n = [], 0, len(t)
    while k < n:
        if not rest[k]:
            k += 1
            continue
        a = k
        while k < n and rest[k]:
            k += 1
        b = k - 1                                   # last rest sample
        if k < n and t[b] - t[a] >= MIN_REST_S:     # rest followed by a load
            out.append((v[b], soc[b], df["temperature_C"].iloc[b]))
    return pd.DataFrame(out, columns=["ocv", "soc", "T_meas"])


def expand_logs(patterns) -> list[str]:
    """Files from one or more glob patterns, file paths, or @list.txt files (one path per line)."""
    if isinstance(patterns, str):
        patterns = [patterns]
    files = []
    for p in patterns:
        if p.startswith("@"):
            base = os.path.dirname(os.path.abspath(p[1:]))
            for line in open(p[1:]):
                line = line.strip()
                if line and not line.startswith("#"):
                    files.append(line if os.path.isabs(line) else os.path.join(base, line))
        else:
            files.extend(sorted(glob.glob(p)) or [p])
    files = [f for f in dict.fromkeys(files)]
    missing = [f for f in files if not os.path.exists(f)]
    if missing or not files:
        raise SystemExit(f"log files not found: {missing or patterns}")
    return files


def load_ocv_points(patterns) -> pd.DataFrame:
    """All OCV points of the given logs (globs, paths or @list.txt): one row per rest period."""
    files = expand_logs(patterns)
    frames = []
    for path in files:
        meta = parse_name(path)
        df = pd.read_csv(path, comment="#", skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
        df = df.sort_values("timestamp_unix").reset_index(drop=True)
        has_cols = {"ocv_voltage", "state_of_charge_pct"} <= set(df.columns)
        pts = _points_from_columns(df) if has_cols else _points_from_rests(df)
        pts["brand"], pts["addr"], pts["T_set"] = meta["brand"], meta["addr"], meta["T_set"]
        pts["cell"] = f"{meta['brand']}_{meta['T_set']:g}C_{meta['addr']}"
        pts["source"] = "columns" if has_cols else "rests"
        pts["file"] = os.path.basename(path)
        frames.append(pts)
    pts = pd.concat(frames, ignore_index=True)
    dup = pts.groupby("cell")["file"].nunique()
    if (dup > 1).any():
        raise SystemExit(f"the same cell appears in several files: {list(dup[dup > 1].index)}")
    return pts


# Temperature span [t_lo, t_hi] over which each calibration curve applies fully, keyed by the set
# point in the log file names. Between spans the two neighbouring curves are blended linearly;
# outside all spans the nearest curve is held. Tuned for the 0-35 C operating range with
# tune_spans.py (leave-one-cell-out error at the MEASURED temperature, each 5 C band weighted
# equally): python tune_spans.py --logs @logs.txt --range 0 35. The "25 C" runs actually
# measured 18-37 C: their curve applies unblended from 19 to 30 C - no mixing with the very
# different 0 C curve where the data shows the warm curve holds - and blends toward the 45 C curve
# above 30 C. Single-temperature runs are points at (about) their measured temperature.
TUNED_SPANS = {-10.0: (-11.0, -11.0), 0.0: (-0.5, -0.5), 25.0: (19.0, 30.0), 45.0: (44.5, 44.5)}


def node_spans(points: pd.DataFrame, spans="tuned") -> dict:
    """{T_set: (t_lo, t_hi)} for every set point in points.

    spans: "tuned"    TUNED_SPANS; set points it does not list get their measured median
           "setpoint" the set point itself (the behaviour before tuning)
           "measured" the median measured temperature of each set point's logs
           dict or path to a JSON file {set point: [t_lo, t_hi]} (e.g. from tune_spans.py)"""
    med = points.groupby("T_set")["T_meas"].median()
    if isinstance(spans, str) and spans not in ("tuned", "setpoint", "measured"):
        with open(spans) as f:
            spans = {float(k): tuple(v) for k, v in json.load(f).items()}
    out = {}
    for t in sorted(points["T_set"].unique()):
        if spans == "setpoint":
            out[t] = (t, t)
        elif spans == "measured":
            out[t] = (round(float(med[t]), 1),) * 2
        else:
            table = TUNED_SPANS if spans == "tuned" else spans
            out[t] = tuple(float(x) for x in table.get(t, (round(float(med[t]), 1),) * 2))
    check_spans([out[t] for t in sorted(out)])
    return out


def check_spans(spans: list) -> None:
    for (lo, hi), (lo2, _) in zip(spans, spans[1:] + [(np.inf, np.inf)]):
        if not (lo <= hi < lo2):
            raise ValueError(f"temperature spans must be ordered and disjoint: {spans}")


def blend_spans(t_lo, t_hi, per_node: np.ndarray, temp) -> np.ndarray:
    """Temperature blending between per-node results.

    t_lo, t_hi: span of each node (K, ordered, disjoint); per_node: (K, n) values of every node at
    the n query points; temp: scalar or (n,). Inside a span: that node; in a gap: linear blend of
    the two neighbours; colder or hotter than all spans: the nearest node."""
    lo, hi = np.asarray(t_lo, float), np.asarray(t_hi, float)
    k, n = per_node.shape
    t = np.broadcast_to(np.asarray(temp, float), (n,))
    j = np.minimum(np.searchsorted(hi, t, side="left"), k - 1)      # first node whose span ends >= t
    cols = np.arange(n)
    out = per_node[j, cols].astype(float)
    gap = (t < lo[j]) & (j > 0)                                      # between span j-1 and span j
    if np.any(gap):
        a = j[gap] - 1
        w = (t[gap] - hi[a]) / (lo[j[gap]] - hi[a])
        out[gap] = (1.0 - w) * per_node[a, cols[gap]] + w * per_node[j[gap], cols[gap]]
    return out
