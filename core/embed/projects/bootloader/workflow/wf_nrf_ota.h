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

// Upper bound on the nRF model-tree co-path (in 32-byte nodes), bounding the
// untrusted co_path_len from FirmwareBegin.

// FirmwareRequest.coprocessor_index value the nRF stream uses (0 = the primary
// bootloader-code / firmware stream). Lets the host tell a phase-1 bl-code
// request from an nRF request when both stream in one session.
#define NRF_OTA_REQUEST_INDEX 1

/**
 * nRF (BLE co-processor) firmware OTA, driven by the nRF fields of
 * FirmwareBegin (phase 1). The nRF MCUboot image is a model-level leaf in the
 * founder tree, covered by THIS boot header's ONE signature -- there is no
 * separate nRF signature. Done by the CURRENT bootloader while it still
 * provides the (BLE) host link -- see the transport reasoning in
 * wf_firmware_update_pq.c. The bootloader:
 *   1. skips if the running nRF already matches `image_hash` (best-effort
 * hint);
 *   2. otherwise streams the image into NRF_STAGING_AREA (non-secure firmware
 *      scratch, capped short of STAGING_AREA so it can't erase the staged
 *      bootloader);
 *   3. founder-verifies it: leaf = H(0x00 || image) folded through `co_path`
 *      must equal `model_root`, AND the image's model-id TLV must equal THIS
 *      device (cross-model guard -- every model's nRF shares modelRoot);
 *   4. SMP-pushes the raw image to the nRF, whose own MCUboot Ed25519 check is
 *      the authoritative post-upload gate.
 *
 * @param iface        Protobuf I/O (also used to send failure messages).
 * @param model_root   The signature-verified modelRoot the boot header commits
 *                     to (from ucb_stage_verify). The nRF leaf is a peer under
 * it.
 * @param co_path      nRF leaf's model co-path, `co_path_len` bytes (multiple
 * of 32).
 * @param co_path_len  Length of `co_path` in bytes.
 * @param image_hash   SHA-256 of the offered nRF image (update-required hint);
 *                     may be NULL / `image_hash_len` 0 to always stream.
 * @param image_hash_len Length of `image_hash` (32 or 0).
 * @param nrf_length   Offered nRF image size in bytes (> 0).
 * @return WF_OK on success (including "already up to date, skipped"); WF_ERROR
 *         on any validation / transport failure (a wire Failure + fail screen
 *         are emitted first).
 */
workflow_result_t workflow_nrf_ota_update(
    protob_io_t *iface, const merkle_proof_node_t *model_root,
    const uint8_t *co_path, size_t co_path_len, const uint8_t *image_hash,
    size_t image_hash_len, uint32_t nrf_length);

/**
 * Boot-time deferred nRF push -- the autonomous, phase-2 half of a coupled
 * boot+nRF update. Call once on every bootloader boot, BEFORE any host/BLE data
 * transfer.
 *
 * A no-op unless a valid staged descriptor is present (nrf_staging_valid).
 * Otherwise it:
 *   1. re-verifies the staged image against the INSTALLED boot header's
 *      modelRoot (the authority after any bootloader swap) + model id, and
 *      DISCARDS a stale/aborted/foreign staging that does not fold (then boots
 *      normally);
 *   2. idempotently pushes the image to the nRF over the link-independent GPIO
 *      serial-recovery path (skipping if the live nRF already matches), driving
 *      the install progress bar;
 *   3. on success clears the staging; on a persistent push failure keeps the
 *      staging (so a power-cycle retries) and halts rather than continue to BLE
 *      with an incompatible co-processor.
 *
 * This is what makes an interrupted coupled update resumable and is mandatory
 * on a BLE-only device, where the push cannot run during a host connection (it
 * reboots the nRF, which IS the BLE link). See nrf_staging.h / the coproc-ota
 * design.
 */
void nrf_ota_resume_boot(void);

#endif  // PQ_SECURE_BOOT && USE_SMP
