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

#ifndef TREZORHAL_NFC_H
#define TREZORHAL_NFC_H

#include <trezor_bsp.h>
#include <trezor_rtl.h>

typedef enum {
  NFC_OK,
  NFC_ERROR,
  NFC_NOT_INITIALIZED,
  NFC_SPI_BUS_ERROR,
  NFC_INITIALIZATION_FAILED,
} nfc_status_t;

nfc_status_t nfc_init();

nfc_status_t nfc_deinit();

void nfc_poll_type_A();

#endif  // TREZORHAL_NFC_H
