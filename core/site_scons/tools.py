
def add_font(font_name, font, defines, sources):
    if font is not None:
        defines += [
            'TREZOR_FONT_' + font_name + '_ENABLE=' + font,
            'TREZOR_FONT_' + font_name + '_INCLUDE=\\"' + font.lower() + '.h\\"',
            ]
        sourcefile = 'embed/extmod/modtrezorui/fonts/' + font.lower() + '.c'
        if sourcefile not in sources:
            sources.append(sourcefile)

