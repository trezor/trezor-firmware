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

/**
 * Loads and initializes a TAPP image.
 *
 * @param applet Pointer to the applet_t structure to be initialized
 * @param elf_ptr Pointer to the pointer to the TAPP image in memory
 * @param elf_size Size of the TAPP image in memory
 * @return true on success, false on failure
 */
bool tapp_load(applet_t* applet, const void* img_ptr, size_t img_size);
