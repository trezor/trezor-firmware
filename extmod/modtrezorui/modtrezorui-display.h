/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "modtrezorui-inflate.h"
#include "modtrezorui-font_robotomono_regular.h"
#include "modtrezorui-font_roboto_regular.h"
#include "modtrezorui-font_roboto_bold.h"

#include "trezor-qrenc/qr_encode.h"

// common display functions

static void DATAS(void *bytes, int len) {
    const uint8_t *c = (const uint8_t *)bytes;
    while (len-- > 0) {
        DATA(*c);
        c++;
    }
}

static void display_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c) {
    display_set_window(x, y, w, h);
    for (int i = 0; i < w * h; i++) {
        DATA(c >> 8);
        DATA(c & 0xFF);
    }
    display_update();
}

static void display_blit(uint8_t x, uint8_t y, uint8_t w, uint8_t h, void *data, int datalen) {
    display_set_window(x, y, w, h);
    DATAS(data, datalen);
    display_update();
}

static void display_image(uint8_t x, uint8_t y, uint8_t w, uint8_t h, void *data, int datalen) {
    display_set_window(x, y, w, h);
    sinf_inflate(data, DATAfunc);
    display_update();
}

static uint16_t COLORTABLE[16];

static void set_color_table(uint16_t fgcolor, uint16_t bgcolor)
{
    uint8_t cr, cg, cb;
    for (int i = 0; i < 16; i++) {
        cr = (((fgcolor & 0xF800) >> 11) * i + ((bgcolor & 0xF800) >> 11) * (15 - i)) / 15;
        cg = (((fgcolor & 0x07E0) >> 5) * i + ((bgcolor & 0x07E0) >> 5) * (15 - i)) / 15;
        cb = ((fgcolor & 0x001F) * i + (bgcolor & 0x001F) * (15 - i)) / 15;
        COLORTABLE[i] = (cr << 11) | (cg << 5) | cb;
    }
}

static void DATAiconmap(uint8_t byte)
{
    DATA(COLORTABLE[byte >> 4] >> 8);
    DATA(COLORTABLE[byte >> 4] & 0xFF);
    DATA(COLORTABLE[byte & 0x0F] >> 8);
    DATA(COLORTABLE[byte & 0x0F] & 0xFF);
}

static void display_icon(uint8_t x, uint8_t y, uint8_t w, uint8_t h, void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor) {
    display_set_window(x, y, w, h);
    set_color_table(fgcolor, bgcolor);
    sinf_inflate(data, DATAiconmap);
    display_update();
}

// first two bytes are width and height of the glyph
// third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// rest is packed 4-bit glyph data
static void display_text(uint8_t x, uint8_t y, uint8_t *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor) {
    int xx = x;
    const uint8_t *g;
    uint8_t c;
    set_color_table(fgcolor, bgcolor);

    // render glyphs
    for (int i = 0; i < textlen; i++) {
        if (text[i] >= ' ' && text[i] <= '~') {
            c = text[i];
        } else
        // UTF-8 handling: https://en.wikipedia.org/wiki/UTF-8#Description
        if (text[i] >= 0xC0) {
            // bytes 11xxxxxx are first byte of UTF-8 characters
            c = '_';
        } else {
            // bytes 10xxxxxx are successive UTF-8 characters
            continue;
        }
        switch (font) {
            case 0:
                g = Font_RobotoMono_Regular_20[c - ' '];
                break;
            case 1:
                g = Font_Roboto_Regular_20[c - ' '];
                break;
            case 2:
                g = Font_Roboto_Bold_20[c - ' '];
                break;
            default:
                return; // unknown font -> abort
        }
        // g[0], g[1] = width, height
        // g[2]       = advance
        // g[3], g[4] = bearingX, bearingY
        if (g[0] && g[1]) {
            display_set_window(xx + (int8_t)(g[3]), y - (int8_t)(g[4]), g[0], g[1]);
            for (int j = 0; j < g[0] * g[1]; j++) {
                if (j % 2 == 0) {
                    c = g[5 + j/2] >> 4;
                } else {
                    c = g[5 + j/2] & 0x0F;
                }
                DATA(COLORTABLE[c] >> 8);
                DATA(COLORTABLE[c] & 0xFF);
            }
            display_update();
        }
        xx += g[2];
    }
}

