from __future__ import annotations

from .. import get_hw_model_as_number
from ..stm32u5_common import stm32u5_common_files


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    features_available: list[str] = []
    board = "T3B1/boards/trezor_t3b1_revB.h"
    display = "vg-2864ksweg01.c"
    hw_model = get_hw_model_as_number("T3B1")
    hw_revision = "B"

    if "new_rendering" in features_wanted:
        defines += ["XFRAMEBUFFER"]
        features_available.append("xframebuffer")
        features_available.append("display_mono")

    mcu = "STM32U585xx"
    linker_script = "stm32u58"

    stm32u5_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 "
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 -mtune=cortex-m33 -mcmse "
    env.get("ENV")["RUST_TARGET"] = "thumbv8m.main-none-eabihf"

    defines += [mcu]
    defines += [f'TREZOR_BOARD=\\"{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={ord(hw_revision)}"]
    sources += [
        "embed/models/T3B1/model_T3B1_layout.c",
    ]

    if "new_rendering" in features_wanted:
        sources += ["embed/trezorhal/xdisplay_legacy.c"]
        sources += ["embed/trezorhal/stm32u5/xdisplay/vg-2864/display_driver.c"]
    else:
        sources += [f"embed/trezorhal/stm32u5/displays/{display}"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/button.c"]
        features_available.append("button")

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/sbu.c"]
        features_available.append("sbu")

    if "usb" in features_wanted:
        sources += [
            "embed/trezorhal/stm32u5/usb/usb_class_hid.c",
            "embed/trezorhal/stm32u5/usb/usb_class_vcp.c",
            "embed/trezorhal/stm32u5/usb/usb_class_webusb.c",
            "embed/trezorhal/stm32u5/usb/usb.c",
            "embed/trezorhal/stm32u5/usb/usbd_conf.c",
            "embed/trezorhal/stm32u5/usb/usbd_core.c",
            "embed/trezorhal/stm32u5/usb/usbd_ctlreq.c",
            "embed/trezorhal/stm32u5/usb/usbd_ioreq.c",
            "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_ll_usb.c",
        ]
        features_available.append("usb")

    if "optiga" in features_wanted:
        defines += ["USE_OPTIGA=1"]
        sources += ["embed/trezorhal/stm32u5/i2c.c"]
        sources += ["embed/trezorhal/stm32u5/optiga_hal.c"]
        sources += ["embed/trezorhal/optiga/optiga.c"]
        sources += ["embed/trezorhal/optiga/optiga_commands.c"]
        sources += ["embed/trezorhal/optiga/optiga_transport.c"]
        sources += ["vendor/trezor-crypto/hash_to_curve.c"]
        features_available.append("optiga")

    if "consumption_mask" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/consumption_mask.c"]
        sources += ["vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_tim.c"]

    env.get("ENV")["TREZOR_BOARD"] = board
    env.get("ENV")["MCU_TYPE"] = mcu
    env.get("ENV")["LINKER_SCRIPT"] = linker_script

    defs = env.get("CPPDEFINES_IMPLICIT")
    defs += ["__ARM_FEATURE_CMSE=3"]

    return features_available
