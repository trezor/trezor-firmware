/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/nlr.h"
#include "py/runtime.h"
#include "py/binary.h"

#if MICROPY_PY_TREZORUI

#define RESX 240
#define RESY 240

#if defined STM32_HAL_H
#include "modTrezorUi-stmhal.h"
#elif defined UNIX
#include "modTrezorUi-unix.h"
#else
#error Unsupported port. Only STMHAL and UNIX ports are supported.
#endif

#define SINF_WRITE DATA

#include "modTrezorUi-inflate.h"
#include "modTrezorUi-font_Roboto.h"
#include "modTrezorUi-font_RobotoMono.h"

// common functions

static void DATAS(void *bytes, int len) {
    const uint8_t *c = (const uint8_t *)bytes;
    while (len-- > 0) {
        DATA(*c);
        c++;
    }
}

static void display_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c) {
    display_set_window(x, y, w, h);
    int i;
    for (i = 0; i < w * h; i++) {
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
    sinf_inflate(data);
    display_update();
}

// first two bytes are width and height of the glyph
// third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// rest is packed 4-bit glyph data
static void display_text(uint8_t x, uint8_t y, uint8_t *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor) {
    int i, j, xx = x;
    const uint8_t *g;
    uint8_t c, cr, cg, cb;
    uint16_t ct[16];
    // precompute color table
    for (i = 0; i < 16; i++) {
        cr = (((fgcolor & 0xF800) >> 11) * i + ((bgcolor & 0xF800) >> 11) * (15 - i)) / 15;
        cg = (((fgcolor & 0x07E0) >> 5) * i + ((bgcolor & 0x07E0) >> 5) * (15 - i)) / 15;
        cb = ((fgcolor & 0x001F) * i + (bgcolor & 0x001F) * (15 - i)) / 15;
        ct[i] = (cr << 11) | (cg << 5) | cb;
    }
    // render glyphs
    for (i = 0; i < textlen; i++) {
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
                g = Font_Roboto_Regular_18[c - ' '];
                break;
            case 1:
                g = Font_RobotoMono_Regular_18[c - ' '];
                break;
            default:
                return; // unknown font -> abort
        }
        // g[0], g[1] = width, height
        // g[2]       = advance
        // g[3], g[4] = bearingX, bearingY
        if (g[0] && g[1]) {
            display_set_window(xx + g[3], y - g[4], g[0], g[1]);
            for (j = 0; j < g[0] * g[1]; j++) {
                if (j % 2 == 0) {
                    c = g[5 + j/2] >> 4;
                } else {
                    c = g[5 + j/2] & 0x0F;
                }
                DATA(ct[c] >> 8);
                DATA(ct[c] & 0xFF);
            }
            display_update();
        }
        xx += g[2];
    }
}

// uPy wrappers

// class Display(object):
typedef struct _mp_obj_Display_t {
    mp_obj_base_t base;
} mp_obj_Display_t;

// def Display.__init__(self):
STATIC mp_obj_t mod_TrezorUi_Display_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    display_init();
    mp_obj_Display_t *o = m_new_obj(mp_obj_Display_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Display.bar(self, x: int, y: int, w: int, h: int, color: int) -> None:
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
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_bar_obj, 6, 6, mod_TrezorUi_Display_bar);

// def Display.blit(self, x: int, y: int, w: int, h: int, data: bytes) -> None:
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
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_blit_obj, 6, 6, mod_TrezorUi_Display_blit);

// def Display.image(self, x: int, y: int, image: bytes) -> None:
STATIC mp_obj_t mod_TrezorUi_Display_image(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[3], &bufinfo, MP_BUFFER_READ);
    uint8_t *data = bufinfo.buf;
    if (bufinfo.len < 8 || memcmp(data, "TOIa", 4) != 0) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid image format"));
    }
    mp_int_t w = (data[4] << 8) | data[5];
    mp_int_t h = (data[6] << 8) | data[7];
    if ((x < 0) || (y < 0) || (x + w > RESX) || (y + h > RESY)) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Out of bounds"));
    }
    display_image(x, y, w, h, data + 8, bufinfo.len - 8);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_image_obj, 4, 4, mod_TrezorUi_Display_image);

// def Display.text(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None:
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
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_text_obj, 7, 7, mod_TrezorUi_Display_text);

STATIC const mp_rom_map_elem_t mod_TrezorUi_Display_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_bar), MP_ROM_PTR(&mod_TrezorUi_Display_bar_obj) },
    { MP_ROM_QSTR(MP_QSTR_blit), MP_ROM_PTR(&mod_TrezorUi_Display_blit_obj) },
    { MP_ROM_QSTR(MP_QSTR_image), MP_ROM_PTR(&mod_TrezorUi_Display_image_obj) },
    { MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&mod_TrezorUi_Display_text_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorUi_Display_locals_dict, mod_TrezorUi_Display_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorUi_Display_type = {
    { &mp_type_type },
    .name = MP_QSTR_Display,
    .make_new = mod_TrezorUi_Display_make_new,
    .locals_dict = (void*)&mod_TrezorUi_Display_locals_dict,
};

STATIC const mp_rom_map_elem_t mp_module_TrezorUi_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorUi) },
    { MP_ROM_QSTR(MP_QSTR_Display), MP_ROM_PTR(&mod_TrezorUi_Display_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorUi_globals, mp_module_TrezorUi_globals_table);

const mp_obj_module_t mp_module_TrezorUi = {
    .base = { &mp_type_module },
    .name = MP_QSTR_TrezorUi,
    .globals = (mp_obj_dict_t*)&mp_module_TrezorUi_globals,
};


#endif // MICROPY_PY_TREZORUI
