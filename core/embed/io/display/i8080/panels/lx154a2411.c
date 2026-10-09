
#include "../display_io.h"

void lx154a2411_gamma(void) {
  // positive voltage correction
  ISSUE_CMD_BYTE(0xE0);
  ISSUE_DATA_BYTE(0xD0);
  ISSUE_DATA_BYTE(0x03);
  ISSUE_DATA_BYTE(0x08);
  ISSUE_DATA_BYTE(0x0E);
  ISSUE_DATA_BYTE(0x11);
  ISSUE_DATA_BYTE(0x2B);
  ISSUE_DATA_BYTE(0x3B);
  ISSUE_DATA_BYTE(0x44);
  ISSUE_DATA_BYTE(0x4C);
  ISSUE_DATA_BYTE(0x2B);
  ISSUE_DATA_BYTE(0x16);
  ISSUE_DATA_BYTE(0x15);
  ISSUE_DATA_BYTE(0x1E);
  ISSUE_DATA_BYTE(0x21);

  // negative voltage correction
  ISSUE_CMD_BYTE(0xE1);
  ISSUE_DATA_BYTE(0xD0);
  ISSUE_DATA_BYTE(0x03);
  ISSUE_DATA_BYTE(0x08);
  ISSUE_DATA_BYTE(0x0E);
  ISSUE_DATA_BYTE(0x11);
  ISSUE_DATA_BYTE(0x2B);
  ISSUE_DATA_BYTE(0x3B);
  ISSUE_DATA_BYTE(0x54);
  ISSUE_DATA_BYTE(0x4C);
  ISSUE_DATA_BYTE(0x2B);
  ISSUE_DATA_BYTE(0x16);
  ISSUE_DATA_BYTE(0x15);
  ISSUE_DATA_BYTE(0x1E);
  ISSUE_DATA_BYTE(0x21);
}

void lx154a2411_init_seq(void) {
  // most recent manual:
  // https://www.newhavendisplay.com/appnotes/datasheets/LCDs/ST7789V.pdf
  // TEON: Tearing Effect Line On; V-blanking only
  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x55);

  // CMD2EN: Commands in command table 2 can be executed when EXTC level is Low
  ISSUE_CMD_BYTE(0xDF);
  ISSUE_DATA_BYTE(0x5A);
  ISSUE_DATA_BYTE(0x69);
  ISSUE_DATA_BYTE(0x02);
  ISSUE_DATA_BYTE(0x01);

  // LCMCTRL: LCM Control: XOR RGB setting
  ISSUE_CMD_BYTE(0xC0);
  ISSUE_DATA_BYTE(0x20);

  // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is gate 80.;
  // gate scan direction 319 -> 0
  ISSUE_CMD_BYTE(0xE4);
  ISSUE_DATA_BYTE(0x1D);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x11);

  // INVOFF (20h): Display Inversion Off
  // INVON  (21h): Display Inversion On
  ISSUE_CMD_BYTE(0x20);

  // the above config is the most important and definitely necessary

  // PWCTRL1: Power Control 1
  ISSUE_CMD_BYTE(0xD0);
  ISSUE_DATA_BYTE(0xA4);
  ISSUE_DATA_BYTE(0xA1);

  lx154a2411_gamma();
}
