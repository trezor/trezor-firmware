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

#include <sys/applet.h>
#include <sys/system.h>

#include "syscall_context.h"

#ifdef KERNEL

// Checks if the current application task has read access to the
// given memory range.
//
// `addr` must point inside the task's memory. NULL is always rejected.
// For optional arguments, use `probe_read_access_opt()` if NULL implies
// zero length, or `probe_read_access_opt_const_size()` if NULL is allowed
// regardless of the length.
bool probe_read_access(const void *addr, size_t len);

// Checks if the current application task has write access to the
// given memory range.
//
// `addr` must point inside the task's memory. NULL is always rejected.
// For optional arguments, use `probe_write_access_opt()` if NULL implies
// zero length, or `probe_write_access_opt_const_size()` if NULL is allowed
// regardless of the length.
bool probe_write_access(void *addr, size_t len);

// Checks if the current application task can execute code at the
// given address.
//
// NULL is rejected. Use `probe_execute_access_opt()` for optional arguments.
bool probe_execute_access(const void *addr);

// Variants for syscall arguments that are optional by contract, i.e. where
// NULL and len == 0 is a meaningful value passed on to the syscall
// implementation.
//
// These functions are used where the length is explicit and passed as a
// separate argument.

static inline bool probe_read_access_opt(const void *addr, size_t len) {
  if (addr == NULL) {
    return len == 0;
  }

  return probe_read_access(addr, len);
}

static inline bool probe_write_access_opt(void *addr, size_t len) {
  if (addr == NULL) {
    return len == 0;
  }

  return probe_write_access(addr, len);
}

static inline bool probe_execute_access_opt(const void *addr) {
  return (addr == NULL) || probe_execute_access(addr);
}

// Variants for syscall arguments that are optional by contract, i.e. where
// NULL is a meaningful value passed on to the syscall implementation.
//
// These functions are used for arguments whose length is implicit
// (i.e. by the type of the argument) and is always constant.

static inline bool probe_write_access_opt_const_size(void *addr, size_t len) {
  return (addr == NULL) || probe_write_access(addr, len);
}

static inline bool probe_read_access_opt_const_size(const void *addr,
                                                    size_t len) {
  return (addr == NULL) || probe_read_access(addr, len);
}

// Handles access violation by exiting the current application task
// with a fatal error and the message "Access violation".
void handle_access_violation(const char *file, int line);

// Exits the current application task with an fatal error
// with the message "Access violation".
#define apptask_access_violation()                    \
  do {                                                \
    handle_access_violation(__FILE_NAME__, __LINE__); \
  } while (0)

#endif  // KERNEL
