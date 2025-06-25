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

#define PQ_SIGNATURE_LEN 7856

/**
 * Signature/upgrade block footer, reserved for the upgrade process
 * and not included in the signing process.
 */
typedef struct {
  // Pointer to the bootloader image in flash
  void* bootloader_image;
  uint8_t reserved[28];
} bootheader_dyn_t;

/**
 * Structure of boot header
 */
typedef struct {
  uint8_t reserved[640];
  uint8_t signature1[PQ_SIGNATURE_LEN];
  uint8_t signature2[PQ_SIGNATURE_LEN];
  bootheader_dyn_t dyn;
} bootheader_t;
