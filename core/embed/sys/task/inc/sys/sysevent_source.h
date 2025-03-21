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

#ifdef KERNEL_MODE

#include <sys/sysevent.h>
#include <sys/systask.h>

// Callback invoked when a new task is created.
// Driver may use this callback to initialize the its own task local storage.
typedef void (*syshandle_task_created_cb_t)(void *context,
                                            systask_id_t task_id);

// Callback invoked when a task is killed
// Driver may use this callback to deinitialize the its own task local storage.
//
// The callback may be called from the fault handler. But in this case
// it's guaranteed that the task is not running anymore.
typedef void (*syshandle_task_killed_cb_t)(void *context, systask_id_t task_id);

// Callback invoked when the system is polling for events.
//
// 'read_awaited' is set if there's at least one task waiting for read events.
// 'write_awaited' is set if there's at least one task waiting for write events.
typedef void (*syshandle_poll_cb_t)(void *context, bool read_awaited,
                                    bool write_awaited);

// Callback invoked when the driver's polling callback calls
// `syshandle_signal_read_ready()` or `syshandle_signal_write_ready()`.
//
// The callback is executed for each task waiting for the event.
// The `param` parameter is passed unchanged from the
// `syshandle_signal_read_ready()` or `syshandle_signal_write_ready()` function.
//
// The callback returns `true` if the event should be signaled to the task.
typedef bool (*syshandle_check_cb_t)(void *context, systask_id_t task_id,
                                     void *param);

// System handle virtual method table
typedef struct {
  syshandle_task_created_cb_t task_created;
  syshandle_task_killed_cb_t task_killed;
  syshandle_poll_cb_t poll;
  syshandle_check_cb_t check_read_ready;
  syshandle_check_cb_t check_write_ready;
} syshandle_vmt_t;

// ----------------------------------------------------------------------

// Registers a new event source
//
// This function is called by the device driver's
// initialization code. Sources that are not registered will never be signaled.
//
// Returns `true` if the source was registered successfully.
bool syshandle_register(syshandle_t handle, const syshandle_vmt_t *vmt,
                        void *context);

// Unregisters an event source
//
// This function is called by the device driver's deinitialization code.
void syshandle_unregister(syshandle_t handle);

// Distributes read ready event to waiting tasks
//
// This function is called by the device driver to distribute events
// to waiting tasks.
//
// The function may only be called from a poll callback.
void syshandle_signal_read_ready(syshandle_t handle, void *param);

// Distributes write ready event to waiting tasks
//
// This function is called by the device driver to distribute events
// to waiting tasks.
//
// The function may only be called from a poll callback.
void syshandle_signal_write_ready(syshandle_t handle, void *param);

// ----------------------------------------------------------------------
// Internal functions called by the system

// Notifies all registered event sources / drivers about a new task creation
//
// The function invoke the `task_created` callback of each registered
// event source.
void sysevents_notify_task_created(systask_t *task);

// Notifies all registered event sources / drivers about a task termination
//
// The function invoke the `task_killed` callback of each registered
// event source.
void sysevents_notify_task_killed(systask_t *task);

#endif  // KERNEL_MODE
