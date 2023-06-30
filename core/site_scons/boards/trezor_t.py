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
    board = "trezor_t.h"
    display = "st7789v.c"
    hw_model = get_hw_model_as_number("T2T1")
    hw_revision = 0
    features_available.append("disp_i8080_8bit_dw")

    mcu = "STM32F427xx"

    stm32f4_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16"
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16 -mtune=cortex-m4 "
    env.get("ENV")["RUST_TARGET"] = "thumbv7em-none-eabihf"

    defines += [mcu]
    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [
        "embed/models/model_T2T1_layout.c",
    ]
    sources += [f"embed/trezorhal/stm32f4/displays/{display}"]
    sources += ["embed/trezorhal/stm32f4/backlight_pwm.c"]
    sources += [
        "embed/trezorhal/stm32f4/displays/panels/tf15411a.c",
    ]
    sources += [
        "embed/trezorhal/stm32f4/displays/panels/154a.c",
    ]
    sources += [
        "embed/trezorhal/stm32f4/displays/panels/lx154a2411.c",
    ]
    sources += [
        "embed/trezorhal/stm32f4/displays/panels/lx154a2422.c",
    ]

    features_available.append("backlight")

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/i2c.c"]
        sources += ["embed/trezorhal/stm32f4/touch/ft6x36.c"]
        sources += ["embed/lib/touch.c"]
        features_available.append("touch")

    if "sd_card" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/sdcard.c"]
        sources += ["embed/extmod/modtrezorio/ff.c"]
        sources += ["embed/extmod/modtrezorio/ffunicode.c"]
        sources += [
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c"
        ]
        sources += ["embed/trezorhal/stm32f4/dma.c"]
        features_available.append("sd_card")

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/sbu.c"]
        features_available.append("sbu")

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

    if "dma2d" in features_wanted:
        defines += ["USE_DMA2D"]
        sources += ["embed/trezorhal/stm32f4/dma2d.c"]
        sources += [
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma2d.c"
        ]
        features_available.append("dma2d")

    env.get("ENV")["TREZOR_BOARD"] = board
    env.get("ENV")["MCU_TYPE"] = mcu

    return features_available
