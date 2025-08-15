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

#include <trezor_rtl.h>

#include <sys/irq.h>

#include <sys/dbg_console.h>
#include <sys/sysevent.h>

#if defined(USE_DBG_CONSOLE_VCP) && !defined(USE_USB_IFACE_VCP)
#error "USE_DBG_CONSOLE_VCP requires USE_USB_IFACE_VCP"
#endif


void dbg_console_init(void) {}

ssize_t dbg_console_read(void *buffer, size_t buffer_size) { return 0; }

#ifdef USE_DBG_CONSOLE_SWO
static void itm_swo_write(const void *data, size_t data_size) {
  irq_key_t irq_key = irq_lock();

  for (size_t i = 0; i < data_size; i++) {
    ITM_SendChar(((const char *)data)[i]);
  }

  irq_unlock(irq_key);
}
#endif

#ifdef USE_DBG_CONSOLE_VCP
static void usb_vcp_write(const void *data, size_t data_size) {
#ifdef BLOCK_ON_VCP
  syshandle_write_blocking(SYSHANDLE_USB_VCP, data, data_size, 1000);
#else
  syshandle_write(SYSHANDLE_USB_VCP, data, data_size);
#endif
}
#endif

void dbg_console_write(const void *data, size_t data_size) {
#ifdef USE_DBG_CONSOLE_SWO
  itm_swo_write(data, data_size);
#endif
#ifdef USE_DBG_CONSOLE_VCP
  usb_vcp_write(data, data_size);
#endif
}

#endif  // KERNEL_MODE
