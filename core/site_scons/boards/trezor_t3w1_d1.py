from . import get_hw_model_as_number


def configure(env, features_wanted, defines, sources):
    features_available = []
    board = 'trezor_t3w1_d1.h'
    display = 'st7789v.c'
    hw_model = get_hw_model_as_number('T3W1')
    hw_revision = 0
    features_available.append("disp_i8080_16bit_dw")

    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"', ]
    defines += [f'HW_MODEL={hw_model}', ]
    defines += [f'HW_REVISION={hw_revision}', ]
    sources += [f'embed/trezorhal/displays/{display}', ]
    sources += [f'embed/trezorhal/displays/panels/LHS200KB-IF21.c', ]

    if "input" in features_wanted:
        sources += ['embed/trezorhal/i2c.c', ]
        sources += ['embed/trezorhal/touch/touch.c', ]
        sources += ['embed/trezorhal/touch/ft6x36.c', ]
        features_available.append("touch")
        sources += ['embed/trezorhal/button.c']
        features_available.append("button")

    if "sd_card" in features_wanted:
        sources += ['embed/trezorhal/sdcard.c', ]
        sources += ['embed/extmod/modtrezorio/ff.c', ]
        sources += ['embed/extmod/modtrezorio/ffunicode.c', ]
        features_available.append("sd_card")

    if "ble" in features_wanted:
        sources += ['embed/trezorhal/ble/comm.c', ]
        sources += ['embed/trezorhal/ble/dfu.c', ]
        sources += ['embed/trezorhal/ble/fwu.c', ]
        sources += ['embed/trezorhal/ble/state.c', ]
        sources += ['embed/trezorhal/ble/messages.c', ]
        features_available.append("ble")

    if "sbu" in features_wanted:
        sources += ['embed/trezorhal/sbu.c', ]
        features_available.append("sbu")

    if "dma2d" in features_wanted:
        defines += ["USE_DMA2D", ]
        sources += ['embed/trezorhal/dma2d.c', ]
        sources += ['vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma2d.c', ]
        features_available.append("dma2d")

    env.get('ENV')['TREZOR_BOARD'] = board

    return features_available
