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

#include <sys/system.h>

#ifdef SECMON

// Checks if the non-secure code has read access to the
// given memory range.
//
// `addr` must be a non-secure address. NULL is always rejected.
// Use `probe_read_access_opt()` for optional arguments.
bool probe_read_access(const void *addr, size_t len);

// Checks if the non-secure code has write access to the
// given memory range.
//
// `addr` must be a non-secure address. NULL is always rejected.
// Use `probe_write_access_opt()` for optional arguments.
bool probe_write_access(void *addr, size_t len);

// Checks if the provided address is in non-secure address range
//
// NULL is rejected. Use `probe_execute_access_opt()` for optional arguments.
bool probe_execute_access(const void *addr);

// Variants for smcall arguments that are optional by contract, i.e. where
// NULL is a meaningful value passed on to the smcall implementation.
//
// These exist so that every such argument is explicit at the call site and
// a NULL reaching any other probe is caught as an access violation instead
// of being dereferenced by the secure monitor.

static inline bool probe_read_access_opt(const void *addr, size_t len) {
  return (addr == NULL) || probe_read_access(addr, len);
}

static inline bool probe_write_access_opt(void *addr, size_t len) {
  return (addr == NULL) || probe_write_access(addr, len);
}

static inline bool probe_execute_access_opt(const void *addr) {
  return (addr == NULL) || probe_execute_access(addr);
}

// Exits the current application task with an fatal error
// with the message "Access violation".
#define apptask_access_violation()                             \
  do {                                                         \
    system_exit_fatal("Access violation", __FILE__, __LINE__); \
  } while (0)

#endif  // SECMON
