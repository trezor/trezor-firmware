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

// Embedded images for the `display-slideshow` prodtest command.
//
// To add an image, run the converter (see core/tools/display_image_converter.py):
//   python display_image_converter.py IMAGE.png --width 240 --height 320
//     --output-c prodtest_img_NAME.h --symbol prodtest_img_NAME
// Then #include the generated header below and add an entry to PRODTEST_IMAGES[].

#pragma once

#include <stdint.h>

typedef struct {
  const char* name;
  int width;
  int height;
  const uint8_t* data;  // RGB565 little-endian, tight-packed (no stride), row-major
} prodtest_image_t;

#include "prodtest_img_ui_concept_1_screen_0.h"
#include "prodtest_img_ui_concept_1_screen_1.h"
#include "prodtest_img_ui_concept_1_screen_2.h"
#include "prodtest_img_ui_concept_1_screen_3.h"
#include "prodtest_img_ui_concept_2_screen_0.h"
#include "prodtest_img_ui_concept_2_screen_1.h"
#include "prodtest_img_ui_concept_2_screen_2.h"
#include "prodtest_img_ui_concept_2_screen_3.h"
#include "prodtest_img_ui_ts7_downscaled_screen_0.h"
#include "prodtest_img_ui_ts7_downscaled_screen_1.h"
#include "prodtest_img_ui_ts7_downscaled_screen_2.h"

static const prodtest_image_t PRODTEST_IMAGES[] = {
    {"UI_Concept_1_Screen-0", prodtest_img_ui_concept_1_screen_0_WIDTH, prodtest_img_ui_concept_1_screen_0_HEIGHT, prodtest_img_ui_concept_1_screen_0},
    {"UI_Concept_1_Screen-1", prodtest_img_ui_concept_1_screen_1_WIDTH, prodtest_img_ui_concept_1_screen_1_HEIGHT, prodtest_img_ui_concept_1_screen_1},
    {"UI_Concept_1_Screen-2", prodtest_img_ui_concept_1_screen_2_WIDTH, prodtest_img_ui_concept_1_screen_2_HEIGHT, prodtest_img_ui_concept_1_screen_2},
    {"UI_Concept_1_Screen-3", prodtest_img_ui_concept_1_screen_3_WIDTH, prodtest_img_ui_concept_1_screen_3_HEIGHT, prodtest_img_ui_concept_1_screen_3},
    {"UI_Concept_2_Screen-0", prodtest_img_ui_concept_2_screen_0_WIDTH, prodtest_img_ui_concept_2_screen_0_HEIGHT, prodtest_img_ui_concept_2_screen_0},
    {"UI_Concept_2_Screen-1", prodtest_img_ui_concept_2_screen_1_WIDTH, prodtest_img_ui_concept_2_screen_1_HEIGHT, prodtest_img_ui_concept_2_screen_1},
    {"UI_Concept_2_Screen-2", prodtest_img_ui_concept_2_screen_2_WIDTH, prodtest_img_ui_concept_2_screen_2_HEIGHT, prodtest_img_ui_concept_2_screen_2},
    {"UI_Concept_2_Screen-3", prodtest_img_ui_concept_2_screen_3_WIDTH, prodtest_img_ui_concept_2_screen_3_HEIGHT, prodtest_img_ui_concept_2_screen_3},
    {"UI_TS7_Downscaled_Screen-0", prodtest_img_ui_ts7_downscaled_screen_0_WIDTH, prodtest_img_ui_ts7_downscaled_screen_0_HEIGHT, prodtest_img_ui_ts7_downscaled_screen_0},
    {"UI_TS7_Downscaled_Screen-1", prodtest_img_ui_ts7_downscaled_screen_1_WIDTH, prodtest_img_ui_ts7_downscaled_screen_1_HEIGHT, prodtest_img_ui_ts7_downscaled_screen_1},
    {"UI_TS7_Downscaled_Screen-2", prodtest_img_ui_ts7_downscaled_screen_2_WIDTH, prodtest_img_ui_ts7_downscaled_screen_2_HEIGHT, prodtest_img_ui_ts7_downscaled_screen_2},
};

#define PRODTEST_IMAGES_COUNT \
  ((int)(sizeof(PRODTEST_IMAGES) / sizeof(PRODTEST_IMAGES[0])))

