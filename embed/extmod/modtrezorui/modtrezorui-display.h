/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "inflate.h"

#include "display.h"

#define FONT_PY_TO_C(f) (-(f))
#define FONT_C_TO_PY(f) (-(f))

/// class Display:
///     '''
///     Provide access to device display.
///     '''
typedef struct _mp_obj_Display_t {
    mp_obj_base_t base;
} mp_obj_Display_t;

/// def __init__(self) -> None:
///     '''
///     Initialize the display.
///     '''
STATIC mp_obj_t mod_trezorui_Display_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Display_t *o = m_new_obj(mp_obj_Display_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def clear(self) -> None:
///     '''
///     Clear display with black color.
///     '''
STATIC mp_obj_t mod_trezorui_Display_clear(mp_obj_t self) {
    display_clear();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui_Display_clear_obj, mod_trezorui_Display_clear);

/// def refresh(self) -> None:
///     '''
///     Refresh display (update screen).
///     '''
STATIC mp_obj_t mod_trezorui_Display_refresh(mp_obj_t self) {
    display_refresh();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui_Display_refresh_obj, mod_trezorui_Display_refresh);

/// def bar(self, x: int, y: int, w: int, h: int, color: int) -> None:
///     '''
///     Renders a bar at position (x,y = upper left corner) with width w and height h of color color.
///     '''
STATIC mp_obj_t mod_trezorui_Display_bar(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_int_t w = mp_obj_get_int(args[3]);
    mp_int_t h = mp_obj_get_int(args[4]);
    uint16_t c = mp_obj_get_int(args[5]);
    display_bar(x, y, w, h, c);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_bar_obj, 6, 6, mod_trezorui_Display_bar);

/// def bar_radius(self, x: int, y: int, w: int, h: int, fgcolor: int, bgcolor: int = None, radius: int = None) -> None:
///     '''
///     Renders a rounded bar at position (x,y = upper left corner) with width w and height h of color fgcolor.
///     Background is set to bgcolor and corners are drawn with radius radius.
///     '''
STATIC mp_obj_t mod_trezorui_Display_bar_radius(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_int_t w = mp_obj_get_int(args[3]);
    mp_int_t h = mp_obj_get_int(args[4]);
    uint16_t c = mp_obj_get_int(args[5]);
    uint16_t b = mp_obj_get_int(args[6]);
    uint8_t r = mp_obj_get_int(args[7]);
    display_bar_radius(x, y, w, h, c, b, r);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_bar_radius_obj, 8, 8, mod_trezorui_Display_bar_radius);

/// def image(self, x: int, y: int, image: bytes) -> None:
///     '''
///     Renders an image at position (x,y).
///     The image needs to be in TREZOR Optimized Image Format (TOIF) - full-color mode.
///     '''
STATIC mp_obj_t mod_trezorui_Display_image(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t image;
    mp_get_buffer_raise(args[3], &image, MP_BUFFER_READ);
    const uint8_t *data = image.buf;
    if (image.len < 8 || memcmp(data, "TOIf", 4) != 0) {
        mp_raise_ValueError("Invalid image format");
    }
    mp_int_t w = *(uint16_t *)(data + 4);
    mp_int_t h = *(uint16_t *)(data + 6);
    mp_int_t datalen = *(uint32_t *)(data + 8);
    if (datalen != image.len - 12) {
        mp_raise_ValueError("Invalid size of data");
    }
    display_image(x, y, w, h, data + 12, datalen);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_image_obj, 4, 4, mod_trezorui_Display_image);

/// def avatar(self, x: int, y: int, image: bytes, fgcolor: int, bgcolor: int) -> None:
///     '''
///     Renders an avatar at position (x,y).
///     The image needs to be in TREZOR Optimized Image Format (TOIF) - full-color mode.
///     Image needs to be of exactly AVATAR_IMAGE_SIZE x AVATAR_IMAGE_SIZE pixels size.
///     '''
STATIC mp_obj_t mod_trezorui_Display_avatar(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t image;
    mp_get_buffer_raise(args[3], &image, MP_BUFFER_READ);
    const uint8_t *data = image.buf;
    if (image.len < 8 || memcmp(data, "TOIf", 4) != 0) {
        mp_raise_ValueError("Invalid image format");
    }
    mp_int_t w = *(uint16_t *)(data + 4);
    mp_int_t h = *(uint16_t *)(data + 6);
    if (w != AVATAR_IMAGE_SIZE || h != AVATAR_IMAGE_SIZE) {
        mp_raise_ValueError("Invalid image size");
    }
    mp_int_t datalen = *(uint32_t *)(data + 8);
    if (datalen != image.len - 12) {
        mp_raise_ValueError("Invalid size of data");
    }
    mp_int_t fgcolor = mp_obj_get_int(args[4]);
    mp_int_t bgcolor = mp_obj_get_int(args[5]);
    display_avatar(x, y, data + 12, datalen, fgcolor, bgcolor);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_avatar_obj, 6, 6, mod_trezorui_Display_avatar);

/// def icon(self, x: int, y: int, icon: bytes, fgcolor: int, bgcolor: int) -> None:
///     '''
///     Renders an icon at position (x,y), fgcolor is used as foreground color, bgcolor as background.
///     The icon needs to be in TREZOR Optimized Image Format (TOIF) - gray-scale mode.
///     '''
STATIC mp_obj_t mod_trezorui_Display_icon(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t icon;
    mp_get_buffer_raise(args[3], &icon, MP_BUFFER_READ);
    const uint8_t *data = icon.buf;
    if (icon.len < 8 || memcmp(data, "TOIg", 4) != 0) {
        mp_raise_ValueError("Invalid image format");
    }
    mp_int_t w = *(uint16_t *)(data + 4);
    mp_int_t h = *(uint16_t *)(data + 6);
    mp_int_t datalen = *(uint32_t *)(data + 8);
    if (datalen != icon.len - 12) {
        mp_raise_ValueError("Invalid size of data");
    }
    mp_int_t fgcolor = mp_obj_get_int(args[4]);
    mp_int_t bgcolor = mp_obj_get_int(args[5]);
    display_icon(x, y, w, h, data + 12, icon.len - 12, fgcolor, bgcolor);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_icon_obj, 6, 6, mod_trezorui_Display_icon);

/// def print(self, text: str) -> None:
///     '''
///     Renders text using 5x8 bitmap font (using special text mode).
///     '''
STATIC mp_obj_t mod_trezorui_Display_print(mp_obj_t self, mp_obj_t text) {
    mp_buffer_info_t buf;
    mp_get_buffer_raise(text, &buf, MP_BUFFER_READ);
    if (buf.len > 0) {
        display_print(buf.buf, buf.len);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorui_Display_print_obj, mod_trezorui_Display_print);

/// def text(self, x: int, y: int, text: str, font: int, fgcolor: int, bgcolor: int, minwidth: int=None) -> int:
///     '''
///     Renders left-aligned text at position (x,y) where x is left position and y is baseline.
///     Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
///     Fills at least minwidth pixels with bgcolor.
///     Returns width of rendered text in pixels.
///     '''
STATIC mp_obj_t mod_trezorui_Display_text(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t text;
    mp_get_buffer_raise(args[3], &text, MP_BUFFER_READ);
    mp_int_t font = FONT_PY_TO_C(mp_obj_get_int(args[4]));
    mp_int_t fgcolor = mp_obj_get_int(args[5]);
    mp_int_t bgcolor = mp_obj_get_int(args[6]);
    mp_int_t minwidth = (n_args > 7) ? mp_obj_get_int(args[7]) : 0;
    // prefill start
    int w = display_text_width(text.buf, text.len, font);
    int barwidth = MAX(w, minwidth);
    display_bar(x, y - 18, barwidth, 23, bgcolor);
    // prefill end
    display_text(x, y, text.buf, text.len, font, fgcolor, bgcolor);
    return mp_obj_new_int(w);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_text_obj, 7, 8, mod_trezorui_Display_text);

/// def text_center(self, x: int, y: int, text: str, font: int, fgcolor: int, bgcolor: int, minwidth: int=None) -> int:
///     '''
///     Renders text centered at position (x,y) where x is text center and y is baseline.
///     Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
///     Fills at least minwidth pixels with bgcolor.
///     Returns width of rendered text in pixels.
///     '''
STATIC mp_obj_t mod_trezorui_Display_text_center(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t text;
    mp_get_buffer_raise(args[3], &text, MP_BUFFER_READ);
    mp_int_t font = FONT_PY_TO_C(mp_obj_get_int(args[4]));
    mp_int_t fgcolor = mp_obj_get_int(args[5]);
    mp_int_t bgcolor = mp_obj_get_int(args[6]);
    mp_int_t minwidth = (n_args > 7) ? mp_obj_get_int(args[7]) : 0;
    // prefill start
    int w = display_text_width(text.buf, text.len, font);
    int barwidth = MAX(w, minwidth);
    display_bar(x - barwidth / 2, y - 18, barwidth, 23, bgcolor);
    // prefill end
    display_text_center(x, y, text.buf, text.len, font, fgcolor, bgcolor);
    return mp_obj_new_int(w);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_text_center_obj, 7, 8, mod_trezorui_Display_text_center);

/// def text_right(self, x: int, y: int, text: str, font: int, fgcolor: int, bgcolor: int, minwidth: int=None) -> int:
///     '''
///     Renders right-aligned text at position (x,y) where x is right position and y is baseline.
///     Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.
///     Fills at least minwidth pixels with bgcolor.
///     Returns width of rendered text in pixels.
///     '''
STATIC mp_obj_t mod_trezorui_Display_text_right(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_buffer_info_t text;
    mp_get_buffer_raise(args[3], &text, MP_BUFFER_READ);
    mp_int_t font = FONT_PY_TO_C(mp_obj_get_int(args[4]));
    mp_int_t fgcolor = mp_obj_get_int(args[5]);
    mp_int_t bgcolor = mp_obj_get_int(args[6]);
    mp_int_t minwidth = (n_args > 7) ? mp_obj_get_int(args[7]) : 0;
    // prefill start
    int w = display_text_width(text.buf, text.len, font);
    int barwidth = MAX(w, minwidth);
    display_bar(x - barwidth, y - 18, barwidth, 23, bgcolor);
    // prefill end
    display_text_right(x, y, text.buf, text.len, font, fgcolor, bgcolor);
    return mp_obj_new_int(w);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_text_right_obj, 7, 8, mod_trezorui_Display_text_right);

/// def text_width(self, text: str, font: int) -> int:
///     '''
///     Returns a width of text in pixels. Font font is used for rendering.
///     '''
STATIC mp_obj_t mod_trezorui_Display_text_width(mp_obj_t self, mp_obj_t text, mp_obj_t font) {
    mp_buffer_info_t txt;
    mp_get_buffer_raise(text, &txt, MP_BUFFER_READ);
    mp_int_t f = FONT_PY_TO_C(mp_obj_get_int(font));
    int w = display_text_width(txt.buf, txt.len, f);
    return mp_obj_new_int(w);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorui_Display_text_width_obj, mod_trezorui_Display_text_width);

/// def qrcode(self, x: int, y: int, data: bytes, scale: int) -> None:
///     '''
///     Renders data encoded as a QR code centered at position (x,y).
///     Scale determines a zoom factor.
///     '''
STATIC mp_obj_t mod_trezorui_Display_qrcode(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[1]);
    mp_int_t y = mp_obj_get_int(args[2]);
    mp_int_t scale = mp_obj_get_int(args[4]);
    if (scale < 1 || scale > 10) {
        mp_raise_ValueError("Scale has to be between 1 and 10");
    }
    mp_buffer_info_t data;
    mp_get_buffer_raise(args[3], &data, MP_BUFFER_READ);
    if (data.len > 0) {
        display_qrcode(x, y, data.buf, data.len, scale);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_qrcode_obj, 5, 5, mod_trezorui_Display_qrcode);

/// def loader(self, progress: int, yoffset: int, fgcolor: int, bgcolor: int, icon: bytes = None, iconfgcolor: int = None) -> None:
///     '''
///     Renders a rotating loader graphic.
///     Progress determines its position (0-1000), fgcolor is used as foreground color, bgcolor as background.
///     When icon and iconfgcolor are provided, an icon is drawn in the middle using the color specified in iconfgcolor.
///     Icon needs to be of exactly LOADER_ICON_SIZE x LOADER_ICON_SIZE pixels size.
///     '''
STATIC mp_obj_t mod_trezorui_Display_loader(size_t n_args, const mp_obj_t *args) {
    mp_int_t progress = mp_obj_get_int(args[1]);
    mp_int_t yoffset = mp_obj_get_int(args[2]);
    mp_int_t fgcolor = mp_obj_get_int(args[3]);
    mp_int_t bgcolor = mp_obj_get_int(args[4]);
    if (n_args > 5) { // icon provided
        mp_buffer_info_t icon;
        mp_get_buffer_raise(args[5], &icon, MP_BUFFER_READ);
        const uint8_t *data = icon.buf;
        if (icon.len < 8 || memcmp(data, "TOIg", 4) != 0) {
            mp_raise_ValueError("Invalid image format");
        }
        mp_int_t w = *(uint16_t *)(data + 4);
        mp_int_t h = *(uint16_t *)(data + 6);
        mp_int_t datalen = *(uint32_t *)(data + 8);
        if (w != LOADER_ICON_SIZE || h != LOADER_ICON_SIZE) {
            mp_raise_ValueError("Invalid icon size");
        }
        if (datalen != icon.len - 12) {
            mp_raise_ValueError("Invalid size of data");
        }
        uint16_t iconfgcolor;
        if (n_args > 6) { // icon color provided
            iconfgcolor = mp_obj_get_int(args[6]);
        } else {
            iconfgcolor = ~bgcolor; // invert
        }
        display_loader(progress, yoffset, fgcolor, bgcolor, icon.buf, icon.len, iconfgcolor);
    } else {
        display_loader(progress, yoffset, fgcolor, bgcolor, NULL, 0, 0);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_loader_obj, 5, 7, mod_trezorui_Display_loader);

/// def orientation(self, degrees: int = None) -> int:
///     '''
///     Sets display orientation to 0, 90, 180 or 270 degrees.
///     Everything needs to be redrawn again when this function is used.
///     Call without the degrees parameter to just perform the read of the value.
///     '''
STATIC mp_obj_t mod_trezorui_Display_orientation(size_t n_args, const mp_obj_t *args) {
    mp_int_t deg;
    if (n_args > 1) {
        deg = mp_obj_get_int(args[1]);
        if (deg != 0 && deg != 90 && deg != 180 && deg != 270) {
            mp_raise_ValueError("Value must be 0, 90, 180 or 270");
        }
        deg = display_orientation(deg);
    } else {
        deg = display_orientation(-1);
    }
    return MP_OBJ_NEW_SMALL_INT(deg);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_orientation_obj, 1, 2, mod_trezorui_Display_orientation);

/// def backlight(self, val: int = None) -> int:
///     '''
///     Sets backlight intensity to the value specified in val.
///     Call without the val parameter to just perform the read of the value.
///     '''
STATIC mp_obj_t mod_trezorui_Display_backlight(size_t n_args, const mp_obj_t *args) {
    mp_int_t val;
    if (n_args > 1) {
        val = mp_obj_get_int(args[1]);
        if (val < 0 || val > 255) {
            mp_raise_ValueError("Value must be between 0 and 255");
        }
        val = display_backlight(val);
    } else {
        val = display_backlight(-1);
    }
    return MP_OBJ_NEW_SMALL_INT(val);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_backlight_obj, 1, 2, mod_trezorui_Display_backlight);

/// def offset(self, xy: Tuple[int, int] = None) -> Tuple[int, int]:
///     '''
///     Sets offset (x, y) for all subsequent drawing calls.
///     Call without the xy parameter to just perform the read of the value.
///     '''
STATIC mp_obj_t mod_trezorui_Display_offset(size_t n_args, const mp_obj_t *args) {
    int xy[2], x, y;
    if (n_args > 1) {
        size_t xy_cnt;
        mp_obj_t *xy_obj;
        if (MP_OBJ_IS_TYPE(args[1], &mp_type_tuple)) {
            mp_obj_tuple_get(args[1], &xy_cnt, &xy_obj);
        } else {
            mp_raise_TypeError("Tuple expected");
        }
        if (xy_cnt != 2) {
            mp_raise_ValueError("Tuple of 2 values expected");
        }
        xy[0] = mp_obj_get_int(xy_obj[0]);
        xy[1] = mp_obj_get_int(xy_obj[1]);
        display_offset(xy, &x, &y);
    } else {
        display_offset(0, &x, &y);
    }
    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
    tuple->items[0] = MP_OBJ_NEW_SMALL_INT(x);
    tuple->items[1] = MP_OBJ_NEW_SMALL_INT(y);
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_offset_obj, 1, 2, mod_trezorui_Display_offset);

/// def save(self, prefix: str) -> None:
///     '''
///     Saves current display contents to PNG file with given prefix.
///     '''
STATIC mp_obj_t mod_trezorui_Display_save(mp_obj_t self, mp_obj_t prefix) {
    mp_buffer_info_t pfx;
    mp_get_buffer_raise(prefix, &pfx, MP_BUFFER_READ);
    if (pfx.len > 0) {
        display_save(pfx.buf);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorui_Display_save_obj, mod_trezorui_Display_save);

STATIC const mp_rom_map_elem_t mod_trezorui_Display_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&mod_trezorui_Display_clear_obj) },
    { MP_ROM_QSTR(MP_QSTR_refresh), MP_ROM_PTR(&mod_trezorui_Display_refresh_obj) },
    { MP_ROM_QSTR(MP_QSTR_bar), MP_ROM_PTR(&mod_trezorui_Display_bar_obj) },
    { MP_ROM_QSTR(MP_QSTR_bar_radius), MP_ROM_PTR(&mod_trezorui_Display_bar_radius_obj) },
    { MP_ROM_QSTR(MP_QSTR_image), MP_ROM_PTR(&mod_trezorui_Display_image_obj) },
    { MP_ROM_QSTR(MP_QSTR_avatar), MP_ROM_PTR(&mod_trezorui_Display_avatar_obj) },
    { MP_ROM_QSTR(MP_QSTR_icon), MP_ROM_PTR(&mod_trezorui_Display_icon_obj) },
    { MP_ROM_QSTR(MP_QSTR_print), MP_ROM_PTR(&mod_trezorui_Display_print_obj) },
    { MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&mod_trezorui_Display_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_text_center), MP_ROM_PTR(&mod_trezorui_Display_text_center_obj) },
    { MP_ROM_QSTR(MP_QSTR_text_right), MP_ROM_PTR(&mod_trezorui_Display_text_right_obj) },
    { MP_ROM_QSTR(MP_QSTR_text_width), MP_ROM_PTR(&mod_trezorui_Display_text_width_obj) },
    { MP_ROM_QSTR(MP_QSTR_qrcode), MP_ROM_PTR(&mod_trezorui_Display_qrcode_obj) },
    { MP_ROM_QSTR(MP_QSTR_loader), MP_ROM_PTR(&mod_trezorui_Display_loader_obj) },
    { MP_ROM_QSTR(MP_QSTR_orientation), MP_ROM_PTR(&mod_trezorui_Display_orientation_obj) },
    { MP_ROM_QSTR(MP_QSTR_backlight), MP_ROM_PTR(&mod_trezorui_Display_backlight_obj) },
    { MP_ROM_QSTR(MP_QSTR_offset), MP_ROM_PTR(&mod_trezorui_Display_offset_obj) },
    { MP_ROM_QSTR(MP_QSTR_save), MP_ROM_PTR(&mod_trezorui_Display_save_obj) },
    { MP_ROM_QSTR(MP_QSTR_WIDTH), MP_OBJ_NEW_SMALL_INT(DISPLAY_RESX) },
    { MP_ROM_QSTR(MP_QSTR_HEIGHT), MP_OBJ_NEW_SMALL_INT(DISPLAY_RESY) },
    { MP_ROM_QSTR(MP_QSTR_FONT_SIZE), MP_OBJ_NEW_SMALL_INT(FONT_SIZE) },
    { MP_ROM_QSTR(MP_QSTR_FONT_MONO), MP_OBJ_NEW_SMALL_INT(FONT_C_TO_PY(FONT_MONO)) },
    { MP_ROM_QSTR(MP_QSTR_FONT_NORMAL), MP_OBJ_NEW_SMALL_INT(FONT_C_TO_PY(FONT_NORMAL)) },
    { MP_ROM_QSTR(MP_QSTR_FONT_BOLD), MP_OBJ_NEW_SMALL_INT(FONT_C_TO_PY(FONT_BOLD)) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorui_Display_locals_dict, mod_trezorui_Display_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorui_Display_type = {
    { &mp_type_type },
    .name = MP_QSTR_Display,
    .make_new = mod_trezorui_Display_make_new,
    .locals_dict = (void*)&mod_trezorui_Display_locals_dict,
};
