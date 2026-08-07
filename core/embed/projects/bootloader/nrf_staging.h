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

#if defined(PQ_SECURE_BOOT) && defined(USE_SMP)

#include <sec/boot_header.h>  // merkle_proof_node_t, MODEL_TREE_MAX_PROOF_NODES

// Persistent staging for the deferred (phase-2) nRF push.
//
// On a BLE-only device the nRF cannot be pushed during a host connection (the
// push reboots the nRF into DFU, which IS the BLE link), so the image is only
// STAGED while the host is connected and PUSHED autonomously by the next
// bootloader boot -- which is also what makes an interrupted update resumable.
// See docs / the coproc-ota design.
//
// Layout inside NRF_STAGING_AREA (firmware-region front, survives the
// bootloader-swap reboot): the raw nRF image streams at offset 0; a descriptor
// occupies the LAST sector. The descriptor is written LAST, as the validity
// commit, so a half-staged image never presents as valid.
//
// The descriptor persists only what cannot be re-derived from the staged image:
// the nRF leaf's co-path (its Merkle siblings). The MCUboot SHA-256
// (idempotency check) and the model id are read back from the image itself at
// push time. The descriptor is NOT a trust input -- the resume driver re-folds
// the image to the installed boot header's modelRoot and re-checks the model id
// regardless; the tag only detects a torn write and bounds image_len before
// use.

// Largest nRF image (bytes) that may be staged: the area minus the reserved
// descriptor sector. Runtime value (depends on the flash sector size).
uint32_t nrf_staging_image_capacity(void);

// Memory-mapped pointer to the staged nRF image (offset 0), or NULL if
// `image_len` is out of range.
const uint8_t *nrf_staging_image(uint32_t image_len);

// Write the descriptor as the FINAL validity commit. Call only after the image
// is fully staged into NRF_STAGING_AREA@0 and fold-verified. `image_len` must
// be
// <= nrf_staging_image_capacity() and `co_path_count` <=
// MODEL_TREE_MAX_PROOF_NODES.
secbool nrf_staging_write_desc(uint32_t image_len,
                               const merkle_proof_node_t *co_path,
                               size_t co_path_count);

// True iff a structurally-valid descriptor is present (magic + version + bounds
// + integrity tag). Cheap: a single mapped read of the descriptor sector, so it
// is a safe no-op probe on every boot.
bool nrf_staging_valid(void);

// Read the validated descriptor. Returns false if none is valid. `out_co_path`
// points into memory-mapped flash (stable, read-only) and is valid until the
// staging area is erased.
bool nrf_staging_read(uint32_t *out_image_len,
                      const merkle_proof_node_t **out_co_path,
                      size_t *out_co_path_count);

// Invalidate the staged descriptor (erases its sector). The image bytes are
// left in place (inert without a valid descriptor; overwritten by the next
// stage). Idempotent.
secbool nrf_staging_clear(void);

#endif  // PQ_SECURE_BOOT && USE_SMP
