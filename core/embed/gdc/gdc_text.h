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

#ifndef GDC_TEXT_H
#define GDC_TEXT_H

#include "gdc_color.h"
#include "gdc_core.h"
#include "gdc_geom.h"

#include <stddef.h>
#include <stdint.h>

typedef struct {
  int font;

  gdc_color_t fg_color;
  gdc_color_t bg_color;

  // TODO: horizontal/vertical alignment??
  // TODO: extra offset???
  gdc_offset_t offset;

} gdc_text_attr_t;

bool gdc_draw_opaque_text(gdc_t* gdc, gdc_rect_t rect, const char* text,
                          size_t maxlen, const gdc_text_attr_t* attr);

bool gdc_draw_blended_text(gdc_t* gdc, gdc_rect_t rect, const char* text,
                           size_t maxlen, const gdc_text_attr_t* attr);

#endif  // GDC_TEXT_H
