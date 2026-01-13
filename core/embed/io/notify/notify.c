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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/notify.h>

#define NOTIFICATION_VERSION 1

#ifdef USE_BLE
#include <io/ble.h>
#endif

void notify_send(notification_event_t event) {
  notification_data_t data = {0};

  data.version = NOTIFICATION_VERSION;
  data.event = event;

#ifdef BOOTLOADER
  data.flags.flags.bootloader = 1;
#endif

#ifdef USE_BLE
  ble_notify((uint8_t*)&data, sizeof(data));
#endif

  (void)data;
}

#endif
