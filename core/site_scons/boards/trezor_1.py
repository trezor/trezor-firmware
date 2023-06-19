from __future__ import annotations

from . import get_hw_model_as_number


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
) -> list[str]:
    features_available: list[str] = []
    board = "trezor_1.h"
    display = "vg-2864ksweg01.c"
    hw_model = get_hw_model_as_number("T1B1")
    hw_revision = 0

    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [f"embed/trezorhal/displays/{display}"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/button.c"]
        features_available.append("button")

    env.get("ENV")["TREZOR_BOARD"] = board

    return features_available
