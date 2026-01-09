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

#include <trezor_model.h>

#include <sec/boot_image.h>

#define CONCAT_NAME_HELPER(prefix, name, suffix) prefix##name##suffix
#define CONCAT_NAME(name, var) CONCAT_NAME_HELPER(BOOTLOADER_, name, var)

#if BOOTLOADER_QA
// QA bootloaders
#define BOOTLOADER_00 CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _QA_00)
#define BOOTLOADER_FF CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _QA_FF)
#else
// normal bootloaders
#define BOOTLOADER_00 CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _00)
#define BOOTLOADER_FF CONCAT_NAME(MODEL_INTERNAL_NAME_TOKEN, _FF)
#endif

// symbols from bootloader.bin => bootloader.o
extern const void bootloader_start;
extern const void bootloader_size;
extern const void bootloader_size;

static const boot_image_t g_bootloader_image = {
    .image_ptr = (const void *)&bootloader_start,
    .image_size = (size_t)&bootloader_size,
#ifndef USE_BOOT_UCB
    .hash_00 = BOOTLOADER_00,
    .hash_FF = BOOTLOADER_FF,
#endif
};

const boot_image_t *boot_image_get_embdata(void) { return &g_bootloader_image; }
