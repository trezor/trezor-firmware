# SoC from OCV and temperature: lookup table vs polynomial (single alkaline AAA cell)

Two estimators of state of charge from the open-circuit voltage and the temperature, fitted
on the logs at −10, 0, 25 and 45 °C and **tuned for the 0–35 °C operating range**, plus scripts
to compare them and to re-tune them.

| File | Role |
| --- | --- |
| `soc_ocv_lut.py` | Algorithm 1: lookup table, 20 points per temperature |
| `soc_ocv_poly.py` | Algorithm 2: one monotone polynomial per temperature, degree 4 |
| `tune_spans.py` | Tunes the temperature span of each calibration curve for an operating range |
| `compare_ocv_methods.py` | Cross-validation and figures (`results/`) |
| `ocv_common.py` | Log loading, the tuned constants (`TUNED_SPANS`), temperature blending |
| `logs.txt` | The 15 logs used. The uploads folder also holds older exports of the 25 °C cells, and the same cell twice is refused |
| `models/` | Fitted models (JSON), the same data as C headers, and `spans_0_35.json` from the tuner |
| `results/` | `fig1_curves` … `fig6_operating_range` and the CSVs behind them |
| `c/` | Memory-optimized C port for STM32H5: integer-only, 400–432 bytes of flash per estimator, no RAM (see `c/README.md`) |

## API (both algorithms identical)

```python
from soc_ocv_lut import OcvLut
from soc_ocv_poly import OcvPoly

lut = OcvLut.load("models/lut_model.json")
poly = OcvPoly.load("models/poly_model.json")
lut.estimate(1.32, 10.0)                    # OCV in V, measured temperature in °C -> SoC in %
poly.estimate([1.25, 1.40], [0.0, 30.0])    # arrays work too (one temperature, or one per OCV)

model = OcvLut.fit(points, n_points=20, spans="tuned")   # or OcvPoly.fit(points, degree=4, spans="tuned")
```

`spans` can be `"tuned"` (the default, for 0–35 °C), `"setpoint"` (the untuned behaviour),
`"measured"`, or the path of a JSON file from `tune_spans.py`.

```
python soc_ocv_lut.py  fit --logs @logs.txt --out models/lut_model.json  [--points 20] [--spans tuned]
python soc_ocv_poly.py fit --logs @logs.txt --out models/poly_model.json [--degree 4] [--spans tuned]
python soc_ocv_lut.py  estimate --model models/lut_model.json --ocv 1.30 1.40 --temp 10
python soc_ocv_lut.py  c --model models/lut_model.json > soc_lut_tables.h
python tune_spans.py   --logs @logs.txt --range 0 35 --out models/spans_0_35.json
python compare_ocv_methods.py --logs @logs.txt --out results --range 0 35
```

## Tuned for 0–35 °C

**What was tuned, and why.** The temperature a device passes to `estimate()` is the measured
one. The chamber set points in the file names were not what the cells saw: the "25 °C" runs
measured 18.8–36.0 °C (2nd–98th percentile). With curves pinned to their set points, a reading
at 19 °C was blended 24 % toward the very different 0 °C curve. So each calibration curve now
has a **temperature span** in which it applies unblended. Between spans the neighbouring curves
are blended linearly; outside all spans the nearest curve is held.

The spans were chosen by `tune_spans.py`:
- **Scoring:** leave-one-cell-out error of every point whose measured temperature lies in
  0–35 °C (±1 °C), estimated at that temperature, with each 5 °C band weighted equally.
- **Search limits:** a span may only cover temperatures actually measured during its runs.

| Calibration run | Span (from) | Span (to) |
| --- | --- | --- |
| -10 °C | -11 °C | -11 °C |
| 0 °C | -0.5 °C | -0.5 °C |
| 25 °C | 19 °C | 30 °C |
| 45 °C | 44.5 °C | 44.5 °C |

