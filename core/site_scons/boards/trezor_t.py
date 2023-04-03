from . import get_hw_model_as_number


def configure(env, features_wanted, defines, sources):
    features_available = []
    board = 'trezor_t.h'
    display = 'st7789v.c'
    hw_model = get_hw_model_as_number('T2T1')
    hw_revision = 0
    features_available.append("disp_i8080_8bit_dw")

    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"', ]
    defines += [f'HW_MODEL={hw_model}', ]
    defines += [f'HW_REVISION={hw_revision}', ]
    sources += [f'embed/trezorhal/displays/{display}', ]

    if "input" in features_wanted:
        sources += ['embed/trezorhal/i2c.c', ]
        sources += ['embed/trezorhal/touch/touch.c', ]
        sources += ['embed/trezorhal/touch/ft6x36.c', ]
        features_available.append("touch")

    if "sd_card" in features_wanted:
        sources += ['embed/trezorhal/sdcard.c', ]
        sources += ['embed/extmod/modtrezorio/ff.c', ]
        sources += ['embed/extmod/modtrezorio/ffunicode.c', ]
        features_available.append("sd_card")

    if "sbu" in features_wanted:
        sources += ['embed/trezorhal/sbu.c', ]
        features_available.append("sbu")

    env.get('ENV')['TREZOR_BOARD'] = board

    return features_available
