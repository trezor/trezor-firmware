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

// using const volatile instead of #define results in binaries that change
// only in 1-byte when the flag changes.
// using #define leads compiler to over-optimize the code leading to bigger
// differencies in the resulting binaries.

#include "display_panel.h"
#include "display_io.h"

#ifdef TREZOR_MODEL_T
#include "panels/154a.h"
#include "panels/lx154a2411.h"
#include "panels/lx154a2422.h"
#include "panels/tf15411a.h"
#else
#include "panels/lx154a2482.h"
#endif

// using const volatile instead of #define results in binaries that change
// only in 1-byte when the flag changes.
// using #define leads compiler to over-optimize the code leading to bigger
// differencies in the resulting binaries.
const volatile uint8_t DISPLAY_ST7789V_INVERT_COLORS2 = 1;

// Window padding (correction) when using 90dg or 270dg orientation
// (internally the display is 240x320 but we use only 240x240)
static display_padding_t g_window_padding;

#ifdef DISPLAY_IDENTIFY
static uint32_t read_display_id(uint8_t command) {
  volatile uint8_t c = 0;
  uint32_t id = 0;
  ISSUE_CMD_BYTE(command);
  c = *DISPLAY_DATA_ADDRESS;  // first returned value is a dummy value and
  // should be discarded
  c = *DISPLAY_DATA_ADDRESS;
  id |= (c << 16);
  c = *DISPLAY_DATA_ADDRESS;
  id |= (c << 8);
  c = *DISPLAY_DATA_ADDRESS;
  id |= c;
  return id;
}

uint32_t display_panel_identify(void) {
  static uint32_t id = 0x000000U;
  static bool id_initialized = false;

  // Return immediately if id has been already initialized
  if (id_initialized) return id;

  // RDDID: Read Display ID
  id = read_display_id(0x04);
  // the default RDDID for ILI9341 should be 0x8000.
  // some display modules return 0x0.
  // the ILI9341 has an extra id, let's check it here.
  if ((id != DISPLAY_ID_ST7789V) && (id != DISPLAY_ID_GC9307)) {
    // Read ID4
    uint32_t id4 = read_display_id(0xD3);
    if (id4 == DISPLAY_ID_ILI9341V) {  // definitely found a ILI9341
      id = id4;
    }
  }
  id_initialized = true;
  return id;
}
#else
uint32_t display_panel_identify(void) { return DISPLAY_ID_ST7789V; }
#endif

bool display_panel_is_inverted() {
  bool inv_on = false;
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_ST7789V) {
    volatile uint8_t c = 0;
    ISSUE_CMD_BYTE(0x09);       // read display status
    c = *DISPLAY_DATA_ADDRESS;  // don't care
    c = *DISPLAY_DATA_ADDRESS;  // don't care
    c = *DISPLAY_DATA_ADDRESS;  // don't care
    c = *DISPLAY_DATA_ADDRESS;
    if (c & 0x20) {
      inv_on = true;
    }
    c = *DISPLAY_DATA_ADDRESS;  // don't care
  }

  return inv_on;
}

void display_panel_sleep(void) {
  uint32_t id = display_panel_identify();
  if ((id == DISPLAY_ID_ILI9341V) || (id == DISPLAY_ID_GC9307) ||
      (id == DISPLAY_ID_ST7789V)) {
    ISSUE_CMD_BYTE(0x28);  // DISPOFF: Display Off
    ISSUE_CMD_BYTE(0x10);  // SLPIN: Sleep in
    HAL_Delay(5);  // need to wait 5 milliseconds after "sleep in" before
    // sending any new commands
  }
}

void display_panel_unsleep(void) {
  uint32_t id = display_panel_identify();
  if ((id == DISPLAY_ID_ILI9341V) || (id == DISPLAY_ID_GC9307) ||
      (id == DISPLAY_ID_ST7789V)) {
    ISSUE_CMD_BYTE(0x11);  // SLPOUT: Sleep Out
    HAL_Delay(5);  // need to wait 5 milliseconds after "sleep out" before
    // sending any new commands
    ISSUE_CMD_BYTE(0x29);  // DISPON: Display On
  }
}

