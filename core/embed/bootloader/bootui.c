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

#include <string.h>

#include "bootui.h"
#include "display.h"
#include "icon_cancel.h"
#include "icon_confirm.h"
#include "icon_done.h"
#include "icon_fail.h"
#include "icon_info.h"
#include "icon_install.h"
#include "icon_logo.h"
#include "icon_safeplace.h"
#include "icon_welcome.h"
#include "icon_wipe.h"
#include "mini_printf.h"
#include "touch.h"
#include "version.h"

#define BACKLIGHT_NORMAL 150

#define COLOR_BL_BG COLOR_WHITE                   // background
#define COLOR_BL_FG COLOR_BLACK                   // foreground
#define COLOR_BL_FAIL RGB16(0xFF, 0x00, 0x00)     // red
#define COLOR_BL_DONE RGB16(0x00, 0xAE, 0x0B)     // green
#define COLOR_BL_PROCESS RGB16(0x4A, 0x90, 0xE2)  // blue
#define COLOR_BL_GRAY RGB16(0x99, 0x99, 0x99)     // gray

#define COLOR_WELCOME_BG COLOR_WHITE  // welcome background
#define COLOR_WELCOME_FG COLOR_BLACK  // welcome foreground

// common shared functions

static void ui_confirm_cancel_buttons(void) {
  display_bar_radius(9, 184, 108, 50, COLOR_BL_FAIL, COLOR_BL_BG, 4);
  display_icon(9 + (108 - 16) / 2, 184 + (50 - 16) / 2, 16, 16,
               toi_icon_cancel + 12, sizeof(toi_icon_cancel) - 12, COLOR_BL_BG,
               COLOR_BL_FAIL);
  display_bar_radius(123, 184, 108, 50, COLOR_BL_DONE, COLOR_BL_BG, 4);
  display_icon(123 + (108 - 19) / 2, 184 + (50 - 16) / 2, 20, 16,
               toi_icon_confirm + 12, sizeof(toi_icon_confirm) - 12,
               COLOR_BL_BG, COLOR_BL_DONE);
}

static const char *format_ver(const char *format, uint32_t version) {
  static char ver_str[64];
  mini_snprintf(ver_str, sizeof(ver_str), format, (int)(version & 0xFF),
                (int)((version >> 8) & 0xFF), (int)((version >> 16) & 0xFF)
                // ignore build field (int)((version >> 24) & 0xFF)
  );
  return ver_str;
}

// boot UI

static uint16_t boot_background;

void ui_screen_boot(const vendor_header *const vhdr,
                    const image_header *const hdr) {
  const int show_string = ((vhdr->vtrust & VTRUST_STRING) == 0);
  if ((vhdr->vtrust & VTRUST_RED) == 0) {
    boot_background = RGB16(0xFF, 0x00, 0x00);  // red
  } else {
    boot_background = COLOR_BLACK;
  }

  const uint8_t *vimg = vhdr->vimg;
  const uint32_t fw_version = hdr->version;

  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, boot_background);

  int image_top = show_string ? 30 : (DISPLAY_RESY - 120) / 2;

  // check whether vendor image is 120x120
  if (memcmp(vimg, "TOIf\x78\x00\x78\x00", 4) == 0) {
    uint32_t datalen = *(uint32_t *)(vimg + 8);
    display_image((DISPLAY_RESX - 120) / 2, image_top, 120, 120, vimg + 12,
                  datalen);
  }

  if (show_string) {
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 5 - 50, vhdr->vstr,
                        vhdr->vstr_len, FONT_NORMAL, COLOR_BL_BG,
                        boot_background);
    const char *ver_str = format_ver("%d.%d.%d", fw_version);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 5 - 25, ver_str, -1,
                        FONT_NORMAL, COLOR_BL_BG, boot_background);
  }
}

