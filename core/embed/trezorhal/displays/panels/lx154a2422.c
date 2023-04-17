
#include "displays/st7789v.h"

void lx154a2422_gamma(void) {
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

void lx154a2422_init_seq(void) {
  // most recent manual:
  // https://www.newhavendisplay.com/appnotes/datasheets/LCDs/ST7789V.pdf
  // TEON: Tearing Effect Line On; V-blanking only
  CMD(0x35);
  DATA(0x00);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  CMD(0x3A);
  DATA(0x55);

  // CMD2EN: Commands in command table 2 can be executed when EXTC level is Low
  CMD(0xDF);
  DATA(0x5A);
  DATA(0x69);
  DATA(0x02);
  DATA(0x01);

  // LCMCTRL: LCM Control: XOR RGB setting
  CMD(0xC0);
  DATA(0x20);

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

  lx154a2422_gamma();
}
