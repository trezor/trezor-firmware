from . import get_hw_model_as_number


def configure(env, features_wanted, defines, sources):
    features_available = []
    board = "stm32f429i-disc1.h"
    display = "ltdc.c"
    hw_model = get_hw_model_as_number("D001")
    hw_revision = 0

    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [f"embed/trezorhal/displays/{display}"]
    sources += ["embed/trezorhal/displays/ili9341_spi.c"]
    sources += ["embed/trezorhal/sdram.c"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/i2c.c"]
        sources += ["embed/trezorhal/touch/touch.c"]
        sources += ["embed/trezorhal/touch/stmpe811.c"]
        features_available.append("touch")

    if "dma2d" in features_wanted:
        defines += ["USE_DMA2D"]
        sources += ["embed/lib/dma2d_emul.c"]
        features_available.append("dma2d")

    env.get("ENV")["TREZOR_BOARD"] = board

    return features_available
