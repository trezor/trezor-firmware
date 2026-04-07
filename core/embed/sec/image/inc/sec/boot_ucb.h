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

#include <sec/boot_header.h>
#include <sec/image_hash_conf.h>

/**
 * Update control block structure sitting on fixed address in flash memory
 */
typedef struct {
  /** Magic constant checked in boardloader */
  uint32_t magic;
  /** Address of the start of the header structure */
  uint32_t header_address;
  /** Address of the start of the bootloader code in flash memory */
  uint32_t code_address;
  /** Padding to align the structure to 16-bytes */
  uint32_t padding;
  /** Hash of the boot header
   * This is used to verify that the boot header has not changed
   * since the UCB was written. */
  uint8_t hash[IMAGE_HASH_DIGEST_LENGTH];

} boot_ucb_t;

/**
 * Reads the update control block from flash memory, checks its integrity and
 * copies it to the provided structure.
 *
 * @param ucb Pointer to the boot update control block structure to be filled
 * @return sectrue if the read was successful and the update control block is
 *         valid, secfalse otherwise.
 */

secbool boot_ucb_read(boot_ucb_t* ucb);

/**
 * Writes to the update control block in flash memory.
 *
 * This function is called by the code that updates the bootloader
 * or the bootloader header. Before calling this function, the updater must
 * store the bootloader header and code in flash memory.
 *
 * @param header_address Address of the start of the boot header in flash
 *        memory. This parameter is mandatory.
 * @param code_address Address of the start of the bootloader code in flash
 *        memory. If the code is not present, it is expected that only the
 *        header will be updated and this parameter should be set to 0.
 * @return sectrue if the write was successful, secfalse otherwise.
 */
secbool boot_ucb_write(uint32_t header_address, uint32_t code_address);

/**
 * Erases the update control block in flash memory.
 *
 * This function is called by the bootloader to finalize
 * the update process and to ensure that the boardloader will not
 * repeat the update process if it was already done.
 *
 * @return sectrue if the erase was successful, secfalse otherwise.
 */
secbool boot_ucb_erase(void);
