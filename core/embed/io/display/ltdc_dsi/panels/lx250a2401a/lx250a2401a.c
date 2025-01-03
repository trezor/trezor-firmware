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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/systick.h>

#include "lx250a2401a.h"

#include "../../display_internal.h"

#define GFXMMU_LINE_L(line_offset, first_block, last_block) \
  (0x1 | ((first_block) << 8) | ((last_block) << 16))
#define GFXMMU_LINE_H(line_offset, first_block, last_block) \
  ((((line_offset) - ((first_block))) & 0x3FFFF) << 4)

typedef struct {
  uint16_t limit;
  uint8_t px;
} lut_def_t;

static uint32_t gfxmmu_lut_config[2 * GFXMMU_LUT_SIZE] = {0};

static uint32_t lut_add_line(uint32_t line, uint32_t offset,
                             uint32_t first_pixel) {
  uint32_t pixel_cut = first_pixel - 1;
  uint32_t first_block = pixel_cut >> 2;
  uint32_t last_block = (DISPLAY_RESX - 1 - pixel_cut) >> 2;

  gfxmmu_lut_config[line * 2] = GFXMMU_LINE_L(offset, first_block, last_block);
  gfxmmu_lut_config[line * 2 + 1] =
      GFXMMU_LINE_H(offset, first_block, last_block);

  return last_block - first_block + 1;
}

const uint32_t *panel_lut_get(void) {
  uint32_t offset = 0;
  uint32_t line = 0;

  const lut_def_t lut[] = {
      {1, 13}, {1, 11}, {1, 9},   {1, 8},  {1, 6},  {2, 5},  {1, 4},  {2, 3},
      {2, 2},  {4, 1},  {411, 1}, {12, 1}, {7, 2},  {6, 3},  {5, 4},  {4, 5},
      {4, 6},  {3, 7},  {4, 8},   {2, 9},  {4, 10}, {2, 11}, {3, 12}, {2, 13},
      {3, 14}, {2, 15}, {2, 16},  {2, 17}, {3, 18}, {1, 19}, {3, 20}, {1, 21},
      {2, 22}, {2, 23}, {2, 24},  {1, 25}, {2, 26}, {2, 27}, {1, 28}, {2, 29},
      {1, 30}, {1, 32}, {1, 33},  {1, 36},
  };

  for (uint32_t i = 0; i < sizeof(lut) / sizeof(lut_def_t); i++) {
    for (uint32_t j = 0; j < lut[i].limit; j++) {
      offset += lut_add_line(line++, offset, lut[i].px);
    }
  }
  return gfxmmu_lut_config;
}