The warm curve applies from 19 to 30 °C, then blends toward the 45 °C curve. The other runs held
their temperature, so their spans are single points. The −10 °C point matters only below 0 °C.

**Polynomial degree.** Degree 4 is best inside the operating range
(4.38 % band-mean MAE). Degree 5
is better only at 45 °C, so use `--degree 5` for hot use.

**Table size.** 20 points per temperature is unchanged; 10–100 points all score
4.24–4.27 % on unseen cells.

**Result:** MAE on unseen cells at their measured temperature, per 5 °C band (number of
points in brackets):

| Configuration | 0-5 °C (201) | 15-20 °C (33) | 20-25 °C (98) | 25-30 °C (343) | 30-35 °C (157) | MAE, all | Band mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lookup table, untuned | 13.1 | 2.5 | 5.2 | 4.1 | 1.2 | 5.79 | 5.23 |
| **Lookup table, tuned** | 13.1 | 0.2 | 3.4 | 4.2 | 0.6 | 5.41 | 4.31 |
| Polynomial, untuned (degree 5) | 13.1 | 2.3 | 5.4 | 4.2 | 1.6 | 5.90 | 5.29 |
| **Polynomial, tuned (degree 4)** | 13.0 | 0.3 | 3.5 | 4.3 | 0.8 | 5.49 | 4.38 |

**Reading this table:**
- **The gain is between 15 and 35 °C.** There the band mean falls from about 3.3 to 2.1 % for the
  table.
- **The 0–5 °C band is unchanged at about 13 %.** It holds the 0 °C runs, where the two brands differ
  by up to 40 % SoC at the same OCV. No constant can fix that; only voltage under load (the
  pulse-based estimator) or brand-specific tables can.
- **The edge bands rest on one brand each.** 15–20 °C is AlzaPower only and 30–35 °C is VARTA
  only. Nothing was measured between 0 and 18 °C, so the blend there is untested
  interpolation. A run at about 10 °C is the most valuable next measurement; after it, rerun
  `tune_spans.py` and refit.

## How the two algorithms work

**Lookup table (`soc_ocv_lut.py`).**
- **Fit, per temperature:** isotonic regression of SoC on OCV, the best monotone fit, sampled at 20
  points evenly spread over that temperature's OCV range (15–26 mV apart).
- **Storage:** one `uint16` SoC value per point, plus a float32 start voltage, step and span
  edges. 224 bytes for all four temperatures.
- **Estimate:** interpolate linearly along OCV inside the table or tables in play, then apply the
  span rule in temperature.

**Polynomial (`soc_ocv_poly.py`).**
- **Fit, per temperature:** SoC = Σ cₖ·xᵏ, with x the OCV normalized to −1…1 over that
  temperature's range, degree 4.
- **Constraint:** least squares with the slope forced non-negative. An unconstrained fit ripples
  where SoC flattens near 0 and 100 %.
- **Storage:** 144 bytes for all four temperatures.
- **Estimate:** OCV is clamped to each polynomial's range; temperature uses the same span rule.

**Why one curve per temperature, rather than a single 2-D polynomial in OCV and T.** The
comparison script scores both against a temperature held out of the fit (`fig4`):

| Approach | Unseen cell | Held-out 25 °C | Held-out 45 °C | Held-out −10 °C |
| --- | --- | --- | --- | --- |
| Lookup table + spans | 4.3 % | 8.8 % | 4.8 % | 18.5 % |
| Polynomial per temperature + spans | 4.5 % | 8.6 % | 4.9 % | 18.6 % |
| 2-D surfaces (OCV degree 5–6 × T degree 2–3) | 4.3–4.4 % | 12–17 % | 17–25 % | 7–18 % |

The surfaces only win when extrapolating to −10 °C. Between and above the calibrated
temperatures they swing badly, because four temperatures cannot pin down the strong change in
curve shape between 0 and 25 °C.

