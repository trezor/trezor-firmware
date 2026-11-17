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

#include <io/nfc.h>
#include <sys/logging.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>

LOG_DECLARE(nfc_driver);

typedef enum {
  NFC_EMU_STATE_OFF,
  NFC_EMU_STATE_DISCOVERING,
  NFC_EMU_STATE_CONNECTED,
  NFC_EMU_STATE_SENDING,
  NFC_EMU_STATE_RESPONSE_WAITING,
  NFC_EMU_STATE_RESPONSE_RECEIVED,
  NFC_EMU_STATE_RESPONSE_ERROR,
} nfc_emu_state_t;

typedef struct {
  bool last_state;       // connection state already reported to this task
  bool connected;        // unreported connect edge
  bool disconnected;     // unreported disconnect edge
  bool transceive_done;  // unreported transceive done
} nfc_fsm_t;

typedef struct {
  nfc_emu_state_t state;
  nfc_dev_info_t connected;
  nfc_apdu_message_t apdu;
  bool is_psk;
  ts_t transceive_error;
  bool transceive_done_reported;

  nfc_fsm_t fsm_tls[SYSTASK_MAX_TASKS];
} unix_driver_t;

static unix_driver_t g_driver = {
    .state = NFC_EMU_STATE_OFF,
    .connected = {0},
    .apdu = {0},
    .is_psk = false,
    .transceive_error = TS_OK,
};

static const syshandle_vmt_t g_nfc_handle_vmt;

static bool card_present(const unix_driver_t *drv) {
  return drv->connected.uid_len > 0;
}

ts_t nfc_init(void) {
  static bool initialized = false;
  if (initialized) {
    LOG_ERR("Multiple init().");
    return TS_OK;
  }
  TSH_DECLARE;
  TSH_CHECK(syshandle_register(SYSHANDLE_NFC, &g_nfc_handle_vmt, NULL),
            TS_ENOINIT);
  initialized = true;
cleanup:
  TSH_RETURN;
}

void nfc_deinit(void) { LOG_ERR("Unexpected deinit()."); }

ts_t nfc_start_discovery(void) {
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  TSH_CHECK(drv->state == NFC_EMU_STATE_OFF, TS_ENOEN);

  if (card_present(drv)) {
    drv->state = NFC_EMU_STATE_CONNECTED;
  } else {
    drv->state = NFC_EMU_STATE_DISCOVERING;
  }
cleanup:
  TSH_RETURN;
}

ts_t nfc_stop_discovery(void) {
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  drv->state = NFC_EMU_STATE_OFF;
  drv->connected.uid_len = 0;
  drv->apdu.data_len = 0;
  for (size_t i = 0; i < SYSTASK_MAX_TASKS; i++) {
    drv->fsm_tls[i].transceive_done = false;
  }
  TSH_RETURN;
}

bool nfc_get_state(void) {
  unix_driver_t *drv = &g_driver;
  return drv->state != NFC_EMU_STATE_OFF &&
         drv->state != NFC_EMU_STATE_DISCOVERING;
}

ts_t nfc_get_device_info(nfc_dev_info_t *dev_info) {
  assert(dev_info != NULL);
  if (nfc_get_state()) {
    unix_driver_t *drv = &g_driver;
    memcpy(dev_info, &drv->connected, sizeof(nfc_dev_info_t));
    return TS_OK;
  } else {
    memset(dev_info, 0, sizeof(nfc_dev_info_t));
    return TS_ENOSTATE;
  }
}

ts_t nfc_transceive_start(const nfc_apdu_message_t *cmd) {
  assert(cmd != NULL);
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  TSH_CHECK(nfc_get_state(), TS_ENOSTATE);
  TSH_CHECK(drv->state == NFC_EMU_STATE_CONNECTED, TS_EBUSY);

  memcpy(&drv->apdu, cmd, sizeof(nfc_apdu_message_t));
  drv->is_psk = false;
  drv->state = NFC_EMU_STATE_SENDING;
cleanup:
  TSH_RETURN;
}

