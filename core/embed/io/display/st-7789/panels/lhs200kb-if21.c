#include <trezor_model.h>

#include "../display_io.h"
#include "lhs200kb-if21.h"

void lhs200kb_if21_gamma(void) {
  ISSUE_CMD_BYTE(0xE0);
  ISSUE_DATA_BYTE(0xF0);
  ISSUE_DATA_BYTE(0x08);
  ISSUE_DATA_BYTE(0x0F);
  ISSUE_DATA_BYTE(0x0B);
  ISSUE_DATA_BYTE(0x0B);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x34);
  ISSUE_DATA_BYTE(0x43);
  ISSUE_DATA_BYTE(0x4B);
  ISSUE_DATA_BYTE(0x38);
  ISSUE_DATA_BYTE(0x14);
  ISSUE_DATA_BYTE(0x13);
  ISSUE_DATA_BYTE(0x2C);
  ISSUE_DATA_BYTE(0x31);

  ISSUE_CMD_BYTE(0xE1);
  ISSUE_DATA_BYTE(0xF0);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x11);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x08);
  ISSUE_DATA_BYTE(0x24);
  ISSUE_DATA_BYTE(0x34);
  ISSUE_DATA_BYTE(0x33);
  ISSUE_DATA_BYTE(0x4A);
  ISSUE_DATA_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x16);
  ISSUE_DATA_BYTE(0x16);
  ISSUE_DATA_BYTE(0x2E);
  ISSUE_DATA_BYTE(0x32);
}
void lhs200kb_if21_init_seq() {
  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(0x00);

  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x05);

  ISSUE_CMD_BYTE(0xB2);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x33);
  ISSUE_DATA_BYTE(0x33);

  ISSUE_CMD_BYTE(0xB7);
  ISSUE_DATA_BYTE(0x78);

  ISSUE_CMD_BYTE(0xBB);
  ISSUE_DATA_BYTE(0x2F);

  ISSUE_CMD_BYTE(0xC0);
  ISSUE_DATA_BYTE(0x2C);

  ISSUE_CMD_BYTE(0xC2);
  ISSUE_DATA_BYTE(0x01);

  ISSUE_CMD_BYTE(0xC3);
  ISSUE_DATA_BYTE(0x19);

  ISSUE_CMD_BYTE(0xC4);
  ISSUE_DATA_BYTE(0x20);

  ISSUE_CMD_BYTE(0xC6);
  ISSUE_DATA_BYTE(0x0F);

  ISSUE_CMD_BYTE(0xD0);
  ISSUE_DATA_BYTE(0xA4);
  ISSUE_DATA_BYTE(0xA1);

  ISSUE_CMD_BYTE(0xD6);
  ISSUE_DATA_BYTE(0xA1);

  lhs200kb_if21_gamma();

  ISSUE_CMD_BYTE(0x21);

  ISSUE_CMD_BYTE(0x29);
}

void lhs200kb_if21_rotate(int degrees, display_padding_t* padding) {
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

  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(display_command_parameter);

  if (shift) {
    // GATECTRL: Gate Control; NL = 320 gate lines, first scan line is
    // gate 0.; gate scan direction 319 -> 0
    ISSUE_CMD_BYTE(0xE4);
    ISSUE_DATA_BYTE(0x27);
    ISSUE_DATA_BYTE(0x00);
    ISSUE_DATA_BYTE(0x10);
  } else {
    // GATECTRL: Gate Control; NL = 320 gate lines, first scan line is
    // gate 0.; gate scan direction 319 -> 0
    ISSUE_CMD_BYTE(0xE4);
    ISSUE_DATA_BYTE(0x27);
    ISSUE_DATA_BYTE(0x00);
    ISSUE_DATA_BYTE(0x10);
  }

  padding->x = BX ? (320 - DISPLAY_RESY) : 0;
  padding->y = BY ? (320 - DISPLAY_RESY) : 0;
}

// uint32_t lhs200kb_if21_transform_touch_coords(uint16_t x, uint16_t y) {
//   return touch_pack_xy(y, MAX_DISPLAY_RESY - x);
// }
