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

// Persistent staging for the deferred nRF push (nrf_ota_resume_boot).
// Layout in NRF_STAGING_AREA: raw image at offset 0, descriptor (co-path only)
// in the last sector, written last as the validity commit. The descriptor is
// not a trust input; the resume driver re-folds the image regardless.

// Largest stageable image: the area minus the descriptor sector.
uint32_t nrf_staging_image_capacity(void);

// Memory-mapped staged image, or NULL if `image_len` is out of range.
const uint8_t *nrf_staging_image(uint32_t image_len);

// Write the descriptor; call only after the image is staged and verified.
secbool nrf_staging_write_desc(uint32_t image_len,
                               const merkle_proof_node_t *co_path,
                               size_t co_path_count);

// Read the validated descriptor; `out_co_path` points into flash.
bool nrf_staging_read(uint32_t *out_image_len,
                      const merkle_proof_node_t **out_co_path,
                      size_t *out_co_path_count);

// Erase the descriptor sector (image bytes left in place). Idempotent.
secbool nrf_staging_clear(void);

#endif  // PQ_SECURE_BOOT && USE_SMP
