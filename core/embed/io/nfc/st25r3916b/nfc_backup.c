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

#include <trezor_bsp.h>

#include <sys/irq.h>

#include "io/nfc_backup.h"
#include "nfc_backup_poll.h"
#include "nfc_internal.h"
#include "rfal_nfc.h"
#include "rfal_nfcv.h"
#include "rfal_platform.h"
#include "rfal_rf.h"

typedef struct {
  bool initialized;
  bool rfal_initialized;
  rfalNfcDiscoverParam disc_params;
} nfc_backup_t;

static nfc_backup_t g_nfc_backup = {
    .initialized = false,
    .rfal_initialized = false,
};

/**
 * Static functions
 */
static ReturnCode st25tv_poller_initialize(void);
static ReturnCode st25tv_poller_technology_detection(void);
static ReturnCode st25tv_poller_start_collision_resolution(void);
static ReturnCode st25tv_poller_get_colision_resolution_status(void);
static ReturnCode st25tv_start_activation(void);
static ReturnCode st25tv_get_activation_status(void);

bool nfc_backup_init() {
  nfc_backup_t *drv = &g_nfc_backup;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(nfc_backup_t));

  if (!nfc_spi_init()) {
    goto cleanup;
  }

  ReturnCode ret;
  ret = rfalNfcInitialize();

  if (ret != RFAL_ERR_NONE) {
    goto cleanup;
  }

  // Set default discovery parameters
  rfalNfcDefaultDiscParams(&drv->disc_params);

  // Assign ST25TV callback functions
  drv->disc_params.propNfc.rfalNfcpPollerInitialize = &st25tv_poller_initialize;
  drv->disc_params.propNfc.rfalNfcpPollerTechnologyDetection =
      st25tv_poller_technology_detection;
  drv->disc_params.propNfc.rfalNfcpPollerStartCollisionResolution =
      st25tv_poller_start_collision_resolution;
  drv->disc_params.propNfc.rfalNfcpPollerGetCollisionResolutionStatus =
      st25tv_poller_get_colision_resolution_status;
  drv->disc_params.propNfc.rfalNfcpStartActivation = st25tv_start_activation;
  drv->disc_params.propNfc.rfalNfcpGetActivationStatus =
      st25tv_get_activation_status;

  if (!nfc_backup_poll_init()) {
    goto cleanup;
  }

  drv->rfal_initialized = true;
  drv->initialized = true;

  return true;

cleanup:
  nfc_backup_deinit();
  return false;
}

void nfc_backup_deinit() {
  nfc_backup_t *drv = &g_nfc_backup;

  if (!drv->initialized) {
    return;
  }

  nfc_backup_poll_deinit();

  if (drv->rfal_initialized) {
    // Deactivate rfal STM (Disconnects active devices)
    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
    while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
      rfalNfcWorker();
    }
  }

  if (drv->rfal_initialized) {
    rfalDeinitialize();
    drv->rfal_initialized = false;
  }

  nfc_spi_deinit();

  drv->initialized = false;
}

bool nfc_backup_start_discovery() {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  drv->disc_params.techs2Find = RFAL_NFC_POLL_TECH_PROP;

  ReturnCode err;
  err = rfalNfcDiscover(&drv->disc_params);
  if (err != RFAL_ERR_NONE) {
    return false;
  }

  return true;
}

void nfc_backup_stop_discovery() {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return;
  }

  // In case the NFC state machine is active, deactivate it to idle
  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
    do {
      rfalNfcWorker();
    } while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE);
  }

  return;
}

bool nfc_backup_write_data(uint16_t block_number, const uint8_t *data,
                           size_t data_size) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  // get block size and count from system info
  nfc_backup_system_info_t system_info;
  if (!nfc_backup_read_system_info(&system_info)) {
    return false;
  }

  if (block_number * system_info.mem_block_size + data_size >
      system_info.mem_block_count * system_info.mem_block_size) {
    // Out of bounds
    return false;
  }

  uint8_t tx_buf[5] = {0};
  uint8_t rx_buf[3];
  uint16_t rx_bytes = 0;

  size_t remaining_bytes = data_size;
  uint8_t *data_pointer = (uint8_t *)data;
  uint16_t current_block = block_number;

  while (remaining_bytes > 0) {
    // Number of block is encoded in first byte of transceived buffer
    tx_buf[0] = current_block;

    if (remaining_bytes >= system_info.mem_block_size) {
      memcpy(&tx_buf[1], data_pointer, system_info.mem_block_size);
      remaining_bytes -= system_info.mem_block_size;
      data_pointer += system_info.mem_block_size;
    } else {
      memset(&tx_buf[1], 0, system_info.mem_block_size);
      memcpy(&tx_buf[1], data_pointer, remaining_bytes);
      remaining_bytes = 0;
    }

    rfalNfcvPollerTransceiveReq(
        RFAL_NFCV_CMD_WRITE_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
        RFAL_NFCV_PARAM_SKIP, NULL, tx_buf, sizeof(tx_buf), rx_buf,
        sizeof(rx_buf), &rx_bytes);

    if (rx_bytes != 1 || rx_buf[0] != 0x00) {
      return false;
    }

    current_block++;
  }

  return true;
}

