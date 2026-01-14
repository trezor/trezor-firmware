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

/** System handles registered by system or device drivers */
typedef enum {
  SYSHANDLE_USB_WIRE,
  SYSHANDLE_USB_DEBUG,
  SYSHANDLE_USB_WEBAUTHN,
  SYSHANDLE_USB_VCP,
  SYSHANDLE_BLE_IFACE_0,
  // SYSHANDLE_BLE_IFACE_N = SYSHANDLE_BLE_IFACE_0 + N - 1,
  SYSHANDLE_POWER_MANAGER,
  SYSHANDLE_BUTTON,
  SYSHANDLE_TOUCH,
  SYSHANDLE_USB,
  SYSHANDLE_BLE,
  SYSHANDLE_SYSCALL,
#ifdef USE_IPC
  SYSHANDLE_IPC0,
  SYSHANDLE_IPC1,
  SYSHANDLE_IPC2,
#endif
  SYSHANDLE_COUNT,
} syshandle_t;

#define SYSHANDLE_USB_IFACE_MIN SYSHANDLE_USB_WIRE
#define SYSHANDLE_USB_IFACE_MAX SYSHANDLE_USB_VCP

/**
 * @brief Reads data from the specified device
 *
 * This function is non-blocking and returns immediately.
 *
 * @param handle Handle of the device to read from
 * @param buffer Pointer to the buffer where the read data will be stored
 * @param buffer_size Size of the buffer in bytes
 *
 * @return Number of bytes read, or negative value on error.
 */
ssize_t syshandle_read(syshandle_t handle, void* buffer, size_t buffer_size);

/**
 * @brief Writes data to the specified device
 *
 * This function is non-blocking and returns immediately.
 *
 * @param handle Handle of the device to write to
 * @param data Pointer to the data to write
 * @param data_size Size of the data in bytes
 *
 * @return Number of bytes written, or negative value on error.
 */
ssize_t syshandle_write(syshandle_t handle, const void* data, size_t data_size);

/**
 * @brief Reads data from the specified device, blocks until data is available
 * or timeout expires.
 *
 * If the timeout is 0, the function behaves like `syshandle_read`.
 *
 * @param handle Handle of the device to read from
 * @param buffer Pointer to the buffer where the read data will be stored
 * @param buffer_size Size of the buffer in bytes
 * @param timeout Timeout in milliseconds, 0 means no timeout
 *
 * @return Number of bytes read, or negative value on error.
 */
ssize_t syshandle_read_blocking(syshandle_t handle, void* buffer,
                                size_t buffer_size, uint32_t timeout);

/**
 * @brief Writes data to the specified device, blocks until data is written
 * or timeout expires.
 *
 * If the timeout is 0, the function behaves like `syshandle_write`.
 *
 * @param handle Handle of the device to write to
 * @param data Pointer to the data to write
 * @param data_size Size of the data in bytes
 * @param timeout Timeout in milliseconds, 0 means no timeout
 */
ssize_t syshandle_write_blocking(syshandle_t handle, const void* data,
                                 size_t data_size, uint32_t timeout);

/** Bitmask of event handles */
typedef uint32_t syshandle_mask_t;

typedef struct {
  /** Bitmask of handles ready for reading */
  syshandle_mask_t read_ready;
  /** Bitmask of handles ready for writing */
  syshandle_mask_t write_ready;
} sysevents_t;

/**
 * @brief Polls for the specified device events. The function blocks until at
 * least one event is signaled or deadline expires.
 *
 * Multiple events may be signaled simultaneously.
 *
 * @param awaited Pointer to the structure specifying which events to wait for.
 * @param signalled Pointer to the structure where the signaled events will be
 * stored.
 *
 * @return The events that were signaled. If the deadline expires, the function
 * returns without signaling any events in the `signalled` structure.
 */
void sysevents_poll(const sysevents_t* awaited, sysevents_t* signalled,
                    uint32_t deadline);
