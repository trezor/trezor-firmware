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

#include <io/nfc.h>

bool nfc_get_event(nfc_event_t *event) { return false; }

ts_t nfc_start_discovery(void) { return TS_OK; }
ts_t nfc_stop_discovery(void) { return TS_OK; }

bool nfc_get_state(void) {
  return true;  // FIXME
}

ts_t nfc_get_device_info(nfc_dev_info_t *dev_info) { return TS_ENOSTATE; }

ts_t nfc_transceive_start(const nfc_apdu_message_t *cmd) { return TS_ENOSTATE; }

ts_t nfc_transceive_psk_start(const uint8_t *pcd_psk, size_t pcd_psk_len) {
  return TS_ENOSTATE;
}

ts_t nfc_transceive_complete(nfc_apdu_message_t *resp) { return TS_ENOSTATE; }
