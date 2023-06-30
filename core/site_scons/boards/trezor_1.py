from __future__ import annotations

from . import get_hw_model_as_number
from .stm32f4_common import stm32f4_common_files


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    features_available: list[str] = []
    board = "trezor_1.h"
    display = "vg-2864ksweg01.c"
    hw_model = get_hw_model_as_number("T1B1")
    hw_revision = 0

    mcu = "STM32F405xx"

    stm32f4_common_files(env, defines, sources, paths)

    env.get("ENV")["CPU_ASFLAGS"] = "-mthumb -mcpu=cortex-m3 -mfloat-abi=soft"
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mtune=cortex-m3 -mcpu=cortex-m3 -mfloat-abi=soft "
    env.get("ENV")["RUST_TARGET"] = "thumbv7m-none-eabi"

    defines += [mcu]
    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [
        "embed/models/model_T1B1_layout.c",
    ]
    sources += [f"embed/trezorhal/stm32f4/displays/{display}"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/button.c"]
        features_available.append("button")

    if "usb" in features_wanted:
        sources += [
            "embed/trezorhal/stm32f4/usb.c",
            "embed/trezorhal/stm32f4/usbd_conf.c",
            "embed/trezorhal/stm32f4/usbd_core.c",
            "embed/trezorhal/stm32f4/usbd_ctlreq.c",
            "embed/trezorhal/stm32f4/usbd_ioreq.c",
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c",
        ]
        features_available.append("usb")

    env.get("ENV")["TREZOR_BOARD"] = board
    env.get("ENV")["MCU_TYPE"] = mcu

    return features_available
