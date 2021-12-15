/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __LAYOUT_H__
#define __LAYOUT_H__

#include <stdbool.h>
#include <stdlib.h>
#include "bitmaps.h"

void layoutButtonNo(const char *btnNo, const BITMAP *icon);
void layoutButtonYes(const char *btnYes, const BITMAP *icon);
void layoutDialog(const BITMAP *icon, const char *btnNo, const char *btnYes,
                  const char *desc, const char *line1, const char *line2,
                  const char *line3, const char *line4, const char *line5,
                  const char *line6);
void layoutDialogEx(const BITMAP *icon, const char *btnNo, const char *btnYes,
                    const char *desc, const char *line1, const char *line2,
                    const char *line3, const char *line4, const char *line5,
                    const char *line6, uint8_t font);
void layoutProgressUpdate(bool refresh);
void layoutProgress(const char *desc, int permil);

#endif
