# Inputs and outputs of gen_soc_ocv_c.py

This folder holds everything the C-data generator depends on, so the full chain can be rerun
offline: lab logs → fitted models → C data and test vectors.

| Path | Role in the chain |
| --- | --- |
| `logs/` | The 15 lab logs (−10, 0, 25, 45 °C; AlzaPower and VARTA), `logs/logs.txt` (the list) and `logs/SHA256SUMS` |
| `logs.txt` | The same list; the generator reads it to find the lab points for the test vectors |
| `ocv_common.py`, `soc_ocv_lut.py`, `soc_ocv_poly.py` | Fit the models from the logs; imported by the generator |
| `models/lut_model.json`, `models/poly_model.json` | Fitted models (20-point table, degree-4 polynomial, spans tuned for 0–35 °C): the input of the C data |
| `c/tools/gen_soc_ocv_c.py` | The generator |
| `c/src/soc_ocv_data.c`, `c/include/soc_ocv_data.h` | Generated C data (from the models) |
| `c/test/test_vectors.h` | Generated test vectors (from the models and the lab logs) |

## Rerun the chain

```
pip install -r requirements.txt
sha256sum -c logs/SHA256SUMS                                          # (inside logs/) check the logs
python soc_ocv_lut.py  fit --logs @logs/logs.txt --out models/lut_model.json
python soc_ocv_poly.py fit --logs @logs/logs.txt --out models/poly_model.json
python c/tools/gen_soc_ocv_c.py                                       # reads ./logs, or $OCV_LOG_DIR
cd c && make test
```

Run from this folder, these commands reproduce the lookup-table model, the C data and the test vectors
byte for byte. The polynomial refit agrees to within 2e-13 % SoC per coefficient (floating-point noise
in the optimizer); the C data stores coefficients in 0.01 % steps, so it is unaffected.
