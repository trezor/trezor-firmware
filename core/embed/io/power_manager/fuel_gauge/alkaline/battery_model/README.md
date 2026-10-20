# SoC from OCV - C port for STM32H5 (memory-optimized)

C99 port of `soc_ocv_lut.py` and `soc_ocv_poly.py` with the 0–35 °C tuning, for the STM32H5F4
(Cortex-M33). Both estimators are integer-only fixed point:
- **No FPU, no libm, no library calls.** The Cortex-M33 hardware divider covers the divisions.
  Calling them from an interrupt never triggers a lazy FPU context save.
- **No RAM at all.** The calibration data is `const` in flash. The functions are reentrant and
  thread- and ISR-safe.
- **Deterministic.** Results are bit-identical on any compiler and core.

| File | Role |
| --- | --- |
| `include/soc_ocv.h` | API |
| `src/soc_ocv_lut.c` | Lookup-table estimator |
| `src/soc_ocv_poly.c` | Polynomial estimator |
| `src/soc_ocv_temp.c`, `src/soc_ocv_internal.h` | Temperature-span blending shared by both |
| `src/soc_ocv_data.c`, `include/soc_ocv_data.h` | Calibration data, generated from `models/*.json` |
| `tools/gen_soc_ocv_c.py` | Data generator; also writes `test/test_vectors.h` from the Python models |
| `test/test_soc_ocv.c` | Host tests against the Python reference |
| `Makefile` | `make test`, `make misra`, `make size`, `make data` |

## API

```c
#include "soc_ocv.h"

uint16_t soc = soc_ocv_lut(ocv_mv, temp_dc);   /* or soc_ocv_poly(): same inputs and result */
/* ocv_mv:  OCV in mV (uint16_t), the battery voltage ~120 s after load-off
 * temp_dc: temperature in 0.1 degC (int16_t)
 * soc:     0..1000 = 0.0..100.0 % (SOC_OCV_FULL = 1000) */
```

Every input value is valid. OCV outside a curve's range clamps to that curve's end value.
Temperature uses the tuned spans:
- **Inside a span:** that curve alone. The "25 °C" curve covers 19–30 °C.
- **Between two spans:** a linear blend of the neighbouring curves.
- **Colder or hotter than every span:** the nearest curve.

## Memory (arm-none-eabi-gcc 13.2.1, `-mcpu=cortex-m33 -mfpu=fpv5-sp-d16 -mfloat-abi=hard -Os`, gc-sections)

| Linked | Code | Const data | Flash total | RAM | Peak stack |
| --- | --- | --- | --- | --- | --- |
| `soc_ocv_lut()` only | 328 B | 104 B | **432 B** | 0 B | 52 B |
| `soc_ocv_poly()` only | 336 B | 64 B | **400 B** | 0 B | 52 B |
| both (share the 148 B temperature code) | 516 B | 168 B | 684 B | 0 B | 52 B |

Link only the estimator you call. With `-ffunction-sections -fdata-sections` and
`--gc-sections`, the other one and its data are dropped automatically.

**Data encodings** (the earlier float headers were 224 B and 144 B):

| Data | Type and unit | Size | Rounding against the Python model |
| --- | --- | --- | --- |
| Temperature spans | `int8_t`, 0.5 °C | 8 B per model | exact |
| Voltage ranges | `uint16_t`, mV | 16 B per model | exact (data has 1 mV resolution) |
| Table SoC values | `uint8_t`, 0.5 % (0..200) | 80 B | ≤ 0.25 % SoC; stays monotone |
| Polynomial coefficients | `int16_t`, 0.01 % | 40 B | ≤ 0.005 % each |

## Verification (`make test`)

| Check | Lookup table | Polynomial |
| --- | --- | --- |
| Max difference vs the Python float model (2,115 grid points, 1,524 lab points) | 0.28 % SoC | 0.07 % SoC |
| SoC error vs truth on the 1,524 lab OCV points, C / Python | 2.944 % / 2.950 % | 3.496 % / 3.498 % |
| SoC non-decreasing in OCV, −30…70 °C, 800–1800 mV (201,000 evaluations) | pass | pass |
| Largest change per 0.1 °C step | 0.4 % | 0.4 % |
| Extreme inputs (0 / 65535 mV, ±32768 × 0.1 °C) stay in 0..1000 | pass | pass |

The lab-point errors above are for models fitted on all the logs, so they measure the C port's
fidelity, not field accuracy. For accuracy on unseen cells, see the README one level up: in
0–35 °C at the measured temperature, 5.41 % MAE for the table and 5.49 % for the polynomial.

**Overflow safety.** All arithmetic is `int32_t` with proven bounds:
- **Table:** the largest product is 200 × 1000 × 50 = 1e7.
- **Polynomial:** the generator refuses any coefficient set with Σ|c| · 2¹⁵ ≥ 2³¹, so Horner
  evaluation cannot overflow.

## MISRA C:2012

The cppcheck 2.13 MISRA addon (`make misra`) reports no findings, with no deviations or
suppressions. The host build is clean with `-Wall -Wextra -pedantic -Wconversion
-Wsign-conversion -Wdouble-promotion -Wshadow -Werror`. Design points:
- No signed shifts; Q15 scaling uses division.
- No casts of composite expressions.
- Single exit per function, and every `if … else if` ends in `else`.

cppcheck is not a qualified MISRA tool; run your project's checker before release.

## Updating the calibration

After refitting the Python models (new logs, or `tune_spans.py` for another range), run:

```
make data   # regenerates soc_ocv_data.c/.h and the test vectors (needs the logs; OCV_LOG_DIR=<dir>)
make test
```

The generator stops if a new model breaks an encoding assumption. That covers spans that aren't
multiples of 0.5 °C, values out of range, a non-monotone table, or coefficients too large for
`int32_t` Horner evaluation. If the number of temperatures, table points or polynomial degree
changes, only the dimensions in `soc_ocv_data.h` change. The code reads them from there.

## Integration notes (STM32H5F4)

- **Files:** add `src/soc_ocv_temp.c`, `src/soc_ocv_data.c`, and `src/soc_ocv_lut.c` or
  `src/soc_ocv_poly.c` (or both), with `include/` and `src/` on the include path.
- **Hardware:** no peripheral, clock or HAL dependency. It runs from the Secure or the
  Non-secure world, and the MPU only needs the code region executable and the data region
  readable.
- **Run time:** a few dozen integer operations per call. The table walk is fixed-length (at most
  4 temperature spans) and the polynomial loop runs 4 iterations.
