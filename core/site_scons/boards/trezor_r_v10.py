from __future__ import annotations

from . import get_hw_model_as_number


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
) -> list[str]:
    features_available: list[str] = []
    hw_model = get_hw_model_as_number("T2B1")
    hw_revision = 10
    board = "trezor_r_v10.h"
    display = "vg-2864ksweg01.c"

    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [f"embed/trezorhal/displays/{display}"]

    sources += [f"embed/trezorhal/i2c.c"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/button.c"]
        features_available.append("button")

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/sbu.c"]
        features_available.append("sbu")

    if "consumption_mask" in features_wanted:
        sources += ["embed/trezorhal/consumption_mask.c"]

    env.get("ENV")["TREZOR_BOARD"] = board

    return features_available
