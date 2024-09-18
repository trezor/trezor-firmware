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

#include "wakeup_flags.h"
#include "irq.h"

#ifdef KERNEL_MODE

static uint16_t g_wakeup_flags = 0;

void wakeup_flag_set(uint16_t flags) {
  irq_key_t irq_key = irq_lock();
  g_wakeup_flags |= flags;
  irq_unlock(irq_key);
}

uint16_t wakeup_get_and_clear(void) {
  irq_key_t irq_key = irq_lock();
  uint16_t flags = g_wakeup_flags;
  g_wakeup_flags = 0;
  irq_unlock(irq_key);
  return flags;
}

#endif  // KERNEL_MODE