bool nfc_backup_read_data(uint16_t block_number, uint8_t *data,
                          size_t data_size) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  // get block size and count from system info
  nfc_backup_system_info_t system_info;
  if (!nfc_backup_read_system_info(&system_info)) {
    return false;
  }

  if (block_number * system_info.mem_block_size + data_size >
      system_info.mem_block_count * system_info.mem_block_size) {
    // Out of bounds
    return false;
  }

  uint8_t data_buffer[1] = {0};
  uint8_t recieved_buf[7] = {0};
  uint16_t received_bytes = 0;

  size_t remaining_bytes = data_size;
  uint8_t *data_pointer = data;
  uint16_t current_block = block_number;

  while (remaining_bytes > 0) {
    data_buffer[0] = current_block;

    // Read each block of data
    rfalNfcvPollerTransceiveReq(
        RFAL_NFCV_CMD_READ_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
        RFAL_NFCV_PARAM_SKIP, NULL, data_buffer, sizeof(data_buffer),
        recieved_buf, sizeof(recieved_buf), &received_bytes);

    if (received_bytes != 5 || recieved_buf[0] != 0x00) {
      return false;
    }

    if (remaining_bytes >= system_info.mem_block_size) {
      memcpy(data_pointer, &recieved_buf[1], system_info.mem_block_size);
      remaining_bytes -= system_info.mem_block_size;
      data_pointer += system_info.mem_block_size;
    } else {
      memcpy(data_pointer, &recieved_buf[1], remaining_bytes);
      remaining_bytes = 0;
    }

    current_block++;
  }

  return true;
}

bool nfc_backup_wipe_memory() {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return false;
  }

  // get block size and count from system info
  nfc_backup_system_info_t system_info;
  if (!nfc_backup_read_system_info(&system_info)) {
    return false;
  }

  uint8_t tx_buf[5] = {0};
  uint8_t rx_buf[3];
  uint16_t rx_bytes = 0;

  for (uint16_t block = 0; block < system_info.mem_block_count; block++) {
    tx_buf[0] = block;

    rfalNfcvPollerTransceiveReq(
        RFAL_NFCV_CMD_WRITE_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
        RFAL_NFCV_PARAM_SKIP, NULL, tx_buf, sizeof(tx_buf), rx_buf,
        sizeof(rx_buf), &rx_bytes);

    if (rx_bytes != 1 || rx_buf[0] != 0x00) {
      return false;
    }
  }

  return true;
}

bool nfc_backup_set_silent_mode(bool enable) {
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

  uint8_t data[3];
  data[0] = 0x05;  // FID
  data[1] = 0x00;  // PID
  if (enable) {
    data[2] = 0x05;  // Boot to silent mode regardless of DS_STS
  } else {
    data[2] = 0x00;  // Disbale silent mode
  }

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
    system_info->dsfid = response[10];
    system_info->afi = response[11];
    system_info->mem_block_count = response[12] + 1;  // Block size in bytes
    system_info->mem_block_size = response[13] + 1;   // Number of blocks
    system_info->ic_reference = response[14];
  }

  // Read UID from the configuration register directly to be sure it reads out
  // even if the TAG is in silent mode.
  uint8_t data[2] = {
      0xFE,  // FID
      0x01,  // PID
  };

  rfalNfcvPollerTransceiveReq(
      0xA0U, RFAL_NFCV_REQ_FLAG_DEFAULT, RFAL_NFCV_ST_IC_MFG_CODE, NULL, data,
      sizeof(data), response, sizeof(response), &received_length);

  if (response[0] == 0x0 && received_length == 9) {
    memcpy(system_info->uid, &response[1], 8);
    return true;
  }

  return false;
}

void nfc_backup_get_state(nfc_backup_state_t *state) {
  nfc_backup_t *drv = &g_nfc_backup;
  if (!drv->initialized) {
    return;
  }

  state->connected = true;
}

static bool nfc_backup_toggle_discrete_mode() {
  ReturnCode ret = RFAL_ERR_NONE;
  uint16_t receivedLength = 0;
  uint8_t response[5] = {0};
  uint8_t data[5] = {0};

  // GetRandomNumber, see section 6.4.24 of ST25TV datasheet
  ret = rfalNfcvPollerTransceiveReq(
      0xB4U, RFAL_NFCV_REQ_FLAG_DEFAULT, RFAL_NFCV_ST_IC_MFG_CODE, NULL, NULL,
      0U, response, sizeof(response), &receivedLength);
  if (ret != RFAL_ERR_NONE) {
    return false;
  }
  if (receivedLength != 3) {
    return false;
  }

  // ToggleUntraceable issued in non-addressed mode to unlock tags in discrete
  // mode, see section 6.4.23 of ST25TV datasheet. It is assumed the password
  // is 0x00000000.

  data[0] = 0x03U;
  data[1] = response[1];
  data[2] = response[2];
  data[3] = response[1];
  data[4] = response[2];
  ret = rfalNfcvPollerTransceiveReq(
      0xBAU, RFAL_NFCV_REQ_FLAG_DEFAULT, RFAL_NFCV_ST_IC_MFG_CODE, NULL, data,
      5, response, sizeof(response), &receivedLength);

  return true;
}

static ReturnCode st25tv_poller_initialize(void) {
  return rfalNfcvPollerInitialize();
}

static ReturnCode st25tv_poller_technology_detection(void) {
  nfc_backup_toggle_discrete_mode();

  rfalNfcvInventoryRes invRes;
  return rfalNfcvPollerCheckPresence(&invRes);
}

static ReturnCode st25tv_poller_start_collision_resolution(void) {
  return RFAL_ERR_NONE;
}

static ReturnCode st25tv_poller_get_colision_resolution_status(void) {
  rfalNfcvListenDevice nfc_dev_list;
  uint8_t devCnt;
  return rfalNfcvPollerCollisionResolution(RFAL_COMPLIANCE_MODE_NFC, 1,
                                           &nfc_dev_list, &devCnt);
}

static ReturnCode st25tv_start_activation(void) { return RFAL_ERR_NONE; }

static ReturnCode st25tv_get_activation_status(void) { return RFAL_ERR_NONE; }

#endif  // KERNEL_MODE
