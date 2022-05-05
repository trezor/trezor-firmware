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
#include "version.h"

#include "screens_rust.h"

#if defined TREZOR_MODEL_T
#include "touch.h"
#elif defined TREZOR_MODEL_R
#include "button.h"
#else
#error Unknown Trezor model
#endif

#define BACKLIGHT_NORMAL 150

#define COLOR_BL_BG COLOR_WHITE  // background
#define COLOR_BL_FG COLOR_BLACK  // foreground

#ifdef RGB16
#define COLOR_BL_FAIL RGB16(0xFF, 0x00, 0x00)     // red
#define COLOR_BL_DONE RGB16(0x00, 0xAE, 0x0B)     // green
#define COLOR_BL_PROCESS RGB16(0x4A, 0x90, 0xE2)  // blue
#define COLOR_BL_GRAY RGB16(0x99, 0x99, 0x99)     // gray
#else
#define COLOR_BL_FAIL COLOR_BL_FG
#define COLOR_BL_DONE COLOR_BL_FG
#define COLOR_BL_PROCESS COLOR_BL_FG
#define COLOR_BL_GRAY COLOR_BL_FG
#endif

#define COLOR_WELCOME_BG COLOR_WHITE  // welcome background
#define COLOR_WELCOME_FG COLOR_BLACK  // welcome foreground

// common shared functions

static void format_ver_bfr(const char *format, uint32_t version, char *bfr,
                           size_t bfr_len) {
  mini_snprintf(bfr, bfr_len, format, (int)(version & 0xFF),
                (int)((version >> 8) & 0xFF), (int)((version >> 16) & 0xFF)
                // ignore build field (int)((version >> 24) & 0xFF)
  );
}

static const char *format_ver(const char *format, uint32_t version) {
  static char ver_str[64];
  format_ver_bfr(format, version, ver_str, sizeof(ver_str));
  return ver_str;
}

// boot UI

static uint16_t boot_background;

void ui_screen_boot(const vendor_header *const vhdr,
                    const image_header *const hdr) {
  const int show_string = ((vhdr->vtrust & VTRUST_STRING) == 0);
  if ((vhdr->vtrust & VTRUST_RED) == 0) {
    boot_background = COLOR_BL_FAIL;
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

uint32_t ui_screen_intro(const vendor_header *const vhdr,
                         const image_header *const hdr) {
  char bld_ver[32];
  format_ver_bfr("%d.%d.%d", VERSION_UINT32, bld_ver, sizeof(bld_ver));
  const char *ver_str = format_ver("Firmware %d.%d.%d by", hdr->version);
  return screen_intro(bld_ver, vhdr->vstr, vhdr->vstr_len, ver_str);
}

uint32_t ui_screen_menu(void) {
  char bld_ver[32];
  format_ver_bfr("%d.%d.%d", VERSION_UINT32, bld_ver, sizeof(bld_ver));
  return screen_menu(bld_ver);
}

uint32_t ui_screen_firmware_fingerprint(const image_header *const hdr) {
  static const char *hexdigits = "0123456789abcdef";
  char fingerprint_str[64];
  for (int i = 0; i < 32; i++) {
    fingerprint_str[i * 2] = hexdigits[(hdr->fingerprint[i] >> 4) & 0xF];
    fingerprint_str[i * 2 + 1] = hexdigits[hdr->fingerprint[i] & 0xF];
  }
  return screen_fwinfo(fingerprint_str);
}

// install UI

uint32_t ui_screen_install_confirm_upgrade(const vendor_header *const vhdr,
                                           const image_header *const hdr) {
  const char *ver_str = format_ver("to version %d.%d.%d?", hdr->version);
  return screen_install_confirm(vhdr->vstr, vhdr->vstr_len, ver_str, false,
                                false);
}

uint32_t ui_screen_install_confirm_newvendor_or_downgrade_wipe(
    const vendor_header *const vhdr, const image_header *const hdr,
    secbool downgrade_wipe) {
  const char *ver_str = format_ver("version %d.%d.%d?", hdr->version);
  return screen_install_confirm(vhdr->vstr, vhdr->vstr_len, ver_str,
                                downgrade_wipe, !downgrade_wipe);
}

void ui_screen_install_start(void) {
  screen_progress("Installing firmware...", 0, true);
}

void ui_screen_install_progress_erase(int pos, int len) {
  screen_progress("Installing firmware...", 250 * pos / len, false);
}

void ui_screen_install_progress_upload(int pos) {
  screen_progress("Installing firmware...", pos, false);
}

// wipe UI

uint32_t ui_screen_wipe_confirm(void) { return screen_wipe_confirm(); }

void ui_screen_wipe(void) { screen_progress("Wiping device...", 0, true); }

void ui_screen_wipe_progress(int pos, int len) {
  screen_progress("Wiping device...", 1000 * pos / len, false);
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
