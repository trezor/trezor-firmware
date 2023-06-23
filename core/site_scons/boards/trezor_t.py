from __future__ import annotations

from . import get_hw_model_as_number


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
) -> list[str]:
    features_available: list[str] = []
    board = "trezor_t.h"
    display = "st7789v.c"
    hw_model = get_hw_model_as_number("T2T1")
    hw_revision = 0
    features_available.append("disp_i8080_8bit_dw")

    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [f"embed/trezorhal/displays/{display}"]
    sources += [f"embed/trezorhal/backlight_pwm.c"]
    sources += [f'embed/trezorhal/displays/panels/tf15411a.c', ]
    sources += [f'embed/trezorhal/displays/panels/154a.c', ]
    sources += [f'embed/trezorhal/displays/panels/lx154a2411.c', ]
    sources += [f'embed/trezorhal/displays/panels/lx154a2422.c', ]

    features_available.append("backlight")

    if "input" in features_wanted:
        sources += ["embed/trezorhal/i2c.c"]
        sources += ["embed/trezorhal/touch/touch.c"]
        sources += ["embed/trezorhal/touch/ft6x36.c"]
        features_available.append("touch")

    if "sd_card" in features_wanted:
        sources += ["embed/trezorhal/sdcard.c"]
        sources += ["embed/extmod/modtrezorio/ff.c"]
        sources += ["embed/extmod/modtrezorio/ffunicode.c"]
        features_available.append("sd_card")

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/sbu.c"]
        features_available.append("sbu")

    if "dma2d" in features_wanted:
        defines += ["USE_DMA2D"]
        sources += ["embed/trezorhal/dma2d.c"]
        sources += [
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma2d.c"
        ]
        features_available.append("dma2d")

    env.get("ENV")["TREZOR_BOARD"] = board

    return features_available
