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

#include <sys/systask.h>

// IPC message is a callback from a previous request
#define IPC_FN_CALLBACK 0x4000
// IPC message is a response to a previous request
#define IPC_FN_RETURN 0x8000

typedef struct {
  systask_id_t remote;
  // Function code with flags (IPC_FN_xxx)
  uint16_t fn;
  // Pointer to the message payload data
  const void *data;
  // Size of the payload data
  size_t size;
} ipc_message_t;

#ifdef KERNEL_MODE

/**
 * @brief Initializes the IPC subsystem.
 *
 * Internal function called during system startup.
 *
 * @return true if the IPC subsystem was successfully initialized
 */
bool ipc_init(void);

#endif  // KERNEL_MODE

/**
 * @brief Registers a buffer for receiving IPC messages from a specific task.
 *
 * Buffer must be aligned to sizeof(size_t) bytes, otherwise the registration
 * will fail.
 *
 * @param remote The remote task ID to register the buffer for.
 * @param buffer Pointer to the buffer to use for receiving messages.
 * @param size Size of the buffer in bytes.
 * @return true if the buffer was successfully registered
 *
 */
bool ipc_register(systask_id_t remote, void *buffer, size_t size);

/**
 * @brief Unregisters the IPC message buffer for the given task ID.
 *
 * @param remote The remote task ID to unregister the buffer for.
 *
 */
void ipc_unregister(systask_id_t remote);

/**
 * @brief Attempts to receive an IPC message without blocking.
 *
 * @param msg Pointer to an `ipc_message_t` structure to store the received
 * message.
 * @return true if a message was received and stored in `msg`
 */
bool ipc_try_receive(ipc_message_t *msg);

/**
 * @brief Releases resources associated with a received IPC message.
 *
 * This function should be called sooner or later for every message
 * received via `ipc_receive` or `ipc_try_receive`.
 *
 * @param msg Pointer to the freed `ipc_message_t` structure.
 */
void ipc_message_free(ipc_message_t *msg);

/**
 * @brief Sends an IPC message to the specified destination task.
 *
 * This function is non-blocking and returns immediately.
 * The call succeeds only if the remote task has registered a buffer for
 * receiving messages and there is enough space in that buffer.
 *
 * @param msg Pointer to the message to send.
 * @return true if the message was successfully sent
 */
bool ipc_send(const ipc_message_t *msg);

/**
 * @brief Sends an IPC request message and waits for a response.
 *
 * @param req Pointer to the request message to send.
 * @param rsp Pointer to the structure to store the received message.
 * @param timeout Maximum time to wait for a response in milliseconds.
 *
 * @return true if the response was successfully received within the timeout
 * period, false otherwise.
 */
bool ipc_call(const ipc_message_t *req, ipc_message_t *rsp, uint32_t timeout);