static void display_qrcode(uint8_t x, uint8_t y, char *data, int datalen, int scale) {
    uint8_t bitdata[QR_MAX_BITDATA];
    int side = qr_encode(QR_LEVEL_M, 0, data, datalen, bitdata);
    display_set_window(x, y, side * scale, side * scale);
    for (int i = 0; i < side * scale; i++) {
        for (int j = 0; j < side; j++) {
            int a = j * side + (i / scale);
            if (bitdata[a / 8] & (1 << (7 - a % 8))) {
                for (a = 0; a < scale * 2; a++) { DATA(0x00); }
            } else {
                for (a = 0; a < scale * 2; a++) { DATA(0xFF); }
            }
        }
    }
    display_update();
}

static void display_raw(uint8_t reg, uint8_t *data, int datalen)
{
    if (reg) {
        CMD(reg);
    }
    DATAS(data, datalen);
}

// class Display(object):
typedef struct _mp_obj_Display_t {
    mp_obj_base_t base;
} mp_obj_Display_t;

// def Display.__init__(self)
STATIC mp_obj_t mod_TrezorUi_Display_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    display_init();
    mp_obj_Display_t *o = m_new_obj(mp_obj_Display_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Display.bar(self, x: int, y: int, w: int, h: int, color: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_bar(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_int_t w = mp_obj_get_int(args[3]);
    mp_int_t h = mp_obj_get_int(args[4]);
    uint16_t c = mp_obj_get_int(args[5]);
    if ((x < 0) || (y < 0) || (x + w > RESX) || (y + h > RESY)) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Out of bounds"));
    }
    display_bar(x, y, w, h, c);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_bar_obj, 6, 6, mod_TrezorUi_Display_bar);

// def Display.blit(self, x: int, y: int, w: int, h: int, data: bytes) -> None
STATIC mp_obj_t mod_TrezorUi_Display_blit(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_int_t w = mp_obj_get_int(args[3]);
    mp_int_t h = mp_obj_get_int(args[4]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[5], &bufinfo, MP_BUFFER_READ);
    if (bufinfo.len != 2 * w * h) {
        nlr_raise(mp_obj_new_exception_msg_varg(&mp_type_ValueError, "Wrong data size (got %d bytes, expected %d bytes)", bufinfo.len, 2 * w * h));
    }
    display_blit(x, y, w, h, bufinfo.buf, bufinfo.len);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_blit_obj, 6, 6, mod_TrezorUi_Display_blit);

// def Display.image(self, x: int, y: int, image: bytes) -> None
STATIC mp_obj_t mod_TrezorUi_Display_image(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[3], &bufinfo, MP_BUFFER_READ);
    uint8_t *data = bufinfo.buf;
    if (bufinfo.len < 8 || memcmp(data, "TOIf", 4) != 0) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid image format"));
    }
    mp_int_t w = *(uint16_t *)(data + 4);
    mp_int_t h = *(uint16_t *)(data + 6);
    mp_int_t datalen = *(uint32_t *)(data + 8);
    if ((x < 0) || (y < 0) || (x + w > RESX) || (y + h > RESY)) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Out of bounds"));
    }
    if (datalen != bufinfo.len - 12) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid size of data"));
    }
    display_image(x, y, w, h, data + 12, bufinfo.len - 12);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_image_obj, 4, 4, mod_TrezorUi_Display_image);

// def Display.icon(self, x: int, y: int, icon: bytes, fgcolor: int, bgcolor: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_icon(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[3], &bufinfo, MP_BUFFER_READ);
    uint8_t *data = bufinfo.buf;
    if (bufinfo.len < 8 || memcmp(data, "TOIg", 4) != 0) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid image format"));
    }
    mp_int_t w = *(uint16_t *)(data + 4);
    mp_int_t h = *(uint16_t *)(data + 6);
    mp_int_t datalen = *(uint32_t *)(data + 8);
    if ((x < 0) || (y < 0) || (x + w > RESX) || (y + h > RESY)) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Out of bounds"));
    }
    if (datalen != bufinfo.len - 12) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid size of data"));
    }
    mp_int_t fgcolor = mp_obj_get_int(args[4]);
    mp_int_t bgcolor = mp_obj_get_int(args[5]);
    display_icon(x, y, w, h, data + 12, bufinfo.len - 12, fgcolor, bgcolor);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_icon_obj, 6, 6, mod_TrezorUi_Display_icon);

