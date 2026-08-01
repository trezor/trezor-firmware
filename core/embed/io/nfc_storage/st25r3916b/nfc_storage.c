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

#include <io/nfc_storage.h>
#include <sys/irq.h>

#include "devices/nfc_device.h"
#include "nfc_storage_internal.h"
#include "nfc_storage_poll.h"
#include "rfal_nfc.h"
#include "rfal_platform.h"

typedef struct {
  bool initialized;
  bool rfal_initialized;
  rfalNfcDiscoverParam disc_params;
} nfc_storage_t;

static nfc_storage_t g_nfc_storage = {
    .initialized = false,
    .rfal_initialized = false,
};

typedef struct {
  bool registered;
  uint8_t tech;
  rfalNfcDevType device_type;

  // Service functions
  bool (*identify)(void);
  bool (*check_connection)(void);

  // Storage functions
  bool (*get_mem_struct)(nfc_storage_mem_struct_t *mem_struct);
  bool (*write)(uint32_t address, const uint8_t *data, size_t length);
  bool (*read)(uint32_t address, uint8_t *data, size_t length);
  bool (*wipe)(void);
} nfc_device_t;

typedef struct {
  nfc_device_t devices[NFC_STORAGE_MAX_TYPES];
  nfc_storage_type_t connected_device;
} nfc_storage_device_list_t;

nfc_storage_device_list_t g_nfc_storage_discovery_list = {
    .devices[NFC_STORAGE_ST25TV] =
        {
            .registered = false,
            .tech = RFAL_NFC_POLL_TECH_PROP,
            .device_type = RFAL_NFC_LISTEN_TYPE_PROP,
            .identify = st25tv_identify,
            .check_connection = st25tv_check_connection,
            .get_mem_struct = st25tv_get_mem_struct,
            .write = st25tv_write,
            .read = st25tv_read,
            .wipe = st25tv_wipe,
        },
    .connected_device = NFC_STORAGE_NO_DEVICE,
};

/**
 * Rfal proprietary technology callback functions
 */
static ReturnCode prop_tech_poller_initialize(void);
static ReturnCode prop_tech_poller_technology_detection(void);
static ReturnCode prop_tech_poller_start_collision_resolution(void);
static ReturnCode prop_tech_poller_get_colision_resolution_status(void);
static ReturnCode prop_tech_start_activation(void);
static ReturnCode prop_tech_get_activation_status(void);

bool nfc_storage_init() {
  nfc_storage_t *drv = &g_nfc_storage;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(nfc_storage_t));

  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  for (int i = 0; i < NFC_STORAGE_MAX_TYPES; i++) {
    list->devices[i].registered = false;
  }

  list->connected_device = NFC_STORAGE_NO_DEVICE;

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
  drv->disc_params.propNfc.rfalNfcpPollerInitialize =
      &prop_tech_poller_initialize;
  drv->disc_params.propNfc.rfalNfcpPollerTechnologyDetection =
      prop_tech_poller_technology_detection;
  drv->disc_params.propNfc.rfalNfcpPollerStartCollisionResolution =
      prop_tech_poller_start_collision_resolution;
  drv->disc_params.propNfc.rfalNfcpPollerGetCollisionResolutionStatus =
      prop_tech_poller_get_colision_resolution_status;
  drv->disc_params.propNfc.rfalNfcpStartActivation = prop_tech_start_activation;
  drv->disc_params.propNfc.rfalNfcpGetActivationStatus =
      prop_tech_get_activation_status;

  if (!nfc_storage_poll_init()) {
    goto cleanup;
  }

  drv->rfal_initialized = true;
  drv->initialized = true;

  return true;

cleanup:
  nfc_storage_deinit();
  return false;
}

