
#include "display.h"
#include "displays/st7789v.h"
#include "touch.h"

void lx154a2482_gamma(void) {
  // positive voltage correction
  CMD(0xE0);
  DATA(0xD0);
  DATA(0x0A);
  DATA(0x10);
  DATA(0x0A);
  DATA(0x0A);
  DATA(0x26);
  DATA(0x36);
  DATA(0x34);
  DATA(0x4D);
  DATA(0x18);
  DATA(0x13);
  DATA(0x14);
  DATA(0x2F);
  DATA(0x34);

  // negative voltage correction
  CMD(0xE1);
  DATA(0xD0);
  DATA(0x0A);
  DATA(0x10);
  DATA(0x0A);
  DATA(0x09);
  DATA(0x26);
  DATA(0x36);
  DATA(0x53);
  DATA(0x4C);
  DATA(0x18);
  DATA(0x14);
  DATA(0x14);
  DATA(0x2F);
  DATA(0x34);
}

void lx154a2482_init_seq(void) {
  // TEON: Tearing Effect Line On; V-blanking only
  CMD(0x35);
  DATA(0x00);

  // Memory Data Access Control (MADCTL)
  CMD(0x36);
  DATA(0x00);

  // Interface Pixel Format
  CMD(0x3A);
  DATA(0x05);

  // Column Address Set
  CMD(0x2A);
  DATA(0x00);
  DATA(0x00);
  DATA(0x00);
  DATA(0xEF);

  // Row Address Set
  CMD(0x2B);
  DATA(0x00);
  DATA(0x00);
  DATA(0x00);
  DATA(0xEF);

  //  Porch Setting
  CMD(0xB2);
  DATA(0x0C);
  DATA(0x0C);
  DATA(0x00);
  DATA(0x33);
  DATA(0x33);

  // VCOM Setting
  CMD(0xBB);
  DATA(0x1F);

  // LCMCTRL: LCM Control: XOR RGB setting
  CMD(0xC0);
  DATA(0x20);

  // VDV and VRH Command Enable
  CMD(0xC2);
  DATA(0x01);

  // VRH Set
  CMD(0xC3);
  DATA(0x0F);  // 4.3V

  // VDV Setting
  CMD(0xC4);
  DATA(0x20);

  // Frame Rate Control in Normal Mode
  CMD(0xC6);
  DATA(0xEF);  // column inversion     //0X0F  Dot INV, 60Hz

  // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is gate 80.;
  // gate scan direction 319 -> 0
  CMD(0xE4);
  DATA(0x1D);
  DATA(0x0A);
  DATA(0x11);

  // INVOFF (20h): Display Inversion Off
  // INVON  (21h): Display Inversion On
  CMD(0x21);
  // the above config is the most important and definitely necessary

  // PWCTRL1: Power Control 1
  CMD(0xD0);
  DATA(0xA4);
  DATA(0xA1);

  lx154a2482_gamma();
}

void lx154a2482_rotate(int degrees, display_padding_t* padding) {
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
