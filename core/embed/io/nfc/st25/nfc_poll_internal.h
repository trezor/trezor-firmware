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

#include <trezor_bsp.h>
#include <trezor_types.h>

#include <sys/systask.h>

bool nfc_identify(nfc_dev_info_t *dev_info);

bool nfc_check_connection(nfc_dev_info_t *dev_info);

ts_t nfc_restart_discovery(void);

// Progress the asynchronous exchange, if any. Must be called after
// rfalNfcWorker(). Returns true while the exchange is still in progress.
bool nfc_transceive_process(void);

// Returns true if the exchange started by `task_id` has finished and the
// NFC_EVENT_TRANSCEIVE_DONE event has not been reported yet.
bool nfc_transceive_event_pending(systask_id_t task_id);

// Same as nfc_transceive_event_pending() but marks the event as reported.
bool nfc_transceive_take_event(systask_id_t task_id);

// Drops the exchange started by a killed task.
void nfc_transceive_task_killed(systask_id_t task_id);
