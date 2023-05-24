
#include TREZOR_BOARD
#include "display_interface.h"
#include "displays/st7789v.h"
#include "touch/touch.h"

void lhs200kb_if21_init_seq() {
  CMD(0x36);
  DATA(0x00);

  CMD(0x35);
  DATA(0x00);

  CMD(0x3A);
  DATA(0x05);

  CMD(0xB2);
  DATA(0x0C);
  DATA(0x0C);
  DATA(0x00);
  DATA(0x33);
  DATA(0x33);

  CMD(0xB7);
  DATA(0x78);

  CMD(0xBB);
  DATA(0x2F);

  CMD(0xC0);
  DATA(0x2C);

  CMD(0xC2);
  DATA(0x01);

  CMD(0xC3);
  DATA(0x19);

  CMD(0xC4);
  DATA(0x20);

  CMD(0xC6);
  DATA(0x0F);

  CMD(0xD0);
  DATA(0xA4);
  DATA(0xA1);

  CMD(0xD6);
  DATA(0xA1);

  CMD(0xE0);
  DATA(0xF0);
  DATA(0x08);
  DATA(0x0F);
  DATA(0x0B);
  DATA(0x0B);
  DATA(0x07);
  DATA(0x34);
  DATA(0x43);
  DATA(0x4B);
  DATA(0x38);
  DATA(0x14);
  DATA(0x13);
  DATA(0x2C);
  DATA(0x31);

  CMD(0xE1);
  DATA(0xF0);
  DATA(0x0C);
  DATA(0x11);
  DATA(0x09);
  DATA(0x08);
  DATA(0x24);
  DATA(0x34);
  DATA(0x33);
  DATA(0x4A);
  DATA(0x3A);
  DATA(0x16);
  DATA(0x16);
  DATA(0x2E);
  DATA(0x32);

  CMD(0x21);

  CMD(0x29);
}

void lhs200kb_if21_rotate(int degrees, buffer_offset_t* offset) {
  uint16_t shift = 0;
  char BX = 0, BY = 0;

#define RGB (1 << 3)
#define ML (1 << 4)  // vertical refresh order
#define MH (1 << 2)  // horizontal refresh order
#define MV (1 << 5)
#define MX (1 << 6)
#define MY (1 << 7)
  // MADCTL: Memory Data Access Control - reference:
  // section 8.12 in the ST7789V manual
  uint8_t display_command_parameter = 0;
  switch (degrees) {
    case 0:
      display_command_parameter = 0;
      BY = 0;
      break;
    case 90:
      display_command_parameter = MV | MX | MH | ML;
      BX = 1;
      shift = 1;
      break;
    case 180:
      display_command_parameter = MX | MY | MH | ML;
      BY = 0;
      shift = 1;
      break;
    case 270:
      display_command_parameter = MV | MY;
      BX = 1;
      break;
  }

  CMD(0x36);
  DATA(display_command_parameter);

  if (shift) {
    // GATECTRL: Gate Control; NL = 320 gate lines, first scan line is
    // gate 0.; gate scan direction 319 -> 0
    CMD(0xE4);
    DATA(0x27);
    DATA(0x00);
    DATA(0x10);
  } else {
    // GATECTRL: Gate Control; NL = 320 gate lines, first scan line is
    // gate 0.; gate scan direction 319 -> 0
    CMD(0xE4);
    DATA(0x27);
    DATA(0x00);
    DATA(0x10);
  }

  // reset the column and page extents
  display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);

  offset->x = BX ? (MAX_DISPLAY_RESY - DISPLAY_RESY) : 0;
  offset->y = BY ? (MAX_DISPLAY_RESY - DISPLAY_RESY) : 0;
}

uint32_t lhs200kb_if21_transform_touch_coords(uint16_t x, uint16_t y) {
  return touch_pack_xy(y, MAX_DISPLAY_RESY - x);
}
