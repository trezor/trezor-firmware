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

#include "buffers.h"
#include "common.h"
#include "fonts/fonts.h"
#include "memzero.h"

const int32_t text_buffer_height = FONT_MAX_HEIGHT;
const int32_t buffer_width = DISPLAY_RESX;

#define CONCAT_(a, b) a##b
#define CONCAT(a, b) CONCAT_(a, b)

#define CONCAT3_(a, b, c) a##b##c
#define CONCAT3(a, b, c) CONCAT3_(a, b, c)

#define STRUCT(name) CONCAT3(buffers_, name, _t)
#define TYPE(name) CONCAT3(buffer_, name, _t)
#define FUNCTION(name) CONCAT(buffers_get_, name)
#define FUNCTION_FREE(name) CONCAT(buffers_free_, name)
#define VARNAME(name) CONCAT(buffers_, name)

#define BUFFER(section, name, count)               \
  typedef struct {                                 \
    TYPE(name) buffers[count];                     \
    uint8_t allocated[count];                      \
  } STRUCT(name);                                  \
  section STRUCT(name) VARNAME(name);              \
                                                   \
  TYPE(name) * FUNCTION(name)(bool clear) {        \
    int idx = -1;                                  \
    for (int i = 0; i < (count); i++) {            \
      if (VARNAME(name).allocated[i] == 0) {       \
        idx = i;                                   \
        break;                                     \
      }                                            \
    }                                              \
    if (idx < 0) {                                 \
      return NULL;                                 \
    }                                              \
    if (clear) {                                   \
      memzero(&VARNAME(name).buffers[idx],         \
              sizeof(VARNAME(name).buffers[idx])); \
    }                                              \
    VARNAME(name).allocated[idx] = 1;              \
    return &VARNAME(name).buffers[idx];            \
  }                                                \
  void FUNCTION_FREE(name)(TYPE(name) * buffer) {  \
    if (buffer == NULL) {                          \
      return;                                      \
    }                                              \
    for (uint16_t i = 0; i < (count); i++) {       \
      if (buffer == &VARNAME(name).buffers[i]) {   \
        VARNAME(name).allocated[i] = 0;            \
        return;                                    \
      }                                            \
    }                                              \
  }

BUFFER(BUFFER_SECTION, line_16bpp, 3);
BUFFER(BUFFER_SECTION, line_4bpp, 3);
BUFFER(BUFFER_SECTION, text, 1);
BUFFER(NODMA_BUFFER_SECTION, jpeg, 1);
BUFFER(NODMA_BUFFER_SECTION, jpeg_work, 1);
BUFFER(NODMA_BUFFER_SECTION, blurring, 1);
BUFFER(NODMA_BUFFER_SECTION, blurring_totals, 1);
