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

#include <trezor_rtl.h>

#if defined(PQ_SECURE_BOOT) && defined(USE_SMP)

#include <sys/flash.h>
#include <sys/flash_utils.h>

#include "sha2.h"

#include "nrf_staging.h"

#define NRF_STAGING_DESC_MAGIC 0x5346524E  // "NRFS"
#define NRF_STAGING_DESC_VERSION 1

// The descriptor persisted in the LAST sector of NRF_STAGING_AREA. `tag` is a
// SHA-256 over every preceding field and detects a torn write; it is NOT a
// trust input (the resume driver re-folds the image to the modelRoot
// regardless).
typedef struct {
  uint32_t magic;
  uint32_t version;
  uint32_t image_len;
  uint32_t co_path_count;
  merkle_proof_node_t co_path[MODEL_TREE_MAX_PROOF_NODES];
  uint8_t tag[SHA256_DIGEST_LENGTH];
} nrf_staging_desc_t;

static uint32_t nrf_staging_sector_size(void) {
  uint16_t sectors = flash_area_total_sectors(&NRF_STAGING_AREA);
  return (sectors != 0) ? flash_area_get_size(&NRF_STAGING_AREA) / sectors : 0;
}

// Byte offset of the reserved descriptor sector (the last sector of the area).
static uint32_t nrf_staging_desc_offset(void) {
  return flash_area_get_size(&NRF_STAGING_AREA) - nrf_staging_sector_size();
}

uint32_t nrf_staging_image_capacity(void) {
  // The image occupies [0, desc_offset); the last sector holds the descriptor.
  return nrf_staging_desc_offset();
}

const uint8_t *nrf_staging_image(uint32_t image_len) {
  if (image_len == 0 || image_len > nrf_staging_image_capacity()) {
    return NULL;
  }
  return (const uint8_t *)flash_area_get_address(&NRF_STAGING_AREA, 0,
                                                 image_len);
}

// SHA-256 over the descriptor up to (not including) the `tag` field.
static void nrf_staging_compute_tag(const nrf_staging_desc_t *desc,
                                    uint8_t out[SHA256_DIGEST_LENGTH]) {
  sha256_Raw((const uint8_t *)desc, offsetof(nrf_staging_desc_t, tag), out);
}

// Memory-mapped descriptor pointer if a structurally-valid descriptor is
// present, NULL otherwise. Bounds `image_len` / `co_path_count` before any use.
static const nrf_staging_desc_t *nrf_staging_get_valid(void) {
  const nrf_staging_desc_t *desc =
      (const nrf_staging_desc_t *)flash_area_get_address(
          &NRF_STAGING_AREA, nrf_staging_desc_offset(),
          sizeof(nrf_staging_desc_t));
  if (desc == NULL) {
    return NULL;
  }
  if (desc->magic != NRF_STAGING_DESC_MAGIC ||
      desc->version != NRF_STAGING_DESC_VERSION ||
      desc->co_path_count > MODEL_TREE_MAX_PROOF_NODES ||
      desc->image_len == 0 || desc->image_len > nrf_staging_image_capacity()) {
    return NULL;
  }
  uint8_t tag[SHA256_DIGEST_LENGTH];
  nrf_staging_compute_tag(desc, tag);
  if (memcmp(tag, desc->tag, SHA256_DIGEST_LENGTH) != 0) {
    return NULL;
  }
  return desc;
}

bool nrf_staging_valid(void) { return nrf_staging_get_valid() != NULL; }

bool nrf_staging_read(uint32_t *out_image_len,
                      const merkle_proof_node_t **out_co_path,
                      size_t *out_co_path_count) {
  const nrf_staging_desc_t *desc = nrf_staging_get_valid();
  if (desc == NULL) {
    return false;
  }
  if (out_image_len != NULL) {
    *out_image_len = desc->image_len;
  }
  if (out_co_path != NULL) {
    *out_co_path = desc->co_path;  // stable, memory-mapped read-only flash
  }
  if (out_co_path_count != NULL) {
    *out_co_path_count = desc->co_path_count;
  }
  return true;
}

secbool nrf_staging_write_desc(uint32_t image_len,
                               const merkle_proof_node_t *co_path,
                               size_t co_path_count) {
  if (image_len == 0 || image_len > nrf_staging_image_capacity() ||
      co_path_count > MODEL_TREE_MAX_PROOF_NODES ||
      (co_path == NULL && co_path_count != 0)) {
    return secfalse;
  }

  // Build the descriptor in RAM; zero unused co-path slots so the tag is
  // deterministic and no stale stack data reaches flash.
  nrf_staging_desc_t desc;
  memset(&desc, 0, sizeof(desc));
  desc.magic = NRF_STAGING_DESC_MAGIC;
  desc.version = NRF_STAGING_DESC_VERSION;
  desc.image_len = image_len;
  desc.co_path_count = (uint32_t)co_path_count;
  if (co_path_count != 0) {
    memcpy(desc.co_path, co_path, co_path_count * sizeof(merkle_proof_node_t));
  }
  nrf_staging_compute_tag(&desc, desc.tag);

  const uint32_t offset = nrf_staging_desc_offset();

  uint32_t bytes_erased = 0;
  if (sectrue !=
          flash_area_erase_partial(&NRF_STAGING_AREA, offset, &bytes_erased) ||
      bytes_erased == 0) {
    return secfalse;
  }

  const uint32_t total = (uint32_t)((sizeof(desc) + FLASH_BLOCK_SIZE - 1) &
                                    ~(FLASH_BLOCK_SIZE - 1));

  secbool ok = secfalse;
  ensure(flash_unlock_write(), NULL);
  ok = flash_area_write_data_padded(&NRF_STAGING_AREA, offset, &desc,
                                    sizeof(desc), 0xFF, total);
  ensure(flash_lock_write(), NULL);
  return ok;
}

secbool nrf_staging_clear(void) {
  // Erasing the descriptor sector drops the magic -> "nothing staged". The
  // image bytes are left inert (overwritten by the next stage). Idempotent.
  uint32_t bytes_erased = 0;
  return flash_area_erase_partial(&NRF_STAGING_AREA, nrf_staging_desc_offset(),
                                  &bytes_erased);
}

#endif  // PQ_SECURE_BOOT && USE_SMP
