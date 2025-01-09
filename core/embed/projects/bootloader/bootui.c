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

#include <trezor_rtl.h>

#include <gfx/fonts.h>
#include <io/display.h>
#include <io/display_utils.h>
#include <rtl/mini_printf.h>
#include "bootui.h"
#include "rust_ui.h"
#include "version.h"

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

#if !defined TREZOR_MODEL_T2B1 && !defined TREZOR_MODEL_T3B1
#define BOOT_WAIT_HEIGHT 25
#define BOOT_WAIT_Y_TOP (DISPLAY_RESY - BOOT_WAIT_HEIGHT)
#else
#define BOOT_WAIT_HEIGHT 12
#define BOOT_WAIT_Y_TOP (DISPLAY_RESY - BOOT_WAIT_HEIGHT)
#endif

#define TOIF_LENGTH(ptr) ((*(uint32_t *)((ptr) + 8)) + 12)

// common shared functions

static void format_ver(const char *format, uint32_t version, char *buffer,
                       size_t buffer_len) {
  mini_snprintf(buffer, buffer_len, format, (int)(version & 0xFF),
                (int)((version >> 8) & 0xFF), (int)((version >> 16) & 0xFF)
                // ignore build field (int)((version >> 24) & 0xFF)
  );
}

// boot UI

static bool initial_setup = true;

void ui_set_initial_setup(bool initial) { initial_setup = initial; }

#if defined USE_TOUCH
#include <io/touch.h>

void ui_click(void) {
  // flush touch events if any
  while (touch_get_event()) {
  }
  // wait for TOUCH_START
  while ((touch_get_event() & TOUCH_START) == 0) {
  }
  // wait for TOUCH_END
  while ((touch_get_event() & TOUCH_END) == 0) {
  }
  // flush touch events if any
  while (touch_get_event()) {
  }
}

#elif defined USE_BUTTON
#include <io/button.h>

void ui_click(void) {
  for (;;) {
    button_get_event();
    if (button_is_down(BTN_LEFT) && button_is_down(BTN_RIGHT)) {
      break;
    }
  }
  for (;;) {
    button_get_event();
    if (!button_is_down(BTN_LEFT) && !button_is_down(BTN_RIGHT)) {
      break;
    }
  }
}

#else
#error "No input method defined"
#endif

void ui_screen_boot(const vendor_header *const vhdr,
                    const image_header *const hdr, int wait) {
  bool show_string = ((vhdr->vtrust & VTRUST_NO_STRING) == 0);
  const char *vendor_str = show_string ? vhdr->vstr : NULL;
  const size_t vendor_str_len = show_string ? vhdr->vstr_len : 0;
  bool red_screen = ((vhdr->vtrust & VTRUST_NO_RED) == 0);
  uint32_t vimg_len = TOIF_LENGTH(vhdr->vimg);

  screen_boot(red_screen, vendor_str, vendor_str_len, hdr->version, vhdr->vimg,
              vimg_len, wait);
}

// welcome UI

void ui_screen_welcome(void) { screen_welcome(); }

uint32_t ui_screen_intro(const vendor_header *const vhdr,
                         const image_header *const hdr, bool fw_ok) {
  char bld_ver[32];
  char ver_str[64];
  format_ver("%d.%d.%d", VERSION_UINT32, bld_ver, sizeof(bld_ver));
  format_ver("%d.%d.%d", hdr->version, ver_str, sizeof(ver_str));

  return screen_intro(bld_ver, vhdr->vstr, vhdr->vstr_len, ver_str, fw_ok);
}

uint32_t ui_screen_menu(secbool firmware_present) {
  return screen_menu(firmware_present);
}

// install UI

uint32_t ui_screen_install_confirm(const vendor_header *const vhdr,
                                   const image_header *const hdr,
                                   secbool should_keep_seed,
                                   secbool is_newvendor, secbool is_newinstall,
                                   int version_cmp) {
  uint8_t fingerprint[32];
  char ver_str[64];
  get_image_fingerprint(hdr, fingerprint);
  format_ver("%d.%d.%d", hdr->version, ver_str, sizeof(ver_str));
  return screen_install_confirm(vhdr->vstr, vhdr->vstr_len, ver_str,
                                fingerprint, should_keep_seed == sectrue,

                                is_newvendor == sectrue,
                                is_newinstall == sectrue, version_cmp);
}

void ui_screen_install_start() {
  screen_install_progress(0, true, initial_setup);
}

void ui_screen_install_progress_erase(int pos, int len) {
  screen_install_progress(250 * pos / len, false, initial_setup);
}

void ui_screen_install_progress_upload(int pos) {
  screen_install_progress(pos, false, initial_setup);
}

// wipe UI

uint32_t ui_screen_wipe_confirm(void) { return screen_wipe_confirm(); }

void ui_screen_wipe(void) { screen_wipe_progress(0, true); }

void ui_screen_wipe_progress(int pos, int len) {
  screen_wipe_progress(1000 * pos / len, false);
}

// done UI
void ui_screen_done(uint8_t restart_seconds, secbool full_redraw) {
  screen_install_success(restart_seconds, initial_setup, full_redraw);
}

void ui_screen_boot_stage_1(bool fading) { screen_boot_stage_1(fading); }

// error UI
void ui_screen_fail(void) { screen_install_fail(); }

#ifdef USE_OPTIGA
uint32_t ui_screen_unlock_bootloader_confirm(void) {
  return screen_unlock_bootloader_confirm();
}
#else
void ui_screen_install_restricted(void) { screen_install_fail(); }
#endif

// general functions

void ui_fadein(void) { display_fade(0, BACKLIGHT_NORMAL, 1000); }

void ui_fadeout(void) { display_fade(BACKLIGHT_NORMAL, 0, 500); }