ts_t nfc_transceive_psk_start(const uint8_t *pcd_psk, size_t pcd_psk_len) {
  assert(pcd_psk != NULL);
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  TSH_CHECK(pcd_psk_len == 16, TS_EINVAL);

  nfc_apdu_message_t psk_apdu = {0};
  memcpy(psk_apdu.data, pcd_psk, pcd_psk_len);
  psk_apdu.data_len = pcd_psk_len;

  ts_t status = nfc_transceive_start(&psk_apdu);
  TSH_CHECK_OK(status);
  drv->is_psk = true;
cleanup:
  TSH_RETURN;
}

ts_t nfc_transceive_complete(nfc_apdu_message_t *resp) {
  assert(resp != NULL);
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  TSH_CHECK(drv->state != NFC_EMU_STATE_SENDING &&
                drv->state != NFC_EMU_STATE_RESPONSE_WAITING,
            TS_EBUSY);
  TSH_CHECK(drv->state == NFC_EMU_STATE_RESPONSE_RECEIVED ||
                drv->state == NFC_EMU_STATE_RESPONSE_ERROR,
            TS_ENOSTATE);

  bool failed = drv->state == NFC_EMU_STATE_RESPONSE_ERROR;
  if (!failed) {
    memcpy(resp, &drv->apdu, sizeof(nfc_apdu_message_t));
  }
  // the card may have been removed during the exchange
  drv->state =
      card_present(drv) ? NFC_EMU_STATE_CONNECTED : NFC_EMU_STATE_DISCOVERING;
  if (failed) {
    ts_t res = drv->transceive_error;
    drv->transceive_error = TS_OK;
    return res;
  }
cleanup:
  TSH_RETURN;
}

// debuglink-side API

ts_t nfc_emu_set_connected(const uint8_t *uid, size_t uid_len) {
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  TSH_CHECK(uid_len <= NFC_MAX_UID_LEN, TS_EINVAL);

  if (uid != NULL && uid_len > 0) {
    TSH_CHECK(!card_present(drv), TS_EBUSY);
    TSH_CHECK(!nfc_get_state(), TS_ENOSTATE);
    nfc_dev_info_t new_connected = {
        .type = NFC_DEV_TYPE_A,
        .tag_type = NFCA_T4T,
        .interface = NFC_DEV_INTERFACE_ISODEP,
        .uid_len = uid_len,
    };
    drv->connected = new_connected;
    memcpy(&drv->connected.uid, uid, uid_len);
    // when the field is off, the card is detected once discovery starts
    if (drv->state == NFC_EMU_STATE_DISCOVERING) {
      drv->state = NFC_EMU_STATE_CONNECTED;
    }
  } else if (card_present(drv)) {
    memset(&drv->connected, 0, sizeof(nfc_dev_info_t));
    switch (drv->state) {
      case NFC_EMU_STATE_CONNECTED:
        drv->state = NFC_EMU_STATE_DISCOVERING;
        break;
      case NFC_EMU_STATE_SENDING:
      case NFC_EMU_STATE_RESPONSE_WAITING:
        // the exchange in progress fails, as with the ST25 driver
        drv->transceive_error = TS_ENOEN;
        drv->state = NFC_EMU_STATE_RESPONSE_ERROR;
        drv->transceive_done_reported = false;
        break;
      default:
        // field off, or a finished exchange that `nfc_transceive_complete()`
        // reports before the disconnect
        break;
    }
  }
cleanup:
  TSH_RETURN;
}

ts_t nfc_emu_get_command(nfc_apdu_message_t **cmd, bool *is_psk) {
  assert(cmd != NULL);
  assert(is_psk != NULL);
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  *cmd = NULL;
  TSH_CHECK(card_present(drv), TS_ENOEN);

  if (drv->state == NFC_EMU_STATE_SENDING) {
    drv->state = NFC_EMU_STATE_RESPONSE_WAITING;
    *is_psk = drv->is_psk;
    *cmd = &drv->apdu;
  }
cleanup:
  TSH_RETURN;
}

