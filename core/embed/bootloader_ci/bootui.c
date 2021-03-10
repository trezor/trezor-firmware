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
#include "icon_done.h"
#include "icon_fail.h"
#include "icon_install.h"
#include "icon_welcome.h"
#include "icon_wipe.h"
#include "mini_printf.h"

#define BACKLIGHT_NORMAL 150

#define COLOR_BL_BG COLOR_WHITE                   // background
#define COLOR_BL_FG COLOR_BLACK                   // foreground
#define COLOR_BL_FAIL RGB16(0xFF, 0x00, 0x00)     // red
#define COLOR_BL_DONE RGB16(0x00, 0xAE, 0x0B)     // green
#define COLOR_BL_PROCESS RGB16(0x4A, 0x90, 0xE2)  // blue

#define COLOR_WELCOME_BG COLOR_WHITE  // welcome background
#define COLOR_WELCOME_FG COLOR_BLACK  // welcome foreground

// welcome UI

void ui_screen_welcome_third(void) {
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WELCOME_BG);
  display_icon((DISPLAY_RESX - 180) / 2, (DISPLAY_RESY - 30) / 2 - 5, 180, 30,
               toi_icon_welcome + 12, sizeof(toi_icon_welcome) - 12,
               COLOR_WELCOME_FG, COLOR_WELCOME_BG);
  display_text_center(120, 220, "Go to trezor.io/start", -1, FONT_NORMAL,
                      COLOR_WELCOME_FG, COLOR_WELCOME_BG);
}

// install UI

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
