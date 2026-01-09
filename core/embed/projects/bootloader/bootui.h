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

#include <sec/image.h>

#include "rust_ui_bootloader.h"

#ifdef TREZOR_MODEL_T3W1
#define BACKLIGHT_NORMAL 155
#define BACKLIGHT_LOW 116
#else
#define BACKLIGHT_NORMAL 150
#define BACKLIGHT_LOW 45
#endif

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

uint32_t ui_screen_intro(const vendor_header* const vhdr,
                         const image_header* const hdr, bool fw_ok);

confirm_result_t ui_screen_install_confirm(const vendor_header* const vhdr,
                                           const image_header* const hdr,
                                           secbool shold_keep_seed,
                                           secbool is_newvendor,
                                           secbool is_newinstall,
                                           int version_cmp);
void ui_screen_install_start(bool wireless);
void ui_screen_install_progress_erase(int pos, int len, bool wireless);
void ui_screen_install_progress_upload(int pos, bool wireless);

confirm_result_t ui_screen_wipe_confirm(void);
void ui_screen_wipe(void);
void ui_screen_wipe_progress(int pos, int len);

void ui_screen_done(uint8_t restart_seconds, secbool full_redraw);

void ui_screen_fail(void);

void ui_fadein(void);
void ui_fadeout(void);
void ui_set_initial_setup(bool initial);
bool ui_get_initial_setup(void);

void ui_screen_boot_stage_1(bool fading);

#ifdef LOCKABLE_BOOTLOADER
uint32_t ui_screen_unlock_bootloader_confirm(void);
#endif

#ifdef USE_BLE
uint32_t ui_screen_confirm_pairing(uint32_t code);
#endif