void nfc_storage_deinit() {
  nfc_storage_t *drv = &g_nfc_storage;

  if (!drv->initialized) {
    return;
  }

  nfc_storage_poll_deinit();

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

bool nfc_storage_register_device(nfc_storage_type_t type) {
  nfc_storage_t *drv = &g_nfc_storage;

  if (drv->initialized == false) {
    return false;
  }

  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  if (type >= NFC_STORAGE_MAX_TYPES) {
    return false;  // Invalid type
  }

  if (list->devices[type].registered) {
    return false;  // Already registered
  }

  list->devices[type].registered = true;

  return true;
}

bool nfc_storage_start_discovery() {
  nfc_storage_t *drv = &g_nfc_storage;

  if (!drv->initialized) {
    return false;
  }

  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  drv->disc_params.techs2Find = RFAL_NFC_TECH_NONE;
  for (uint8_t i = 0; i < NFC_STORAGE_MAX_TYPES; i++) {
    if (list->devices[i].registered) {
      drv->disc_params.techs2Find |= list->devices[i].tech;

      // In case the specific technology requires any special disc_params
      // set then here.
    }
  }

  if (drv->disc_params.techs2Find == RFAL_NFC_TECH_NONE) {
    return false;  // No registered technologies
  }

  ReturnCode err;
  err = rfalNfcDiscover(&drv->disc_params);
  if (err != RFAL_ERR_NONE) {
    return false;
  }

  return true;
}

void nfc_storage_stop_discovery() {
  nfc_storage_t *drv = &g_nfc_storage;
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

bool nfc_storage_device_get_mem_struct(nfc_storage_mem_struct_t *mem_struct) {
  nfc_storage_t *drv = &g_nfc_storage;

  if (drv->initialized == false) {
    return false;
  }

  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  if (mem_struct == NULL || list->connected_device == NFC_STORAGE_NO_DEVICE) {
    return false;
  }

  return list->devices[list->connected_device].get_mem_struct(mem_struct);
}

bool nfc_storage_device_read_data(uint32_t addr, uint8_t *data,
                                  size_t data_size) {
  nfc_storage_t *drv = &g_nfc_storage;
  if (drv->initialized == false) {
    return false;
  }

  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  if (list->connected_device == NFC_STORAGE_NO_DEVICE) {
    return false;
  }

  return list->devices[list->connected_device].read(addr, data, data_size);
}

bool nfc_storage_device_write_data(uint32_t addr, const uint8_t *data,
                                   size_t data_size) {
  nfc_storage_t *drv = &g_nfc_storage;
  if (drv->initialized == false) {
    return false;
  }

  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  if (list->connected_device == NFC_STORAGE_NO_DEVICE) {
    return false;
  }

  return list->devices[list->connected_device].write(addr, data, data_size);
}

bool nfc_storage_device_wipe_memory() {
  nfc_storage_t *drv = &g_nfc_storage;
  if (drv->initialized == false) {
    return false;
  }

  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  if (list->connected_device == NFC_STORAGE_NO_DEVICE) {
    return false;
  }

  return list->devices[list->connected_device].wipe();
}

bool nfc_storage_is_connected() {
  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;
  return list->connected_device != NFC_STORAGE_NO_DEVICE;
}

bool nfc_storage_identify(rfalNfcDevType device_type) {
  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  if (list->connected_device != NFC_STORAGE_NO_DEVICE) {
    return true;  // Device already identified
  }

  for (uint8_t i = 0; i < NFC_STORAGE_MAX_TYPES; i++) {
    if (list->devices[i].registered &&
        (list->devices[i].device_type == device_type)) {
      // Call identify function
      if (list->devices[i].identify()) {
        // Device identified
        list->connected_device = i;
        return true;
      }
    }
  }

  return false;
}

bool nfc_storage_check_connection() {
  nfc_storage_device_list_t *list = &g_nfc_storage_discovery_list;

  if (list->connected_device == NFC_STORAGE_NO_DEVICE) {
    return false;
  }

  if (!list->devices[list->connected_device].check_connection()) {
    // Device disconnected
    list->connected_device = NFC_STORAGE_NO_DEVICE;
    return false;
  }

  return true;
}

static ReturnCode prop_tech_poller_initialize(void) {
  return rfalNfcvPollerInitialize();
}

static ReturnCode prop_tech_poller_technology_detection(void) {
  // nfc_storage_toggle_discrete_mode();

  rfalNfcvInventoryRes invRes;
  return rfalNfcvPollerCheckPresence(&invRes);
}

static ReturnCode prop_tech_poller_start_collision_resolution(void) {
  return RFAL_ERR_NONE;
}

static ReturnCode prop_tech_poller_get_colision_resolution_status(void) {
  rfalNfcvListenDevice nfc_dev_list;
  uint8_t devCnt;
  return rfalNfcvPollerCollisionResolution(RFAL_COMPLIANCE_MODE_NFC, 1,
                                           &nfc_dev_list, &devCnt);
}

static ReturnCode prop_tech_start_activation(void) { return RFAL_ERR_NONE; }

static ReturnCode prop_tech_get_activation_status(void) {
  return RFAL_ERR_NONE;
}

#endif  // KERNEL_MODE