void ui_screen_boot_wait(int wait_seconds) {
  char wait_str[16];
  mini_snprintf(wait_str, sizeof(wait_str), "starting in %d s", wait_seconds);
  display_bar(0, DISPLAY_RESY - 5 - 20, DISPLAY_RESX, 5 + 20, boot_background);
  display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 5, wait_str, -1,
                      FONT_NORMAL, COLOR_BL_BG, boot_background);
}

void ui_screen_boot_click(void) {
  display_bar(0, DISPLAY_RESY - 5 - 20, DISPLAY_RESX, 5 + 20, boot_background);
  display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 5,
                      "click to continue ...", -1, FONT_NORMAL, COLOR_BL_BG,
                      boot_background);
}

// welcome UI

void ui_screen_welcome_first(void) {
  display_icon(0, 0, 240, 240, toi_icon_logo + 12, sizeof(toi_icon_logo) - 12,
               COLOR_WELCOME_FG, COLOR_WELCOME_BG);
}

void ui_screen_welcome_second(void) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WELCOME_BG);
  display_icon((DISPLAY_RESX - 200) / 2, (DISPLAY_RESY - 60) / 2, 200, 60,
               toi_icon_safeplace + 12, sizeof(toi_icon_safeplace) - 12,
               COLOR_WELCOME_FG, COLOR_WELCOME_BG);
}

void ui_screen_welcome_third(void) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WELCOME_BG);
  display_icon((DISPLAY_RESX - 180) / 2, (DISPLAY_RESY - 30) / 2 - 5, 180, 30,
               toi_icon_welcome + 12, sizeof(toi_icon_welcome) - 12,
               COLOR_WELCOME_FG, COLOR_WELCOME_BG);
  display_text_center(120, 220, "Go to trezor.io/start", -1, FONT_NORMAL,
                      COLOR_WELCOME_FG, COLOR_WELCOME_BG);
}

// info UI

static int display_vendor_string(const char *text, int textlen,
                                 uint16_t fgcolor) {
  int split = display_text_split(text, textlen, FONT_NORMAL, DISPLAY_RESX - 55);
  if (split >= textlen) {
    display_text(55, 95, text, textlen, FONT_NORMAL, fgcolor, COLOR_BL_BG);
    return 120;
  } else {
    display_text(55, 95, text, split, FONT_NORMAL, fgcolor, COLOR_BL_BG);
    if (text[split] == ' ') {
      split++;
    }
    display_text(55, 120, text + split, textlen - split, FONT_NORMAL, fgcolor,
                 COLOR_BL_BG);
    return 145;
  }
}

void ui_screen_firmware_info(const vendor_header *const vhdr,
                             const image_header *const hdr) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  const char *ver_str = format_ver("Bootloader %d.%d.%d", VERSION_UINT32);
  display_text(16, 32, ver_str, -1, FONT_NORMAL, COLOR_BL_FG, COLOR_BL_BG);
  display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BL_FG);
  display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12,
               COLOR_BL_GRAY, COLOR_BL_BG);
  if (vhdr && hdr) {
    ver_str = format_ver("Firmware %d.%d.%d by", (hdr->version));
    display_text(55, 70, ver_str, -1, FONT_NORMAL, COLOR_BL_GRAY, COLOR_BL_BG);
    display_vendor_string(vhdr->vstr, vhdr->vstr_len, COLOR_BL_GRAY);
  } else {
    display_text(55, 70, "No Firmware", -1, FONT_NORMAL, COLOR_BL_GRAY,
                 COLOR_BL_BG);
  }
  display_text_center(120, 220, "Go to trezor.io/start", -1, FONT_NORMAL,
                      COLOR_BL_FG, COLOR_BL_BG);
}

