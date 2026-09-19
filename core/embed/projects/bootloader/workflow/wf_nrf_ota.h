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

#include <sec/boot_header.h>

#include "protob/protob.h"
#include "workflow_common.h"

// FirmwareRequest.coprocessor_index of the nRF stream (0 = primary stream).
#define NRF_OTA_REQUEST_INDEX 1

/**
 * Phase-1 nRF OTA: fold-verifies the offered image hash, streams the image
 * into NRF_STAGING_AREA, verifies it against `model_root` and stages it for
 * the boot-time push (nrf_ota_resume_boot). Emits its own Failure + fail
 * screen on error.
 *
 * @param model_root     signature-verified modelRoot (from ucb_stage_verify)
 * @param co_path        nRF leaf co-path, `co_path_len` bytes (multiple of 32)
 * @param image_hash     SHA-256 update-required hint; NULL / len 0 = no hint
 * @param image_hash_len 32 or 0; anything else is rejected
 * @param nrf_length     offered image size in bytes (> 0)
 * @return WF_OK (including "already up to date"), WF_ERROR otherwise
 */
workflow_result_t workflow_nrf_ota_update(
    protob_io_t *iface, const merkle_proof_node_t *model_root,
    const uint8_t *co_path, size_t co_path_len, const uint8_t *image_hash,
    size_t image_hash_len, uint32_t nrf_length);

/**
 * Boot-time deferred nRF push; call on every boot before any host/BLE traffic.
 * No-op without a valid staged descriptor. Re-verifies the staged image
 * against the installed boot header (discarding a stale staging), pushes it
 * idempotently, clears the staging on success and halts on persistent failure.
 */
void nrf_ota_resume_boot(void);

#endif  // PQ_SECURE_BOOT && USE_SMP
