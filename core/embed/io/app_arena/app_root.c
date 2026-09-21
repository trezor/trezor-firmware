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

#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include <io/app_root.h>
#include <sec/mldsa44.h>

#include "root_packet.h"

// Information held for each application ring, derived from the root packet
typedef struct {
  // Timestamp of the root packet the ring data was derived from
  int64_t timestamp;
  // Merkle root for this ring
  sha256_digest_t merkle_root;
} app_ring_data_t;

// Root-of-trust storage structure
typedef struct {
  // Set if the structure has been initialized
  bool initialized;
  // Merkle root for each ring, indexed by app_ring_t
  app_ring_data_t ring[APP_RING_COUNT];
} app_root_t;

// App root-of-trust storage instance
static app_root_t g_app_root = {
    .initialized = false,
};

ts_t app_root_init(void) {
  TSH_DECLARE;

  app_root_t* root = &g_app_root;

  if (root->initialized) {
    TSH_RETURN;
  }

  memset(root, 0, sizeof(app_root_t));
  root->initialized = true;

  // cleanup:
  TSH_RETURN;
}

// Returns the index of the first set bit in the ring mask,
// or -1 if no bits are set.
static int first_updated_ring(uint8_t ring_mask) {
  for (int id = 0; id < APP_RING_COUNT; id++) {
    if (ring_mask & (1 << id)) {
      return id;
    }
  }
  return -1;
}

ts_t app_root_update(const void* root_packet_data, size_t root_packet_data_size,
                     app_root_state_t* state) {
  TSH_DECLARE;
  ts_t status;

  app_root_t* root = &g_app_root;
  TSH_CHECK(root->initialized, TS_ENOINIT);

  root_packet_auth_t* root_packet = NULL;
  status =
      root_packet_verify(root_packet_data, root_packet_data_size, &root_packet);
  TSH_CHECK_OK(status);

  TSH_CHECK(root_packet != NULL, TS_EBADMSG);

  // Check that any updated ring is not downgraded
  for (int id = 0; id < APP_RING_COUNT; id++) {
    if (root_packet->ring_mask & (1 << id)) {
      TSH_CHECK(root_packet->timestamp >= state->ring_timestamp[id],
                TS_EBADMSG);
    }
  }

  // Ensure that lower-priority rings (with higher id) are not older than
  // higher-priority rings
  int first_id = first_updated_ring(root_packet->ring_mask);
  if (first_id > 0) {
    TSH_CHECK(
        root_packet->chain_timestamp >= state->ring_timestamp[first_id - 1],
        TS_EBADMSG);
  }

  int slot = 0;
  for (int id = 0; id < APP_RING_COUNT; id++) {
    if (root_packet->ring_mask & (1 << id)) {
      state->ring_timestamp[id] = root_packet->timestamp;
      root->ring[id].timestamp = root_packet->timestamp;
      root->ring[id].merkle_root = root_packet->merkle_root[slot];
      ++slot;
    }
  }

cleanup:
  TSH_RETURN;
}

ts_t app_root_reset(void) {
  TSH_DECLARE;

  app_root_t* root = &g_app_root;
  TSH_CHECK(root->initialized, TS_ENOINIT);

  for (size_t i = 0; i < ARRAY_LENGTH(root->ring); i++) {
    memset(&root->ring[i], 0, sizeof(app_ring_data_t));
  }

cleanup:
  TSH_RETURN;
}

bool app_root_is_loaded(app_ring_t ring) {
  app_root_t* root = &g_app_root;

  if (!root->initialized) {
    return false;
  }

  if (ring >= ARRAY_LENGTH(root->ring)) {
    return false;
  }

  return root->ring[ring].timestamp != 0;
}

ts_t app_root_get_timestamp(app_ring_t ring, int64_t* timestamp) {
  TSH_DECLARE;

  TSH_CHECK_ARG(timestamp != NULL);
  *timestamp = 0;

  app_root_t* root = &g_app_root;
  TSH_CHECK(root->initialized, TS_ENOINIT);

  TSH_CHECK_ARG(ring < ARRAY_LENGTH(root->ring));
  app_ring_data_t* ring_data = &root->ring[ring];

  TSH_CHECK(ring_data->timestamp != 0, TS_ENOENT);

  *timestamp = ring_data->timestamp;

cleanup:
  TSH_RETURN;
}

ts_t app_root_get_merkle_root(app_ring_t ring, sha256_digest_t* merkle_root) {
  TSH_DECLARE;

  TSH_CHECK_ARG(merkle_root != NULL);
  memset(merkle_root, 0, sizeof(sha256_digest_t));

  app_root_t* root = &g_app_root;
  TSH_CHECK(root->initialized, TS_ENOINIT);

  TSH_CHECK_ARG(ring < ARRAY_LENGTH(root->ring));
  app_ring_data_t* ring_data = &root->ring[ring];

  TSH_CHECK(ring_data->timestamp != 0, TS_ENOENT);

  *merkle_root = ring_data->merkle_root;

cleanup:
  TSH_RETURN;
}

#endif  // KERNEL_MODE