void ui_screen_firmware_fingerprint(const image_header *const hdr) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  display_text(16, 32, "Firmware fingerprint", -1, FONT_NORMAL, COLOR_BL_FG,
               COLOR_BL_BG);
  display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BL_FG);

  static const char *hexdigits = "0123456789abcdef";
  char fingerprint_str[64];
  for (int i = 0; i < 32; i++) {
    fingerprint_str[i * 2] = hexdigits[(hdr->fingerprint[i] >> 4) & 0xF];
    fingerprint_str[i * 2 + 1] = hexdigits[hdr->fingerprint[i] & 0xF];
  }
  for (int i = 0; i < 4; i++) {
    display_text_center(120, 70 + i * 25, fingerprint_str + i * 16, 16,
                        FONT_MONO, COLOR_BL_FG, COLOR_BL_BG);
  }

  display_bar_radius(9, 184, 222, 50, COLOR_BL_DONE, COLOR_BL_BG, 4);
  display_icon(9 + (222 - 19) / 2, 184 + (50 - 16) / 2, 20, 16,
               toi_icon_confirm + 12, sizeof(toi_icon_confirm) - 12,
               COLOR_BL_BG, COLOR_BL_DONE);
}

// install UI

void ui_screen_install_confirm_upgrade(const vendor_header *const vhdr,
                                       const image_header *const hdr) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  display_text(16, 32, "Firmware update", -1, FONT_NORMAL, COLOR_BL_FG,
               COLOR_BL_BG);
  display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BL_FG);
  display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12,
               COLOR_BL_FG, COLOR_BL_BG);
  display_text(55, 70, "Update firmware by", -1, FONT_NORMAL, COLOR_BL_FG,
               COLOR_BL_BG);
  int next_y = display_vendor_string(vhdr->vstr, vhdr->vstr_len, COLOR_BL_FG);
  const char *ver_str = format_ver("to version %d.%d.%d?", hdr->version);
  display_text(55, next_y, ver_str, -1, FONT_NORMAL, COLOR_BL_FG, COLOR_BL_BG);
  ui_confirm_cancel_buttons();
}

void ui_screen_install_confirm_newvendor_or_downgrade_wipe(
    const vendor_header *const vhdr, const image_header *const hdr,
    secbool downgrade_wipe) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  display_text(
      16, 32,
      (sectrue == downgrade_wipe) ? "Firmware downgrade" : "Vendor change", -1,
      FONT_NORMAL, COLOR_BL_FG, COLOR_BL_BG);
  display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BL_FG);
  display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12,
               COLOR_BL_FG, COLOR_BL_BG);
  display_text(55, 70, "Install firmware by", -1, FONT_NORMAL, COLOR_BL_FG,
               COLOR_BL_BG);
  int next_y = display_vendor_string(vhdr->vstr, vhdr->vstr_len, COLOR_BL_FG);
  const char *ver_str = format_ver("(version %d.%d.%d)?", hdr->version);
  display_text(55, next_y, ver_str, -1, FONT_NORMAL, COLOR_BL_FG, COLOR_BL_BG);
  display_text_center(120, 170, "Seed will be erased!", -1, FONT_NORMAL,
                      COLOR_BL_FAIL, COLOR_BL_BG);
  ui_confirm_cancel_buttons();
}

void ui_screen_install_start(void) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  display_loader(0, false, -20, COLOR_BL_PROCESS, COLOR_BL_BG, toi_icon_install,
                 sizeof(toi_icon_install), COLOR_BL_FG);
  display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24,
                      "Installing firmware", -1, FONT_NORMAL, COLOR_BL_FG,
                      COLOR_BL_BG);
}

void ui_screen_install_progress_erase(int pos, int len) {
  display_loader(250 * pos / len, false, -20, COLOR_BL_PROCESS, COLOR_BL_BG,
                 toi_icon_install, sizeof(toi_icon_install), COLOR_BL_FG);
}

void ui_screen_install_progress_upload(int pos) {
  display_loader(pos, false, -20, COLOR_BL_PROCESS, COLOR_BL_BG,
                 toi_icon_install, sizeof(toi_icon_install), COLOR_BL_FG);
}

// wipe UI

