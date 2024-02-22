/*
 * This file is part of the Trezor project, https://trezor.io/
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

#include "gdc_text.h"

#include "fonts/fonts.h"

#if TREZOR_FONT_BPP == 1
#define GLYPH_FORMAT GDC_FORMAT_MONO1
#define GLYPH_STRIDE(w) (((w) + 7) / 8)
#elif TREZOR_FONT_BPP == 2
#error Unsupported TREZOR_FONT_BPP value
#define GLYPH_FORMAT GDC_FORMAT_MONO2
#define GLYPH_STRIDE(w) (((w) + 3) / 4)
#elif TREZOR_FONT_BPP == 4
#define GLYPH_FORMAT GDC_FORMAT_MONO4
#define GLYPH_STRIDE(w) (((w) + 1) / 2)
#elif TREZOR_FONT_BPP == 8
#error Unsupported TREZOR_FONT_BPP value
#define GLYPH_FORMAT GDC_FORMAT_MONO8
#define GLYPH_STRIDE(w) (w)
#else
#error Unsupported TREZOR_FONT_BPP value
#endif

#define GLYPH_WIDTH(g) ((g)[0])
#define GLYPH_HEIGHT(g) ((g)[1])
#define GLYPH_ADVANCE(g) ((g)[2])
#define GLYPH_BEARING_X(g) ((g)[3])
#define GLYPH_BEARING_Y(g) ((g)[4])
#define GLYPH_DATA(g) ((void*)&(g)[5])

bool gdc_draw_opaque_text(gdc_t* gdc, gdc_rect_t rect, const char* text,
                          size_t maxlen, const gdc_text_attr_t* attr) {
  if (text == NULL) {
    return false;
  }

  gdc_bitmap_t glyph_bitmap;
  glyph_bitmap.vmt = NULL;
  glyph_bitmap.format = GLYPH_FORMAT;

  gdc_bitmap_ref_t glyph_ref;
  glyph_ref.bitmap = &glyph_bitmap;
  glyph_ref.fg_color = attr->fg_color;
  glyph_ref.bg_color = attr->bg_color;

  int max_height = font_max_height(attr->font);
  int baseline = font_baseline(attr->font);

  int offset_x = attr->offset.x;

  if (offset_x < 0) {
    rect.x0 -= attr->offset.x;
    offset_x = 0;
  }

  for (int i = 0; i < maxlen; i++) {
    uint8_t ch = (uint8_t)text[i];

    if (ch == 0 || rect.x0 >= rect.x1) {
      break;
    }

    const uint8_t* glyph = font_get_glyph(attr->font, ch);

    if (glyph == NULL) {
      continue;
    }

    if (offset_x >= GLYPH_ADVANCE(glyph)) {
      offset_x -= GLYPH_ADVANCE(glyph);
      continue;
    }

    glyph_bitmap.ptr = GLYPH_DATA(glyph);
    glyph_bitmap.stride = GLYPH_STRIDE(GLYPH_WIDTH(glyph));
    glyph_bitmap.size.x = GLYPH_WIDTH(glyph);
    glyph_bitmap.size.y = GLYPH_HEIGHT(glyph);

    glyph_ref.offset.x = attr->offset.x - GLYPH_BEARING_X(glyph);
    glyph_ref.offset.y =
        attr->offset.y - (max_height - baseline - GLYPH_BEARING_Y(glyph));

    if (!gdc_draw_bitmap(gdc, rect, &glyph_ref)) {
      return false;
    }

    rect.x0 += GLYPH_ADVANCE(glyph) - offset_x;
    offset_x = 0;
  }

  return true;
}

bool gdc_draw_blended_text(gdc_t* gdc, gdc_rect_t rect, const char* text,
                           size_t maxlen, const gdc_text_attr_t* attr) {
  if (text == NULL) {
    return false;
  }

  gdc_bitmap_t glyph_bitmap;
  glyph_bitmap.vmt = NULL;
  glyph_bitmap.format = GLYPH_FORMAT;

  gdc_bitmap_ref_t glyph_ref;
  glyph_ref.bitmap = &glyph_bitmap;
  glyph_ref.fg_color = attr->fg_color;
  glyph_ref.bg_color = attr->bg_color;

  int max_height = font_max_height(attr->font);
  int baseline = font_baseline(attr->font);

  int offset_x = attr->offset.x;

  if (offset_x < 0) {
    rect.x0 -= attr->offset.x;
    offset_x = 0;
  }

  for (int i = 0; i < maxlen; i++) {
    uint8_t ch = (uint8_t)text[i];

    if (ch == 0 || rect.x0 >= rect.x1) {
      break;
    }

    const uint8_t* glyph = font_get_glyph(attr->font, ch);

    if (glyph == NULL) {
      continue;
    }

    if (offset_x >= GLYPH_ADVANCE(glyph)) {
      offset_x -= GLYPH_ADVANCE(glyph);
      continue;
    } else {
    }

    glyph_bitmap.ptr = GLYPH_DATA(glyph);
    glyph_bitmap.stride = GLYPH_STRIDE(GLYPH_WIDTH(glyph));
    glyph_bitmap.size.x = GLYPH_WIDTH(glyph);
    glyph_bitmap.size.y = GLYPH_HEIGHT(glyph);

    glyph_ref.offset.x = offset_x - GLYPH_BEARING_X(glyph);
    glyph_ref.offset.y =
        attr->offset.y - (max_height - baseline - GLYPH_BEARING_Y(glyph));

    if (!gdc_draw_blended(gdc, rect, &glyph_ref)) {
      return false;
    }

    rect.x0 += GLYPH_ADVANCE(glyph) - offset_x;
    offset_x = 0;
  }

  return true;
}
