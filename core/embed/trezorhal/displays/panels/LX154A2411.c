
#include "displays/st7789v.h"

void lx154a2411_init_seq() {
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
  CMD(0x20);

  // the above config is the most important and definitely necessary

  // PWCTRL1: Power Control 1
  CMD(0xD0);
  DATA(0xA4);
  DATA(0xA1);
}