## Results at the calibrated temperatures (MAE / P95 in % SoC)

| Temperature | Table, unseen cell | Polynomial, unseen cell | Table, unseen temperature | Polynomial, unseen temperature |
| --- | --- | --- | --- | --- |
| -10 °C | 4.9 / 13 | 4.7 / 13 | 18.5 / 39 | 18.6 / 41 |
| 0 °C | 13.0 / 33 | 12.8 / 31 | 12.2 / 31 | 11.9 / 30 |
| 25 °C | 3.3 / 8 | 3.4 / 9 | 8.8 / 17 | 8.6 / 17 |
| 45 °C | 2.2 / 6 | 2.8 / 9 | 4.8 / 11 | 4.9 / 10 |
| all | 4.3 / 14 | 4.5 / 14 | 8.2 / 22 | 8.2 / 21 |

- **Unseen cell:** fitted on every other cell and scored at the cell's own temperature set point.
- **Unseen temperature:** fitted without that temperature and estimated from the others; for
  −10 °C and 45 °C this is extrapolation.

Both algorithms are equally accurate. What limits them is the spread between cells and brands,
not the model.

## Caveats

- **The OCV is the voltage after a ~120 s rest.** After a rest of hours the cell reads higher, so
  calibrate with the same rest you will use in the device.
- **SoC is your `state_of_charge_pct`.** It reaches 0 % close to the first battery voltage below
  0.8 V.
- **The tuned spans fit these 15 logs.** After adding logs, rerun `tune_spans.py`, then refit both
  models with `--spans models/<new>.json`, or copy the result into `TUNED_SPANS` in
  `ocv_common.py`.

## C evaluation (with the generated headers)

```c
/* lookup table: models/soc_lut_tables.h */
static float lut_node(uint32_t k, float v)
{
    const float x = (v - lut_v0[k]) / lut_step[k];
    float s;
    if (x <= 0.0f) { s = (float)lut_soc[k][0]; }
    else if (x >= (float)(LUT_POINTS - 1U)) { s = (float)lut_soc[k][LUT_POINTS - 1U]; }
    else {
        const uint32_t i = (uint32_t)x;
        s = (float)lut_soc[k][i] + ((x - (float)i) * ((float)lut_soc[k][i + 1U] - (float)lut_soc[k][i]));
    }
    return s * 0.01f;
}

/* polynomial: models/soc_poly_coefs.h */
static float poly_node(uint32_t k, float v)
{
    const float vc = (v < poly_vmin[k]) ? poly_vmin[k] : ((v > poly_vmax[k]) ? poly_vmax[k] : v);
    const float x = ((2.0f * vc) - (poly_vmin[k] + poly_vmax[k])) / (poly_vmax[k] - poly_vmin[k]);
    float y = 0.0f;
    for (int32_t c = (int32_t)POLY_COEFS - 1; c >= 0; c--) { y = (y * x) + poly_coef[k][c]; }
    return (y < 0.0f) ? 0.0f : ((y > 100.0f) ? 100.0f : y);
}

/* temperature spans, the same for both (shown for the table; use the poly_* names for the polynomial):
 * inside a span -> that curve; between two spans -> linear blend; outside all spans -> nearest curve */
float soc_from_ocv(float v, float t)
{
    uint32_t j = 0U;
    float s;
    while ((j < (LUT_TEMPS - 1U)) && (t > lut_t_hi[j])) { j++; }   /* first span ending at or above t */
    if ((t >= lut_t_lo[j]) || (j == 0U) || (t > lut_t_hi[j])) {
        s = lut_node(j, v);                                          /* inside, colder or hotter than all */
    } else {
        const float w = (t - lut_t_hi[j - 1U]) / (lut_t_lo[j] - lut_t_hi[j - 1U]);
        s = ((1.0f - w) * lut_node(j - 1U, v)) + (w * lut_node(j, v));
    }
    return s;
}
```
