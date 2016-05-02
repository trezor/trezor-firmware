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

static void inflate_callback_image(uint8_t byte, uint32_t pos, void *userdata)
{
    DATA(byte);
}

static void display_image(uint8_t x, uint8_t y, uint8_t w, uint8_t h, void *data, int datalen) {
    display_set_window(x, y, w, h);
    sinf_inflate(data, inflate_callback_image, NULL);
    display_update();
}

static void set_color_table(uint16_t colortable[16], uint16_t fgcolor, uint16_t bgcolor)
{
    uint8_t cr, cg, cb;
    for (int i = 0; i < 16; i++) {
        cr = (((fgcolor & 0xF800) >> 11) * i + ((bgcolor & 0xF800) >> 11) * (15 - i)) / 15;
        cg = (((fgcolor & 0x07E0) >> 5) * i + ((bgcolor & 0x07E0) >> 5) * (15 - i)) / 15;
        cb = ((fgcolor & 0x001F) * i + (bgcolor & 0x001F) * (15 - i)) / 15;
        colortable[i] = (cr << 11) | (cg << 5) | cb;
    }
}

static void inflate_callback_icon(uint8_t byte, uint32_t pos, void *userdata)
{
    uint16_t *colortable = (uint16_t *)userdata;
    DATA(colortable[byte >> 4] >> 8);
    DATA(colortable[byte >> 4] & 0xFF);
    DATA(colortable[byte & 0x0F] >> 8);
    DATA(colortable[byte & 0x0F] & 0xFF);
}

static void display_icon(uint8_t x, uint8_t y, uint8_t w, uint8_t h, void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor) {
    display_set_window(x, y, w, h);
    uint16_t colortable[16];
    set_color_table(colortable, fgcolor, bgcolor);
    sinf_inflate(data, inflate_callback_icon, colortable);
    display_update();
}

static const uint8_t *get_glyph(uint8_t font, uint8_t c) {
    if (c >= ' ' && c <= '~') {
    // do nothing - valid ASCII
    } else
    // UTF-8 handling: https://en.wikipedia.org/wiki/UTF-8#Description
    if (c >= 0xC0) {
        // bytes 11xxxxxx are first byte of UTF-8 characters
        c = '_';
    } else {
        // bytes 10xxxxxx are successive UTF-8 characters
        return 0;
    }
    switch (font) {
        case 0:
            return Font_RobotoMono_Regular_20[c - ' '];
        case 1:
            return Font_Roboto_Regular_20[c - ' '];
        case 2:
            return Font_Roboto_Bold_20[c - ' '];
    }
    return 0;
}

// first two bytes are width and height of the glyph
// third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// rest is packed 4-bit glyph data
static void display_text(uint8_t x, uint8_t y, uint8_t *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor) {
    uint32_t px = x;
    uint16_t colortable[16];
    set_color_table(colortable, fgcolor, bgcolor);

    // render glyphs
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, text[i]);
        if (!g) continue;
        // g[0], g[1] = width, height
        // g[2]       = advance
        // g[3], g[4] = bearingX, bearingY
        if (g[0] && g[1]) {
            display_set_window(px + (int8_t)(g[3]), y - (int8_t)(g[4]), g[0], g[1]);
            for (int j = 0; j < g[0] * g[1]; j++) {
                uint8_t c;
                if (j % 2 == 0) {
                    c = g[5 + j/2] >> 4;
                } else {
                    c = g[5 + j/2] & 0x0F;
                }
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            }
            display_update();
        }
        px += g[2];
    }
}

// compute the width of the text (in pixels)
static uint32_t display_text_width(uint8_t *text, int textlen, uint8_t font) {
    uint32_t w = 0;
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, text[i]);
        if (!g) continue;
        w += g[2];
    }
    return w;
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

#include "modtrezorui-loader.h"

