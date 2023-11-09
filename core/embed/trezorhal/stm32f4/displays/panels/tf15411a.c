#include "display_interface.h"
#include "displays/st7789v.h"

void tf15411a_init_seq(void) {
  // Inter Register Enable1
  CMD(0xFE);

  // Inter Register Enable2
  CMD(0xEF);

  // TEON: Tearing Effect Line On; V-blanking only
  CMD(0x35);
  DATA(0x00);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  CMD(0x3A);
  DATA(0x55);

  // Frame Rate
  // CMD(0xE8); DATA(0x12); DATA(0x00);

  // Power Control 2
  CMD(0xC3);
  DATA(0x27);

  // Power Control 3
  CMD(0xC4);
  DATA(0x18);

  // Power Control 4
  CMD(0xC9);
  DATA(0x1F);

  CMD(0xC5);
  DATA(0x0F);

  CMD(0xC6);
  DATA(0x00);

  CMD(0xC7);
  DATA(0x10);

  CMD(0xC8);
  DATA(0x01);

  CMD(0xFF);
  DATA(0x62);

  CMD(0x99);
  DATA(0x3E);

  CMD(0x9D);
  DATA(0x4B);

  CMD(0x8E);
  DATA(0x0F);

  // SET_GAMMA1
  CMD(0xF0);
  DATA(0x8F);
  DATA(0x1B);
  DATA(0x05);
  DATA(0x06);
  DATA(0x07);
  DATA(0x42);

  // SET_GAMMA3
  CMD(0xF2);
  DATA(0x5C);
  DATA(0x1F);
  DATA(0x12);
  DATA(0x10);
  DATA(0x07);
  DATA(0x43);

  // SET_GAMMA2
  CMD(0xF1);
  DATA(0x59);
  DATA(0xCF);
  DATA(0xCF);
  DATA(0x35);
  DATA(0x37);
  DATA(0x8F);

  // SET_GAMMA4
  CMD(0xF3);
  DATA(0x58);
  DATA(0xCF);
  DATA(0xCF);
  DATA(0x35);
  DATA(0x37);
  DATA(0x8F);
}

void tf15411a_rotate(int degrees, display_padding_t* padding) {
  uint16_t shift = 0;
  char BX = 0, BY = 0;

#define RGB (1 << 3)
#define ML (1 << 4)  // vertical refresh order
#define MH (1 << 2)  // horizontal refresh order
#define MV (1 << 5)
#define MX (1 << 6)
#define MY (1 << 7)
  // MADCTL: Memory Data Access Control - reference:
  // section 9.3 in the ILI9341 manual
  // section 6.2.18 in the GC9307 manual
  // section 8.12 in the ST7789V manual
  uint8_t display_command_parameter = 0;
  switch (degrees) {
    case 0:
      display_command_parameter = 0;
      BY = 1;
      break;
    case 90:
      display_command_parameter = MV | MX | MH | ML;
      BX = 0;
      shift = 1;
      break;
    case 180:
      display_command_parameter = MX | MY | MH | ML;
      BY = 1;
      shift = 1;
      break;
    case 270:
      display_command_parameter = MV | MY;
      BX = 0;
      break;
  }

  display_command_parameter ^= RGB | MY;  // XOR RGB and MY settings

  CMD(0x36);
  DATA(display_command_parameter);

  if (shift) {
    // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is
    // gate 80.; gate scan direction 319 -> 0
    CMD(0xE4);
    DATA(0x1D);
    DATA(0x00);
    DATA(0x11);
  } else {
    // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is
    // gate 80.; gate scan direction 319 -> 0
    CMD(0xE4);
    DATA(0x1D);
    DATA(0x0A);
    DATA(0x11);
  }

  // reset the column and page extents
  display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);

  padding->x = BX ? (MAX_DISPLAY_RESY - DISPLAY_RESY) : 0;
  padding->y = BY ? (MAX_DISPLAY_RESY - DISPLAY_RESY) : 0;
}
