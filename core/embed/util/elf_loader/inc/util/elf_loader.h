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

#include <sys/applet.h>

#ifdef TREZOR_EMULATOR

/**
 * Loads an ELF image using the system dynamic loader.
 *
 * @param applet Pointer to the applet_t structure to be initialized
 * @param filename Path to the ELF file to be loaded
 * @return true on success, false on failure
 */
bool elf_load(applet_t* applet, const char* filename);

#else

/**
 * Loads an ELF image
 *
 * Only ELF files with the specific properties are supported
 *
 * @param elf_ptr Pointer to the ELF image in flash
 * @param elf_size Size of the ELF image in bytes
 * @param ram_ptr Pointer to RAM area for RW segment
 * @param ram_size Size of the RAM area in bytes
 * @param applet Pointer to the applet_t structure to be initialized
 *
 * @return true on success, false on failure
 */
bool elf_load(const void* elf_ptr, size_t elf_size, void* ram_ptr,
              size_t ram_size, applet_t* applet);

#endif
