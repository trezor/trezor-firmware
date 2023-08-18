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

#ifndef __BOOTUI_H__
#define __BOOTUI_H__

#include "image.h"
#include "secbool.h"
#include "stdbool.h"
#include TREZOR_BOARD

typedef enum {
  SCREEN_INTRO = 0,
  SCREEN_MENU = 1,
  SCREEN_WIPE_CONFIRM = 2,
  SCREEN_FINGER_PRINT = 3,
  SCREEN_WAIT_FOR_HOST = 4,
} screen_t;

void ui_screen_boot(const vendor_header* const vhdr,
                    const image_header* const hdr);
void ui_screen_boot_wait(int wait_seconds);
void ui_screen_boot_click(void);
void ui_click(void);

void ui_screen_welcome(void);

uint32_t ui_screen_intro(const vendor_header* const vhdr,
                         const image_header* const hdr);

uint32_t ui_screen_menu(void);

uint32_t ui_screen_install_confirm(const vendor_header* const vhdr,
                                   const image_header* const hdr,
                                   secbool shold_keep_seed,
                                   secbool is_newvendor, int version_cmp);
void ui_screen_install_start();
void ui_screen_install_progress_erase(int pos, int len);
void ui_screen_install_progress_upload(int pos);

uint32_t ui_screen_wipe_confirm(void);
void ui_screen_wipe(void);
void ui_screen_wipe_progress(int pos, int len);

void ui_screen_done(uint8_t restart_seconds, secbool full_redraw);

void ui_screen_fail(void);

void ui_fadein(void);
void ui_fadeout(void);
void ui_set_initial_setup(bool initial);

void ui_screen_boot_empty(bool fading);

#ifdef USE_OPTIGA
uint32_t ui_screen_unlock_bootloader_confirm(void);
#endif

// clang-format off
#define INPUT_CANCEL 0x01        // Cancel button
#define INPUT_CONFIRM 0x02       // Confirm button
#define INPUT_LONG_CONFIRM 0x04  // Long Confirm button
#define INPUT_INFO 0x08          // Info icon
// clang-format on

#endif
