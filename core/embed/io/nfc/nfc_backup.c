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

#include "io/nfc_backup.h"
#include "io/nfc.h"
#include "rfal_nfcv.h"
#include "rfal_st25xv.h"

#pragma GCC optimize("O0")

typedef struct {
  bool initialized;
  nfc_backup_system_info_t system_info;
} nfc_backup_t;

static nfc_backup_t g_nfc_backup = {
    .initialized = false,
};

bool nfc_backup_init() {
  nfc_backup_t *drv = &g_nfc_backup;

  if (drv->initialized) {
    return true;
  }

  nfc_status_t status = nfc_init();
  if (status != NFC_OK) {
    return false;
  }

  nfc_register_tech(NFC_POLLER_TECH_V);

  drv->initialized = true;
  return true;
}

void nfc_backup_deinit() {
  nfc_backup_t *drv = &g_nfc_backup;

  if (!drv->initialized) {
    return;
  }

  nfc_deinit();

  drv->initialized = false;
}

bool nfc_backup_store_data(const uint8_t *data, size_t data_size) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  uint8_t recieved_buf[3];
  uint16_t received = 0;

  const size_t block_size = 4;
  const size_t block_count = data_size / block_size;

  uint8_t data_buffer[5];

  for (size_t i = 0; i < block_count; i++) {
    const uint8_t *block_data = data + (i * block_size);

    data_buffer[0] = i;
    memcpy(&data_buffer[1], block_data, block_size);

    // Store each block of data
    rfalNfcvPollerTransceiveReq(
        RFAL_NFCV_CMD_WRITE_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
        RFAL_NFCV_PARAM_SKIP, NULL, data_buffer, sizeof(data_buffer),
        recieved_buf, sizeof(recieved_buf), &received);

    if (received != 1 || recieved_buf[0] != 0x00) {
      return false;
    }
  }

  return true;
}

bool nfc_backup_read_data(uint8_t *data, size_t data_size) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  uint8_t recieved_buf[7] = {0};
  uint16_t received = 0;

  const size_t block_size = 4;
  const size_t block_count = data_size / block_size;

  uint8_t data_buffer[1];

  for (size_t i = 0; i < block_count; i++) {
    data_buffer[0] = i;

    // Read each block of data
    rfalNfcvPollerTransceiveReq(
        RFAL_NFCV_CMD_READ_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
        RFAL_NFCV_PARAM_SKIP, NULL, data_buffer, sizeof(data_buffer),
        recieved_buf, sizeof(recieved_buf), &received);

    if (received != 5 || recieved_buf[0] != 0x00) {
      return false;
    }

    memcpy(data + (i * block_size), &recieved_buf[1], block_size);
  }

  return true;
}

bool nfc_backup_configure_discrete_mode() {
  uint8_t response[16] = {0};
  uint16_t received_length = 0;

  // GetRandomNumber, see section 6.4.24 of ST25TV datasheet
  rfalNfcvPollerTransceiveReq(0xB4U, RFAL_NFCV_REQ_FLAG_DEFAULT,
                              RFAL_NFCV_ST_IC_MFG_CODE, NULL, NULL, 0U,
                              response, sizeof(response), &received_length);

  if (received_length != 3) {
    return RFAL_ERR_PROTO;
  }

  uint8_t password_req_data[5] = {
      0x00,  // PWD_CFG id
      0x00 ^ response[1],
      0x00 ^ response[2],
      0x00 ^ response[1],
      0x00 ^ response[2],
  };

  rfalNfcvPollerTransceiveReq(0xB3, RFAL_NFCV_REQ_FLAG_DEFAULT, 0x2, NULL,
                              password_req_data, sizeof(password_req_data),
                              response, sizeof(response), &received_length);

  if (response[0] != 0x0) {
    return false;
  }

  uint8_t data[3] = {
      0x05,  // FID
      0x00,  // PID
      0x01,  // Boot to discrete state regardless of DS_STS value
  };

  rfalNfcvPollerTransceiveReq(
      0xA1U, RFAL_NFCV_REQ_FLAG_DEFAULT, RFAL_NFCV_ST_IC_MFG_CODE, NULL, data,
      sizeof(data), response, sizeof(response), &received_length);

  if (response[0] == 0x0) {
    return true;
  }

  return false;
}

bool nfc_backup_read_system_info(nfc_backup_system_info_t *system_info) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  uint8_t response[16] = {0};
  uint16_t received_length = 0;

  rfalNfcvPollerTransceiveReq(0x2BU, RFAL_NFCV_REQ_FLAG_DEFAULT,
                              RFAL_NFCV_PARAM_SKIP, NULL, NULL, 0x0, response,
                              sizeof(response), &received_length);

  if (response[0] == 0x0 && response[1] == 0x0F) {
    // Parse system info
    memcpy(system_info->uid, &response[2], 8);
    system_info->dsfid = response[10];
    system_info->afi = response[11];
    system_info->memory_size = (response[12] << 8) | response[13];
    system_info->ic_reference = response[14];
    return true;
  }

  return false;
}

void nfc_backup_configure_storage() {
  // Configure NFC storage parameters if needed
}

void nfc_backup_worker(nfc_backup_state_t *state) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return;
  }

  nfc_event_t nfc_event;
  nfc_status_t nfc_status = nfc_get_event(&nfc_event);
  if (nfc_status != NFC_OK) {
    return;
  }

  if (nfc_event == NFC_EVENT_ACTIVATED) {
    state->connected = true;
  } else if (nfc_event == NFC_EVENT_DEACTIVATED) {
    state->connected = false;
  }
}

bool nfc_backup_start_discovery() {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  nfc_activate_stm();

  return true;
}

void nfc_backup_stop_discovery() {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return;
  }

  nfc_deactivate_stm();
}

void nfc_backup_get_state(nfc_backup_state_t *state) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return;
  }

  state->connected = true;
}
