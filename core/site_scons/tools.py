def add_font(font_name, font, defines, sources):
    if font is not None:
        defines += [
            'TREZOR_FONT_' + font_name + '_ENABLE=' + font,
            'TREZOR_FONT_' + font_name + '_INCLUDE=\\"' + font.lower() + '.h\\"',
        ]
        sourcefile = 'embed/extmod/modtrezorui/fonts/' + font.lower() + '.c'
        if sourcefile not in sources:
            sources.append(sourcefile)


def get_hw_model_as_number(hw_model):
    return int.from_bytes(hw_model.encode(), 'little')



def configure_board(model, env, defines, sources):
    model_r_version = 4

    if model in ('1',):
        board = 'trezor_1.h'
        display = 'vg-2864ksweg01.c'
        hw_model = get_hw_model_as_number('T1B1')
        hw_revision = 0
    elif model in ('T',):
        board = 'trezor_t.h'
        display = 'st7789v.c'
        hw_model = get_hw_model_as_number('T2T1')
        hw_revision = 0
    elif model in ('R',):
        hw_model = get_hw_model_as_number('T2B1')
        hw_revision = model_r_version
        if model_r_version == 3:
            board = 'trezor_r_v3.h'
            display = "ug-2828tswig01.c"
        else:
            board = 'trezor_r_v4.h'
            display = 'vg-2864ksweg01.c'
    else:
        raise Exception("Unknown model")

    defines += [f'TREZOR_BOARD=\\"boards/{board}\\"', ]
    defines += [f'HW_MODEL={hw_model}', ]
    defines += [f'HW_REVISION={hw_revision}', ]
    sources += [f'embed/trezorhal/displays/{display}', ]
    env.get('ENV')['TREZOR_BOARD'] = board
