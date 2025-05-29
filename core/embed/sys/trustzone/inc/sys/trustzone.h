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

// Initializes the TrustZone subsystem for current firmware layer.
void tz_init(void);

// Alignment required by MCPBB/GTZC for SRAM regions
#define TZ_SRAM_ALIGNMENT 512

// Sets/Resets unprivileged access to an SRAM address range at the
// MCPBB/GTZC level. The region's start and end are automatically aligned to
// 512B to cover the entire specified range.
void tz_set_sram_unpriv(uint32_t start, uint32_t size, bool unpriv);

// Sets/Resets non-secure access to an SRAM address range at the
// MCPBB/GTZC level. The region's start and end are automatically aligned to
// 512B to cover the entire specified range.
void tz_set_sram_unsecure(uint32_t start, uint32_t size, bool unsecure);

// Alignment required by GTZC for FLASH regions
#define TZ_FLASH_ALIGNMENT 8192

// Sets/resets unprivileged access to a FLASH address range at the
// MCPBB/GTZC level. The region's start and end are automatically aligned to
// 8KB to cover the entire specified range.
void tz_set_flash_unpriv(uint32_t start, uint32_t size, bool unpriv);

// Sets/resets non-secure access to a FLASH address range at the
// MCPBB/GTZC level. The region's start and end are automatically aligned to
// 8KB to cover the entire specified range.
void tz_set_flash_unsecure(uint32_t start, uint32_t size, bool unsecure);

// Sets unprivileged access to the SAES peripheral.
void tz_set_saes_unpriv(bool unpriv);

// Sets unprivileged access to the TAMP peripheral.
void tz_set_tamper_unpriv(bool unpriv);

// Sets unprivileged access to the GFXMMU peripheral.
void tz_set_gfxmmu_unpriv(bool unpriv);