bool panel_init(display_driver_t *drv) {
  HAL_StatusTypeDef ret;

  // Write(Command , 0xFF);
  // Write(Parameter , 0x77);
  // Write(Parameter , 0x01);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x13);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 10, 0xFF,
                          (uint8_t[]){0x77, 0x01, 0x00, 0x00, 0x13});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xEF);
  // Write(Parameter , 0x08);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xEF,
                           0x08);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xFF);
  // Write(Parameter , 0x77);
  // Write(Parameter , 0x01);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x10);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 10, 0xFF,
                          (uint8_t[]){0x77, 0x01, 0x00, 0x00, 0x10});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xC0);
  // Write(Parameter , 0x40);
  // Write(Parameter , 0x00);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC0,
                          (uint8_t[]){0x40, 0x00});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xC1);
  // Write(Parameter , 0x0D);
  // Write(Parameter , 0x02);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC1,
                          (uint8_t[]){0x0D, 0x02});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xC2);
  // Write(Parameter , 0x37);  //column  //0x30  1dot
  // Write(Parameter , 0x06);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC2,
                          (uint8_t[]){0x37, 0x06});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xCC);
  // Write(Parameter , 0x18);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xCC,
                           0x18);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB0);
  // Write(Parameter , 0x40);
  // Write(Parameter , 0x8D);
  // Write(Parameter , 0x96);
  // Write(Parameter , 0x0F);
  // Write(Parameter , 0x13);
  // Write(Parameter , 0x07);
  // Write(Parameter , 0x07);
  // Write(Parameter , 0x0B);
  // Write(Parameter , 0x08);
  // Write(Parameter , 0x23);
  // Write(Parameter , 0x09);
  // Write(Parameter , 0x58);
  // Write(Parameter , 0x14);
  // Write(Parameter , 0x29);
  // Write(Parameter , 0xAD);
  // Write(Parameter , 0xDF);
  ret = HAL_DSI_LongWrite(
      &drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 16, 0xB0,
      (uint8_t[]){0x40, 0x8D, 0x96, 0x0F, 0x13, 0x07, 0x07, 0x0B, 0x08, 0x23,
                  0x09, 0x58, 0x14, 0x29, 0xAD, 0xDF});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB1);
  // Write(Parameter , 0x40);
  // Write(Parameter , 0xCD);
  // Write(Parameter , 0x13);
  // Write(Parameter , 0x0B);
  // Write(Parameter , 0x10);
  // Write(Parameter , 0x06);
  // Write(Parameter , 0x04);
  // Write(Parameter , 0x06);
  // Write(Parameter , 0x07);
  // Write(Parameter , 0x20);
  // Write(Parameter , 0x06);
  // Write(Parameter , 0x17);
  // Write(Parameter , 0x17);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x22);
  // Write(Parameter , 0xDF);
  ret = HAL_DSI_LongWrite(
      &drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 16, 0xB1,
      (uint8_t[]){0x40, 0xCD, 0x13, 0x0B, 0x10, 0x06, 0x04, 0x06, 0x07, 0x20,
                  0x06, 0x17, 0x17, 0xA0, 0x22, 0xDF});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xFF);
  // Write(Parameter , 0x77);
  // Write(Parameter , 0x01);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x11);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 10, 0xFF,
                          (uint8_t[]){0x77, 0x01, 0x00, 0x00, 0x11});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB0);
  // Write(Parameter , 0x4D);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB0,
                           0x4D);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB1);
  // Write(Parameter , 0x4B);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB1,
                           0x4B);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB2);
  // Write(Parameter , 0x85);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB2,
                           0x85);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB3);
  // Write(Parameter , 0x80);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB3,
                           0x80);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB5);
  // Write(Parameter , 0x45);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB5,
                           0x45);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB8);
  // Write(Parameter , 0x33);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB8,
                           0x33);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xB9);
  // Write(Parameter , 0x10);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB9,
                           0x10);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xC0);
  // Write(Parameter , 0x09);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xC0,
                           0x09);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xC1);
  // Write(Parameter , 0x78);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xC1,
                           0x78);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xC2);
  // Write(Parameter , 0x78);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xC2,
                           0x78);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xD0);
  // Write(Parameter , 0x88);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xD0,
                           0x88);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x3A);
  // Write(Parameter , 0x02);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 3, 0xE0,
                          (uint8_t[]){0x00, 0x3A, 0x02});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE1);
  // Write(Parameter , 0x08);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x07);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x40);
  // Write(Parameter , 0x40);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 11, 0xE1,
                          (uint8_t[]){0x08, 0xA0, 0x00, 0xA0, 0x07, 0xA0, 0x00,
                                      0xA0, 0x00, 0x40, 0x40});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE2);
  // Write(Parameter , 0x20);
  // Write(Parameter , 0x20);
  // Write(Parameter , 0x40);
  // Write(Parameter , 0x40);
  // Write(Parameter , 0x16);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x15);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x00);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 13, 0xE2,
                          (uint8_t[]){0x20, 0x20, 0x40, 0x40, 0x16, 0xA0, 0x00,
                                      0xA0, 0x15, 0xA0, 0x00, 0xA0, 0x00});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE3);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x22);
  // Write(Parameter , 0x22);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 4, 0xE3,
                          (uint8_t[]){0x00, 0x00, 0x22, 0x22});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE4);
  // Write(Parameter , 0x44);
  // Write(Parameter , 0x44);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xE4,
                          (uint8_t[]){0x44, 0x44});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE5);
  // Write(Parameter , 0x0A);
  // Write(Parameter , 0x13);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x0C);
  // Write(Parameter , 0x15);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x0E);
  // Write(Parameter , 0x17);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x10);
  // Write(Parameter , 0x19);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  ret = HAL_DSI_LongWrite(
      &drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 16, 0xE5,
      (uint8_t[]){0x0A, 0x13, 0xD8, 0xA0, 0x0C, 0x15, 0xD8, 0xA0, 0x0E, 0x17,
                  0xD8, 0xA0, 0x10, 0x19, 0xD8, 0xA0});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE6);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x22);
  // Write(Parameter , 0x22);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 4, 0xE6,
                          (uint8_t[]){0x00, 0x00, 0x22, 0x22});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE7);
  // Write(Parameter , 0x44);
  // Write(Parameter , 0x44);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xE7,
                          (uint8_t[]){0x44, 0x44});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xE8);
  // Write(Parameter , 0x09);
  // Write(Parameter , 0x12);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x0B);
  // Write(Parameter , 0x14);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x0D);
  // Write(Parameter , 0x16);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  // Write(Parameter , 0x0F);
  // Write(Parameter , 0x18);
  // Write(Parameter , 0xD8);
  // Write(Parameter , 0xA0);
  ret = HAL_DSI_LongWrite(
      &drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 16, 0xE8,
      (uint8_t[]){0x09, 0x12, 0xD8, 0xA0, 0x0B, 0x14, 0xD8, 0xA0, 0x0D, 0x16,
                  0xD8, 0xA0, 0x0F, 0x18, 0xD8, 0xA0});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xEB);
  // Write(Parameter , 0x02);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xE4);
  // Write(Parameter , 0xE4);
  // Write(Parameter , 0x88);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  ret =
      HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 8, 0xEB,
                        (uint8_t[]){0x02, 0x00, 0xE4, 0xE4, 0x88, 0x00, 0x00});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xEC);
  // Write(Parameter , 0x02);
  // Write(Parameter , 0x00);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xEC,
                          (uint8_t[]){0x02, 0x00});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xED);
  // Write(Parameter , 0xFF);
  // Write(Parameter , 0x07);
  // Write(Parameter , 0x65);
  // Write(Parameter , 0x4A);
  // Write(Parameter , 0xB2);
  // Write(Parameter , 0xF8);
  // Write(Parameter , 0x9F);
  // Write(Parameter , 0xFF);
  // Write(Parameter , 0xFF);
  // Write(Parameter , 0xF9);
  // Write(Parameter , 0x8F);
  // Write(Parameter , 0x2B);
  // Write(Parameter , 0xA4);
  // Write(Parameter , 0x56);
  // Write(Parameter , 0x70);
  // Write(Parameter , 0xFF);
  ret = HAL_DSI_LongWrite(
      &drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 16, 0xED,
      (uint8_t[]){0xFF, 0x07, 0x65, 0x4A, 0xB2, 0xF8, 0x9F, 0xFF, 0xFF, 0xF9,
                  0x8F, 0x2B, 0xA4, 0x56, 0x70, 0xFF});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0xEF);
  // Write(Parameter , 0x08);
  // Write(Parameter , 0x08);
  // Write(Parameter , 0x08);
  // Write(Parameter , 0x45);
  // Write(Parameter , 0x3F);
  // Write(Parameter , 0x54);
  ret = HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 6, 0xEF,
                          (uint8_t[]){0x08, 0x08, 0x08, 0x45, 0x3F, 0x54});
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0x35);
  // Write(Parameter , 0x00);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x35,
                           0x00);
  if (ret != HAL_OK) {
    return false;
  }

  // Write(Command , 0x11);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x11,
                           0x00);
  if (ret != HAL_OK) {
    return false;
  }

  systick_delay_ms(120);

  // Write(Command , 0x29);
  ret = HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x29,
                           0x00);
  if (ret != HAL_OK) {
    return false;
  }

  systick_delay_ms(20);

  return true;
}
