
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/systick.h>

#include "lx200d2406a.h"

#include "../../display_internal.h"

// todo static assert resolution

void panel_init(display_driver_t *drv) {
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x11, 0);

  systick_delay_ms(120);

  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x36, 0x00);
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x3A, 0x06);

  // mipi video mode
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB0, 0x10);

  // Write(Command , 0xB2);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0C);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0C);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x33);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x33);
  HAL_DSI_LongWrite(
      &drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 10, 0xB2,
      (uint8_t[]){0x00, 0x0c, 0x00, 0x0C, 0x00, 0x00, 0x00, 0x33, 0x00, 0x33});

  // Write(Command , 0xB7);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x06);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xB7,
                    (uint8_t[]){0x00, 0x06});

  // Write(Command , 0xBB);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x1E);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xBB,
                    (uint8_t[]){0x00, 0x1E});

  //   Write(Command , 0xC0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x2C);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC0,
                    (uint8_t[]){0x00, 0x2C});

  //   Write(Command , 0xC2);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x01);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC2,
                    (uint8_t[]){0x00, 0x01});

  // Write(Command , 0xC3);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0F);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC3,
                    (uint8_t[]){0x00, 0x0F});

  // Write(Command , 0xC6);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0F);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC6,
                    (uint8_t[]){0x00, 0x0F});

  // Write(Command , 0xD0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA7);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xD0,
                    (uint8_t[]){0x00, 0xA7});

  // Write(Command , 0xD0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA4);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA1);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 4, 0xD0,
                    (uint8_t[]){0x00, 0xA4, 0x00, 0xA1});

  // Write(Command , 0xD6);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA1);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xD6,
                    (uint8_t[]){0x00, 0xA1});

  // Write(Command , 0xE0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xF0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x06);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x11);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x09);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0A);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x28);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x37);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x44);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x4E);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x39);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x14);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x15);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x34);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x3A);
  // HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE,  28, 0xE0,
  // (uint8_t[]){0x00, 0xF0, 0x00, 0x06, 0x00, 0x11, 0x00, 0x09, 0x00, 0x0A,
  // 0x00, 0x28, 0x00, 0x37, 0x00, 0x44, 0x00, 0x4E, 0x00, 0x39, 0x00, 0x14,
  // 0x00, 0x15, 0x00, 0x34, 0x00, 0x3A});

  // Write(Command , 0xE1);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xF0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0E);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0F);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0A);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x08);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x04);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x37);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x43);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x4D);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x35);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x12);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x13);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x32);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x39);
  // HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE,  28, 0xE1,
  // (uint8_t[]){0x00, 0xF0, 0x00, 0x0E, 0x00, 0x0F, 0x00, 0x0A, 0x00, 0x08,
  // 0x00, 0x04, 0x00, 0x37, 0x00, 0x43, 0x00, 0x4D, 0x00, 0x35, 0x00, 0x12,
  // 0x00, 0x13, 0x00, 0x32, 0x00, 0x39});

  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x21, 0);
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x29, 0);
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x2C, 0);
}
