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

#pragma once

#include <trezor_types.h>

#include <util/image.h>

// todo: use bindgen to tie this to rust
typedef enum {
  UI_RESULT_CANCEL = 1,
  UI_RESULT_CONFIRM = 2,
} ui_result_t;

// todo: use bindgen to tie this to rust
typedef enum {
  MENU_EXIT = 0xAABBCCDD,
  MENU_REBOOT = 0x11223344,
  MENU_WIPE = 0x55667788,
} menu_result_t;

// todo: use bindgen to tie this to rust
typedef enum {
  INTRO_MENU = 1,
  INTRO_HOST = 2,
} intro_result_t;

// Displays a warning screen before jumping to the untrusted firmware
//
// Shows vendor image, vendor string and firmware version
// and optional message to the user (see `wait` argument)
//
// `wait` argument specifies a message to the user
//   0 do not show any message
//   > 0 show a message like "starting in %d s"
//   < 0 show a message like "press button to continue"
void ui_screen_boot(const vendor_header* const vhdr,
                    const image_header* const hdr, int wait);

// Waits until the user confirms the untrusted firmware
//
// Implementation is device specific - it wait's until
// the user presses a button, touches the display
void ui_click(void);

void ui_screen_welcome(void);

uint32_t ui_screen_intro(const vendor_header* const vhdr,
                         const image_header* const hdr, bool fw_ok);

uint32_t ui_screen_menu(secbool firmware_present);

void ui_screen_connect(void);

ui_result_t ui_screen_install_confirm(const vendor_header* const vhdr,
                                      const image_header* const hdr,
                                      secbool shold_keep_seed,
                                      secbool is_newvendor,
                                      secbool is_newinstall, int version_cmp);
void ui_screen_install_start();
void ui_screen_install_progress_erase(int pos, int len);
void ui_screen_install_progress_upload(int pos);

ui_result_t ui_screen_wipe_confirm(void);
void ui_screen_wipe(void);
void ui_screen_wipe_progress(int pos, int len);

void ui_screen_done(uint8_t restart_seconds, secbool full_redraw);

void ui_screen_fail(void);

void ui_fadein(void);
void ui_fadeout(void);
void ui_set_initial_setup(bool initial);

void ui_screen_boot_stage_1(bool fading);

#ifdef USE_OPTIGA
uint32_t ui_screen_unlock_bootloader_confirm(void);
#endif