static void display_loader(uint16_t progress, uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon, uint16_t iconfgcolor)
{
    uint16_t colortable[16], iconcolortable[16];
    set_color_table(colortable, fgcolor, bgcolor);
    if (icon) {
        set_color_table(iconcolortable, iconfgcolor, bgcolor);
    }
    display_set_window(RESX / 2 - img_loader_size, RESY * 2 / 5 - img_loader_size, img_loader_size * 2, img_loader_size * 2);
    for (int y = 0; y < img_loader_size * 2; y++) {
        for (int x = 0; x < img_loader_size * 2; x++) {
            int mx = x, my = y;
            uint16_t a;
            if ((mx >= img_loader_size) && (my >= img_loader_size)) {
                mx = img_loader_size * 2 - 1 - x;
                my = img_loader_size * 2 - 1 - y;
                a = 499 - (img_loader[my][mx] >> 8);
            } else
            if (mx >= img_loader_size) {
                mx = img_loader_size * 2 - 1 - x;
                a = img_loader[my][mx] >> 8;
            } else
            if (my >= img_loader_size) {
                my = img_loader_size * 2 - 1 - y;
                a = 500 + (img_loader[my][mx] >> 8);
            } else {
                a = 999 - (img_loader[my][mx] >> 8);
            }
            // inside of circle - draw glyph
            if (icon && mx + my > (48 * 2) && mx >= img_loader_size - 48 && my >= img_loader_size - 48) {
                int i = (x - (img_loader_size - 48)) + (y - (img_loader_size - 48)) * 96;
                uint8_t c;
                if (i % 2) {
                    c = icon[i / 2] & 0x0F;
                } else {
                    c = (icon[i / 2] & 0xF0) >> 4;
                }
                DATA(iconcolortable[c] >> 8);
                DATA(iconcolortable[c] & 0xFF);
            } else {
                uint8_t c;
                if (progress > a) {
                    c = (img_loader[my][mx] & 0x00F0) >> 4;
                } else {
                    c = img_loader[my][mx] & 0x000F;
                }
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
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

// def Display.text_center(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_text_center(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[3], &bufinfo, MP_BUFFER_READ);
    mp_int_t font = mp_obj_get_int(args[4]);
    mp_int_t fgcolor = mp_obj_get_int(args[5]);
    mp_int_t bgcolor = mp_obj_get_int(args[6]);
    uint32_t w = display_text_width(bufinfo.buf, bufinfo.len, font);
    display_text(x - w / 2, y, bufinfo.buf, bufinfo.len, font, fgcolor, bgcolor);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_text_center_obj, 7, 7, mod_TrezorUi_Display_text_center);

// def Display.text_right(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
STATIC mp_obj_t mod_TrezorUi_Display_text_right(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[3], &bufinfo, MP_BUFFER_READ);
    mp_int_t font = mp_obj_get_int(args[4]);
    mp_int_t fgcolor = mp_obj_get_int(args[5]);
    mp_int_t bgcolor = mp_obj_get_int(args[6]);
    uint32_t w = display_text_width(bufinfo.buf, bufinfo.len, font);
    display_text(x - w, y, bufinfo.buf, bufinfo.len, font, fgcolor, bgcolor);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_text_right_obj, 7, 7, mod_TrezorUi_Display_text_right);

// def Display.text_width(self, text: bytes, font: int) -> int
STATIC mp_obj_t mod_TrezorUi_Display_text_width(mp_obj_t self, mp_obj_t text, mp_obj_t font) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(text, &bufinfo, MP_BUFFER_READ);
    mp_int_t f = mp_obj_get_int(font);
    uint32_t w = display_text_width(bufinfo.buf, bufinfo.len, f);
    return MP_OBJ_NEW_SMALL_INT(w);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorUi_Display_text_width_obj, mod_TrezorUi_Display_text_width);

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


static void inflate_callback_loader(uint8_t byte, uint32_t pos, void *userdata)
{
    uint8_t *out = (uint8_t *)userdata;
    out[pos] = byte;
}

// def Display.loader(self, progress: int, fgcolor: int, bgcolor: int, icon: bytes=None, iconfgcolor: int=None) -> None
STATIC mp_obj_t mod_TrezorUi_Display_loader(size_t n_args, const mp_obj_t *args) {
    mp_int_t progress = mp_obj_get_int(args[1]);
    mp_int_t fgcolor = mp_obj_get_int(args[2]);
    mp_int_t bgcolor = mp_obj_get_int(args[3]);
    if (n_args > 4) { // icon provided
        mp_buffer_info_t bufinfo;
        mp_get_buffer_raise(args[4], &bufinfo, MP_BUFFER_READ);
        uint8_t *data = bufinfo.buf;
        if (bufinfo.len < 8 || memcmp(data, "TOIg", 4) != 0) {
            nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid image format"));
        }
        mp_int_t w = *(uint16_t *)(data + 4);
        mp_int_t h = *(uint16_t *)(data + 6);
        mp_int_t datalen = *(uint32_t *)(data + 8);
        if (w != 96 || h != 96) {
            nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid icon size"));
        }
        if (datalen != bufinfo.len - 12) {
            nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid size of data"));
        }
        uint8_t icondata[96 * 96 /2];
        sinf_inflate(data + 12, inflate_callback_loader, icondata);
        uint16_t iconfgcolor;
        if (n_args > 5) { // icon color provided
            iconfgcolor = mp_obj_get_int(args[5]);
        } else {
            iconfgcolor = ~bgcolor; // invert
        }
        display_loader(progress, fgcolor, bgcolor, icondata, iconfgcolor);
    } else {
        display_loader(progress, fgcolor, bgcolor, NULL, 0);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_TrezorUi_Display_loader_obj, 4, 6, mod_TrezorUi_Display_loader);

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
    { MP_ROM_QSTR(MP_QSTR_text_center), MP_ROM_PTR(&mod_TrezorUi_Display_text_center_obj) },
    { MP_ROM_QSTR(MP_QSTR_text_right), MP_ROM_PTR(&mod_TrezorUi_Display_text_right_obj) },
    { MP_ROM_QSTR(MP_QSTR_text_width), MP_ROM_PTR(&mod_TrezorUi_Display_text_width_obj) },
    { MP_ROM_QSTR(MP_QSTR_qrcode), MP_ROM_PTR(&mod_TrezorUi_Display_qrcode_obj) },
    { MP_ROM_QSTR(MP_QSTR_loader), MP_ROM_PTR(&mod_TrezorUi_Display_loader_obj) },
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