void display_panel_set_window(uint16_t x0, uint16_t y0, uint16_t x1,
                              uint16_t y1) {
  x0 += g_window_padding.x;
  x1 += g_window_padding.x;
  y0 += g_window_padding.y;
  y1 += g_window_padding.y;

  uint32_t id = display_panel_identify();
  if ((id == DISPLAY_ID_ILI9341V) || (id == DISPLAY_ID_GC9307) ||
      (id == DISPLAY_ID_ST7789V)) {
    ISSUE_CMD_BYTE(0x2A);
    ISSUE_DATA_BYTE(x0 >> 8);
    ISSUE_DATA_BYTE(x0 & 0xFF);
    ISSUE_DATA_BYTE(x1 >> 8);
    ISSUE_DATA_BYTE(x1 & 0xFF);  // column addr set
    ISSUE_CMD_BYTE(0x2B);
    ISSUE_DATA_BYTE(y0 >> 8);
    ISSUE_DATA_BYTE(y0 & 0xFF);
    ISSUE_DATA_BYTE(y1 >> 8);
    ISSUE_DATA_BYTE(y1 & 0xFF);  // row addr set
    ISSUE_CMD_BYTE(0x2C);
  }
}

void display_panel_set_little_endian(void) {
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_GC9307) {
    // CANNOT SET ENDIAN FOR GC9307
  } else if (id == DISPLAY_ID_ST7789V) {
    ISSUE_CMD_BYTE(0xB0);
    ISSUE_DATA_BYTE(0x00);
    ISSUE_DATA_BYTE(0xF8);
  } else if (id == DISPLAY_ID_ILI9341V) {
    // Interface Control: XOR BGR as ST7789V does
    ISSUE_CMD_BYTE(0xF6);
    ISSUE_DATA_BYTE(0x09);
    ISSUE_DATA_BYTE(0x30);
    ISSUE_DATA_BYTE(0x20);
  }
}

void display_panel_set_big_endian(void) {
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_GC9307) {
    // CANNOT SET ENDIAN FOR GC9307
  } else if (id == DISPLAY_ID_ST7789V) {
    ISSUE_CMD_BYTE(0xB0);
    ISSUE_DATA_BYTE(0x00);
    ISSUE_DATA_BYTE(0xF0);
  } else if (id == DISPLAY_ID_ILI9341V) {
    // Interface Control: XOR BGR as ST7789V does
    ISSUE_CMD_BYTE(0xF6);
    ISSUE_DATA_BYTE(0x09);
    ISSUE_DATA_BYTE(0x30);
    ISSUE_DATA_BYTE(0x00);
  }
}

void display_panel_init(void) {
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);  // LCD_RST/PC14
  // wait 10 milliseconds. only needs to be low for 10 microseconds.
  // my dev display module ties display reset and touch panel reset together.
  // keeping this low for max(display_reset_time, ctpm_reset_time) aids
  // development and does not hurt.
  HAL_Delay(10);
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_SET);  // LCD_RST/PC14
  // max wait time for hardware reset is 120 milliseconds
  // (experienced display flakiness using only 5ms wait before sending commands)
  HAL_Delay(120);

  // identify the controller we will communicate with
#ifdef TREZOR_MODEL_T
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_GC9307) {
    tf15411a_init_seq();
  } else if (id == DISPLAY_ID_ST7789V) {
    if (DISPLAY_ST7789V_INVERT_COLORS2) {
      lx154a2422_init_seq();
    } else {
      lx154a2411_init_seq();
    }
  } else if (id == DISPLAY_ID_ILI9341V) {
    _154a_init_seq();
  }
#else
  lx154a2482_init_seq();
#endif

  display_panel_unsleep();
}

void display_panel_reinit(void) {
  // reinitialization is needed due to original sequence is unchangable in
  // boardloader
#ifdef TREZOR_MODEL_T
  // model TT has new gamma settings
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_ST7789V && display_panel_is_inverted()) {
    // newest TT display - set proper gamma
    lx154a2422_gamma();
  } else if (id == DISPLAY_ID_ST7789V) {
    lx154a2411_gamma();
  }
#else
  // reduced touch-display interference in T3T1
  lx154a2482_init_seq();
#endif
}

void display_panel_rotate(int angle) {
#ifdef TREZOR_MODEL_T
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_GC9307) {
    tf15411a_rotate(angle, &g_window_padding);
  } else {
    lx154a2422_rotate(angle, &g_window_padding);
  }
#else
  lx154a2482_rotate(angle, &g_window_padding);
#endif
}