ts_t nfc_emu_set_response(uint32_t status, const uint8_t *resp, size_t len) {
  TSH_DECLARE;
  unix_driver_t *drv = &g_driver;
  TSH_CHECK(card_present(drv), TS_ENOEN);
  TSH_CHECK(drv->state == NFC_EMU_STATE_RESPONSE_WAITING, TS_ENOSTATE);
  TSH_CHECK(status == TS_CODE_OK || resp == NULL, TS_EINVAL);
  TSH_CHECK(status != TS_CODE_OK || resp != NULL, TS_EINVAL);

  if (resp == NULL || status != TS_CODE_OK) {
    drv->transceive_error = ts_make(status);
    drv->state = NFC_EMU_STATE_RESPONSE_ERROR;
  } else if (len > NFC_MAX_APDU_LEN) {
    // does not fit the reader's buffer, as with the ST25 driver
    drv->transceive_error = TS_ENOMEM;
    drv->state = NFC_EMU_STATE_RESPONSE_ERROR;
  } else {
    memcpy(&drv->apdu.data, resp, len);
    drv->apdu.data_len = len;
    drv->state = NFC_EMU_STATE_RESPONSE_RECEIVED;
  }
  drv->transceive_done_reported = false;
cleanup:
  TSH_RETURN;
}

// poll

bool nfc_get_event(nfc_event_t *event) {
  assert(event != NULL);
  unix_driver_t *drv = &g_driver;
  nfc_fsm_t *fsm = &drv->fsm_tls[systask_id(systask_active())];

  if (fsm->transceive_done) {
    fsm->transceive_done = false;
    *event = NFC_EVENT_TRANSCEIVE_DONE;
    return true;
  } else if (fsm->connected && fsm->disconnected) {
    fsm->connected = false;
    fsm->disconnected = false;
    fsm->last_state = false;
  } else if (fsm->connected) {
    fsm->connected = false;
    fsm->last_state = true;
    *event = NFC_EVENT_CONNECTED;
    return true;
  } else if (fsm->disconnected) {
    fsm->disconnected = false;
    fsm->last_state = false;
    *event = NFC_EVENT_DISCONNECTED;
    return true;
  }
  *event = NFC_NO_EVENT;
  return false;
}

static void on_task_created(void *context, systask_id_t task_id) {
  unix_driver_t *drv = &g_driver;
  memset(&drv->fsm_tls[task_id], 0, sizeof(nfc_fsm_t));
}

static void on_event_poll(void *context, bool read_awaited,
                          bool write_awaited) {
  UNUSED(write_awaited);

  unix_driver_t *drv = &g_driver;

  if (read_awaited) {
    bool received = drv->state == NFC_EMU_STATE_RESPONSE_RECEIVED ||
                    drv->state == NFC_EMU_STATE_RESPONSE_ERROR;
    bool notified = drv->transceive_done_reported;
    drv->transceive_done_reported = true;
    bool transceive_done = received && !notified;
    syshandle_signal_read_ready(SYSHANDLE_NFC, &transceive_done);
  }
}

static bool on_check_read_ready(void *context, systask_id_t task_id,
                                void *param) {
  unix_driver_t *drv = &g_driver;
  nfc_fsm_t *fsm = &drv->fsm_tls[task_id];
  bool new_state = nfc_get_state();
  bool transceive_done = *(bool *)param;

  if (transceive_done) {
    fsm->transceive_done = true;
  }
  if (new_state && !(fsm->last_state)) {
    fsm->connected = true;
  }
  if (!new_state && fsm->last_state) {
    fsm->disconnected = true;
  }
  return fsm->connected || fsm->disconnected || fsm->transceive_done;
}

static const syshandle_vmt_t g_nfc_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};