void ui_screen_wipe_confirm(void) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  display_text(16, 32, "Wipe device", -1, FONT_NORMAL, COLOR_BL_FG,
               COLOR_BL_BG);
  display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BL_FG);
  display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12,
               COLOR_BL_FG, COLOR_BL_BG);
  display_text(55, 70, "Do you want to", -1, FONT_NORMAL, COLOR_BL_FG,
               COLOR_BL_BG);
  display_text(55, 95, "wipe the device?", -1, FONT_NORMAL, COLOR_BL_FG,
               COLOR_BL_BG);

  display_text_center(120, 170, "Seed will be erased!", -1, FONT_NORMAL,
                      COLOR_BL_FAIL, COLOR_BL_BG);
  ui_confirm_cancel_buttons();
}

void ui_screen_wipe(void) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  display_loader(0, false, -20, COLOR_BL_PROCESS, COLOR_BL_BG, toi_icon_wipe,
                 sizeof(toi_icon_wipe), COLOR_BL_FG);
  display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24, "Wiping device", -1,
                      FONT_NORMAL, COLOR_BL_FG, COLOR_BL_BG);
}

void ui_screen_wipe_progress(int pos, int len) {
  display_loader(1000 * pos / len, false, -20, COLOR_BL_PROCESS, COLOR_BL_BG,
                 toi_icon_wipe, sizeof(toi_icon_wipe), COLOR_BL_FG);
}

// done UI

void ui_screen_done(int restart_seconds, secbool full_redraw) {
  const char *str;
  char count_str[24];
  if (restart_seconds >= 1) {
    mini_snprintf(count_str, sizeof(count_str), "Done! Restarting in %d s",
                  restart_seconds);
    str = count_str;
  } else {
    str = "Done! Unplug the device.";
  }
  if (sectrue == full_redraw) {
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  }
  display_loader(1000, false, -20, COLOR_BL_DONE, COLOR_BL_BG, toi_icon_done,
                 sizeof(toi_icon_done), COLOR_BL_FG);
  if (secfalse == full_redraw) {
    display_bar(0, DISPLAY_RESY - 24 - 18, 240, 23, COLOR_BL_BG);
  }
  display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24, str, -1, FONT_NORMAL,
                      COLOR_BL_FG, COLOR_BL_BG);
}

// error UI

void ui_screen_fail(void) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_BL_BG);
  display_loader(1000, false, -20, COLOR_BL_FAIL, COLOR_BL_BG, toi_icon_fail,
                 sizeof(toi_icon_fail), COLOR_BL_FG);
  display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24,
                      "Failed! Please, reconnect.", -1, FONT_NORMAL,
                      COLOR_BL_FG, COLOR_BL_BG);
}

// general functions

void ui_fadein(void) { display_fade(0, BACKLIGHT_NORMAL, 1000); }

void ui_fadeout(void) {
  display_fade(BACKLIGHT_NORMAL, 0, 500);
  display_clear();
}

int ui_user_input(int zones) {
  for (;;) {
    uint32_t evt = touch_click();
    uint16_t x = touch_unpack_x(evt);
    uint16_t y = touch_unpack_y(evt);
    // clicked on Cancel button
    if ((zones & INPUT_CANCEL) && x >= 9 && x < 9 + 108 && y > 184 &&
        y < 184 + 50) {
      return INPUT_CANCEL;
    }
    // clicked on Confirm button
    if ((zones & INPUT_CONFIRM) && x >= 123 && x < 123 + 108 && y > 184 &&
        y < 184 + 50) {
      return INPUT_CONFIRM;
    }
    // clicked on Long Confirm button
    if ((zones & INPUT_LONG_CONFIRM) && x >= 9 && x < 9 + 222 && y > 184 &&
        y < 184 + 50) {
      return INPUT_LONG_CONFIRM;
    }
    // clicked on Info icon
    if ((zones & INPUT_INFO) && x >= 16 && x < 16 + 32 && y > 54 &&
        y < 54 + 32) {
      return INPUT_INFO;
    }
  }
}
