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

// OTP blocks allocation
#define FLASH_OTP_BLOCK_BATCH 0
#define FLASH_OTP_BLOCK_BOOTLOADER_VERSION 1
#define FLASH_OTP_BLOCK_VENDOR_HEADER_LOCK 2
#define FLASH_OTP_BLOCK_RANDOMNESS 3
#define FLASH_OTP_BLOCK_DEVICE_VARIANT 4
#define FLASH_OTP_BLOCK_FIRMWARE_VERSION 5
