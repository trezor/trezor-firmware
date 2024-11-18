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
    hw_model = get_hw_model_as_number("T3B1")
    hw_revision = "B"

    defines += ["FRAMEBUFFER"]
    features_available.append("framebuffer")
    features_available.append("display_mono")

    mcu = "STM32U585xx"
    linker_script = """embed/trezorhal/stm32u5/linker/u58/{target}.ld"""

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

    sources += ["embed/trezorhal/stm32u5/xdisplay/vg-2864/display_driver.c"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/button.c"]
        features_available.append("button")
        defines += ["USE_BUTTON=1"]

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/sbu.c"]
        features_available.append("sbu")
        defines += ["USE_SBU=1"]

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
        sources += ["embed/trezorhal/stm32u5/i2c_bus.c"]
        sources += ["embed/trezorhal/stm32u5/optiga_hal.c"]
        sources += ["embed/trezorhal/optiga/optiga.c"]
        sources += ["embed/trezorhal/optiga/optiga_commands.c"]
        sources += ["embed/trezorhal/optiga/optiga_transport.c"]
        sources += ["vendor/trezor-crypto/hash_to_curve.c"]
        features_available.append("optiga")
        defines += ["USE_OPTIGA=1"]
        defines += ["USE_I2C=1"]

    if "consumption_mask" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/consumption_mask.c"]
        sources += ["vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_tim.c"]
        defines += ["USE_CONSUMPTION_MASK=1"]

    defines += [
        "USE_HASH_PROCESSOR=1",
        "USE_STORAGE_HWKEY=1",
        "USE_TAMPER=1",
        "USE_FLASH_BURST=1",
        "USE_RESET_TO_BOOT=1",
        "USE_OEM_KEYS_CHECK=1",
        "USE_PVD=1",
    ]

    env.get("ENV")["TREZOR_BOARD"] = board
    env.get("ENV")["MCU_TYPE"] = mcu
    env.get("ENV")["LINKER_SCRIPT"] = linker_script

    defs = env.get("CPPDEFINES_IMPLICIT")
    defs += ["__ARM_FEATURE_CMSE=3"]

    return features_available
