

#include "displays/st7789v.h"

void _154a_init_seq(void) {
  // most recent manual: https://www.newhavendisplay.com/app_notes/ILI9341.pdf
  // TEON: Tearing Effect Line On; V-blanking only
  CMD(0x35);
  DATA(0x00);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  CMD(0x3A);
  DATA(0x55);

  // Display Function Control: gate scan direction 319 -> 0
  CMD(0xB6);
  DATA(0x0A);
  DATA(0xC2);
  DATA(0x27);
  DATA(0x00);

  // Interface Control: XOR BGR as ST7789V does
  CMD(0xF6);
  DATA(0x09);
  DATA(0x30);
  DATA(0x00);

  // the above config is the most important and definitely necessary

  CMD(0xCF);
  DATA(0x00);
  DATA(0xC1);
  DATA(0x30);

  CMD(0xED);
  DATA(0x64);
  DATA(0x03);
  DATA(0x12);
  DATA(0x81);

  CMD(0xE8);
  DATA(0x85);
  DATA(0x10);
  DATA(0x7A);

  CMD(0xF7);
  DATA(0x20);

  CMD(0xEA);
  DATA(0x00);
  DATA(0x00);

  // power control VRH[5:0]
  CMD(0xC0);
  DATA(0x23);

  // power control SAP[2:0] BT[3:0]
  CMD(0xC1);
  DATA(0x12);

  // vcm control 1
  CMD(0xC5);
  DATA(0x60);
  DATA(0x44);

  // vcm control 2
  CMD(0xC7);
  DATA(0x8A);

  // framerate
  CMD(0xB1);
  DATA(0x00);
  DATA(0x18);

  // 3 gamma func disable
  CMD(0xF2);
  DATA(0x00);

  // gamma curve 1
  CMD(0xE0);
  DATA(0x0F);
  DATA(0x2F);
  DATA(0x2C);
  DATA(0x0B);
  DATA(0x0F);
  DATA(0x09);
  DATA(0x56);
  DATA(0xD9);
  DATA(0x4A);
  DATA(0x0B);
  DATA(0x14);
  DATA(0x05);
  DATA(0x0C);
  DATA(0x06);
  DATA(0x00);

  // gamma curve 2
  CMD(0xE1);
  DATA(0x00);
  DATA(0x10);
  DATA(0x13);
  DATA(0x04);
  DATA(0x10);
  DATA(0x06);
  DATA(0x25);
  DATA(0x26);
  DATA(0x3B);
  DATA(0x04);
  DATA(0x0B);
  DATA(0x0A);
  DATA(0x33);
  DATA(0x39);
  DATA(0x0F);
}
