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
    board = "stm32f429i-disc1.h"
    display = "ltdc.c"
    hw_model = get_hw_model_as_number("D001")
    hw_revision = 0

    stm32f4_common_files(defines, sources, paths)

    env.get("ENV")['CPU_ASFLAGS'] = '-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16'
    env.get("ENV")['CPU_CCFLAGS'] = '-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16 -mtune=cortex-m4 '
    env.get("ENV")['RUST_TARGET'] = 'thumbv7em-none-eabihf'

    defines += ["STM32F429xx"]
    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [f"embed/trezorhal/stm32f4/displays/{display}"]
    sources += ["embed/trezorhal/stm32f4/displays/ili9341_spi.c"]
    sources += ["embed/trezorhal/stm32f4/sdram.c"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/i2c.c"]
        sources += ["embed/trezorhal/stm32f4/touch/stmpe811.c"]
        sources += ["embed/lib/touch.c"]
        features_available.append("touch")

    if "dma2d" in features_wanted:
        defines += ["USE_DMA2D"]
        sources += ["embed/lib/dma2d_emul.c"]
        features_available.append("dma2d")

    if "usb" in features_wanted:
        sources += [
            'embed/trezorhal/stm32f4/usb.c',
            'embed/trezorhal/stm32f4/usbd_conf.c',
            'embed/trezorhal/stm32f4/usbd_core.c',
            'embed/trezorhal/stm32f4/usbd_ctlreq.c',
            'embed/trezorhal/stm32f4/usbd_ioreq.c',
            'vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c',
        ]
        features_available.append("usb")

    env.get("ENV")["TREZOR_BOARD"] = board

    return features_available