// def Display.text(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_text(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[3], &bufinfo, MP_BUFFER_READ);
    mp_int_t font = mp_obj_get_int(args[4]);
    mp_int_t fgcolor = mp_obj_get_int(args[5]);
    mp_int_t bgcolor = mp_obj_get_int(args[6]);
    display_text(x, y, bufinfo.buf, bufinfo.len, font, fgcolor, bgcolor);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_text_obj, 7, 7, mod_TrezorUi_Display_text);

// def Display.qrcode(self, x: int, y: int, data: bytes, scale: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_qrcode(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_int_t scale = mp_obj_get_int(args[4]);
    if (scale < 1 || scale > 10) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Scale has to be between 1 and 10"));
    }
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[3], &bufinfo, MP_BUFFER_READ);
    display_qrcode(x, y, bufinfo.buf, bufinfo.len, scale);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_qrcode_obj, 5, 5, mod_TrezorUi_Display_qrcode);

// def Display.orientation(self, degrees: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_orientation(mp_obj_t self, mp_obj_t degrees) {
    mp_int_t deg = mp_obj_get_int(degrees);
    if (deg != 0 && deg != 90 && deg != 180 && deg != 270) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Value must be 0, 90, 180 or 270"));
    }
    display_orientation(deg);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorUi_Display_orientation_obj, mod_TrezorUi_Display_orientation);

// def Display.raw(self, reg: int, data: bytes) -> None
STATIC mp_obj_t mod_TrezorUi_Display_raw(mp_obj_t self, mp_obj_t reg, mp_obj_t data) {
    mp_int_t r = mp_obj_get_int(reg);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data, &bufinfo, MP_BUFFER_READ);
    display_raw(r, bufinfo.buf, bufinfo.len);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorUi_Display_raw_obj, mod_TrezorUi_Display_raw);

// def Display.backlight(self, val: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_backlight(mp_obj_t self, mp_obj_t reg) {
    display_backlight(mp_obj_get_int(reg));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorUi_Display_backlight_obj, mod_TrezorUi_Display_backlight);

// Display stuff

STATIC const mp_rom_map_elem_t mod_TrezorUi_Display_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_bar), MP_ROM_PTR(&mod_TrezorUi_Display_bar_obj) },
    { MP_ROM_QSTR(MP_QSTR_blit), MP_ROM_PTR(&mod_TrezorUi_Display_blit_obj) },
    { MP_ROM_QSTR(MP_QSTR_image), MP_ROM_PTR(&mod_TrezorUi_Display_image_obj) },
    { MP_ROM_QSTR(MP_QSTR_icon), MP_ROM_PTR(&mod_TrezorUi_Display_icon_obj) },
    { MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&mod_TrezorUi_Display_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_qrcode), MP_ROM_PTR(&mod_TrezorUi_Display_qrcode_obj) },
    { MP_ROM_QSTR(MP_QSTR_orientation), MP_ROM_PTR(&mod_TrezorUi_Display_orientation_obj) },
    { MP_ROM_QSTR(MP_QSTR_raw), MP_ROM_PTR(&mod_TrezorUi_Display_raw_obj) },
    { MP_ROM_QSTR(MP_QSTR_backlight), MP_ROM_PTR(&mod_TrezorUi_Display_backlight_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorUi_Display_locals_dict, mod_TrezorUi_Display_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorUi_Display_type = {
    { &mp_type_type },
    .name = MP_QSTR_Display,
    .make_new = mod_TrezorUi_Display_make_new,
    .locals_dict = (void*)&mod_TrezorUi_Display_locals_dict,
};
