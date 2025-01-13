from __future__ import annotations

from .. import get_hw_model_as_number
from ..stm32f4_common import stm32f4_common_files


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    features_available: list[str] = []
    hw_model = get_hw_model_as_number("T2B1")
    hw_revision = 10
    board = "T2B1/boards/trezor_r_v10.h"

    defines += [
        "FRAMEBUFFER",
        ("DISPLAY_RESX", "128"),
        ("DISPLAY_RESY", "64"),
    ]
    features_available.append("framebuffer")
    features_available.append("display_mono")

    mcu = "STM32F427xx"

    stm32f4_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16"
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16 -mtune=cortex-m4 "
    env.get("ENV")["RUST_TARGET"] = "thumbv7em-none-eabihf"

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("HSE_VALUE", "8000000"),
        ("USE_HSE", "1"),
    ]

    sources += ["embed/io/display/vg-2864/display_driver.c"]
    paths += ["embed/io/display/inc"]

    if "input" in features_wanted:
        sources += ["embed/io/button/stm32/button.c"]
        paths += ["embed/io/button/inc"]
        features_available.append("button")
        defines += [("USE_BUTTON", "1")]

    if "sbu" in features_wanted:
        sources += ["embed/io/sbu/stm32/sbu.c"]
        paths += ["embed/io/sbu/inc"]
        features_available.append("sbu")
        defines += [("USE_SBU", "1")]

    if "consumption_mask" in features_wanted:
        sources += ["embed/sec/consumption_mask/stm32f4/consumption_mask.c"]
        sources += [
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c"
        ]
        paths += ["embed/sec/consumption_mask/inc"]
        defines += [("USE_CONSUMPTION_MASK", "1")]

    if "usb" in features_wanted:
        sources += [
            "embed/io/usb/stm32/usb_class_hid.c",
            "embed/io/usb/stm32/usb_class_vcp.c",
            "embed/io/usb/stm32/usb_class_webusb.c",
            "embed/io/usb/stm32/usb.c",
            "embed/io/usb/stm32/usbd_conf.c",
            "embed/io/usb/stm32/usbd_core.c",
            "embed/io/usb/stm32/usbd_ctlreq.c",
            "embed/io/usb/stm32/usbd_ioreq.c",
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c",
        ]
        features_available.append("usb")
        paths += ["embed/io/usb/inc"]
        defines += [("USE_USB", "1")]

    if "optiga" in features_wanted:
        sources += ["embed/io/i2c_bus/stm32f4/i2c_bus.c"]
        sources += ["embed/sec/optiga/stm32/optiga_hal.c"]
        sources += ["embed/sec/optiga/optiga.c"]
        sources += ["embed/sec/optiga/optiga_commands.c"]
        sources += ["embed/sec/optiga/optiga_config.c"]
        sources += ["embed/sec/optiga/optiga_transport.c"]
        sources += ["vendor/trezor-crypto/hash_to_curve.c"]
        paths += ["embed/io/i2c_bus/inc"]
        paths += ["embed/sec/optiga/inc"]
        features_available.append("optiga")
        defines += [("USE_OPTIGA", "1")]
        defines += [("USE_I2C", "1")]

    defines += [("USE_PVD", "1")]

    return features_available
