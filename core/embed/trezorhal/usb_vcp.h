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

#ifndef TREZORHAL_USB_CLASS_VCP_H
#define TREZORHAL_USB_CLASS_VCP_H

#include <stddef.h>
#include "secbool.h"

/* usb_vcp_info_t contains all information for setting up a VCP interface.  All
 * passed pointers need to live at least until the interface is disabled
 * (usb_stop is called). */
typedef struct {
  uint8_t *tx_packet;  // Buffer for one packet, with length of at least
                       // max_packet_len bytes
  uint8_t *tx_buffer;  // Buffer for IN EP ring buffer, with length of at least
                       // tx_buffer_len bytes
  uint8_t *rx_packet;  // Buffer for one packet, with length of at least
                       // max_packet_len bytes
  uint8_t *rx_buffer;  // Buffer for OUT EP ring buffer, with length of at least
                       // rx_buffer_len bytes
  size_t tx_buffer_len;      // Length of tx_buffer, needs to be a power of 2
  size_t rx_buffer_len;      // Length of rx_buffer, needs to be a power of 2
  void (*rx_intr_fn)(void);  // Callback called from usb_vcp_class_data_out IRQ
                             // handler if rx_intr_byte matches
  uint8_t rx_intr_byte;      // Value matched against every received byte
  uint8_t iface_num;         // Address of this VCP interface
  uint8_t data_iface_num;    // Address of data interface of the VCP interface
                             // association
#ifdef TREZOR_EMULATOR
  uint16_t emu_port;  // UDP port of this interface in the emulator.
#else
  uint8_t ep_cmd;  // Address of IN CMD endpoint (with the highest bit set)
  uint8_t ep_in;   // Address of IN endpoint (with the highest bit set)
  uint8_t ep_out;  // Address of OUT endpoint
#endif
  uint8_t polling_interval;  // In units of 1ms
  uint8_t max_packet_len;  // Length of the biggest packet, and of tx_packet and
                           // rx_packet
} usb_vcp_info_t;

secbool __wur usb_vcp_add(const usb_vcp_info_t *vcp_info);
secbool __wur usb_vcp_can_read(uint8_t iface_num);
secbool __wur usb_vcp_can_write(uint8_t iface_num);
int __wur usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len);
int __wur usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len);

int __wur usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                                int timeout);
int __wur usb_vcp_write_blocking(uint8_t iface_num, const uint8_t *buf,
                                 uint32_t len, int timeout);

#endif  // TREZORHAL_USB_CLASS_VCP_H
