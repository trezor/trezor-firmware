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

// Turning off the stack protector for this file improves
// the performance of syscall dispatching.
#pragma GCC optimize("no-stack-protector")

#include <trezor_bsp.h>
#include <trezor_model.h>

#include "smcall_probe.h"

#ifdef SECMON

bool probe_read_access(const void *addr, size_t len) {
  if (addr == NULL) {
    return true;
  }

  // Address overflow check
  if ((uintptr_t)addr + len < (uintptr_t)addr) {
    return false;
  }

  if (!cmse_check_address_range((void *)addr, len,
                                CMSE_MPU_READ | CMSE_NONSECURE)) {
    return false;
  }

  return true;
}

bool probe_write_access(void *addr, size_t len) {
  if (addr == NULL) {
    return true;
  }

  // Address overflow check
  if ((uintptr_t)addr + len < (uintptr_t)addr) {
    return false;
  }

  if (!cmse_check_address_range(addr, len,
                                CMSE_MPU_READWRITE | CMSE_NONSECURE)) {
    return false;
  }

  return true;
}

bool probe_execute_access(const void *addr) {
  if (addr == NULL) {
    return true;
  }

  // Just check if the address is in non-secure address range
  if (!cmse_check_address_range((void *)addr, 4,
                                CMSE_MPU_READ | CMSE_NONSECURE)) {
    return false;
  }

  return true;
}

#endif  // SECMON
