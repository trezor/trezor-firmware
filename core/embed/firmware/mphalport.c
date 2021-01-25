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

#include "common.h"
#include "py/mphal.h"
#include "usb.h"

static int vcp_iface_num = -1;

int mp_hal_stdin_rx_chr(void) {
  ensure(sectrue * (vcp_iface_num >= 0), "vcp stdio is not configured");
  uint8_t c = 0;
  int r = usb_vcp_read_blocking(vcp_iface_num, &c, 1, -1);
  (void)r;
  return c;
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
  if (vcp_iface_num >= 0) {
    // The write timeout is set to 0, because otherwise when the VCP receive
    // buffer on the host gets full, the timeout will block device operation.
    int r = usb_vcp_write_blocking(vcp_iface_num, (const uint8_t *)str, len, 0);
    (void)r;
  }
}

void mp_hal_set_vcp_iface(int iface_num) { vcp_iface_num = iface_num; }
