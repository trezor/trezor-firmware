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

#define USB_WEBUSB_VENDOR_CODE 0x01   // arbitrary
#define USB_WEBUSB_LANDING_PAGE 0x01  // arbitrary

typedef struct __attribute__((packed)) {
  usb_interface_descriptor_t iface;
  usb_endpoint_descriptor_t ep_in;
  usb_endpoint_descriptor_t ep_out;
} usb_webusb_descriptor_block_t;

/* usb_webusb_info_t contains all information for setting up a WebUSB interface.
 * All passed pointers need to live at least until the interface is disabled
 * (usb_stop is called). */
typedef struct {
  uint8_t *rx_buffer;  // With length of max_packet_len bytes
  uint8_t iface_num;   // Address of this WebUSB interface
#ifdef TREZOR_EMULATOR
  uint16_t emu_port;  // UDP port of this interface in the emulator.
#else
  uint8_t ep_in;   // Address of IN endpoint (with the highest bit set)
  uint8_t ep_out;  // Address of OUT endpoint
#endif
  uint8_t subclass;          // usb_iface_subclass_t
  uint8_t protocol;          // usb_iface_protocol_t
  uint8_t polling_interval;  // In units of 1ms
  uint8_t max_packet_len;    // Length of the biggest report and of rx_buffer
} usb_webusb_info_t;

/* usb_webusb_state_t encapsulates all state used by enabled WebUSB interface.
 * It needs to be completely initialized in usb_webusb_add and reset in
 * usb_webusb_class_init.  See usb_webusb_info_t for details of the
 * configuration fields. */
typedef struct {
  const usb_webusb_descriptor_block_t *desc_block;
  uint8_t *rx_buffer;
  uint8_t ep_in;
  uint8_t ep_out;
  uint8_t max_packet_len;

  uint8_t alt_setting;    // For SET_INTERFACE/GET_INTERFACE setup reqs
  uint8_t last_read_len;  // Length of data read into rx_buffer
  uint8_t ep_in_is_idle;  // Set to 1 after IN endpoint gets idle
} usb_webusb_state_t;

secbool __wur usb_webusb_add(const usb_webusb_info_t *webusb_info);
secbool __wur usb_webusb_can_read(uint8_t iface_num);
secbool __wur usb_webusb_can_write(uint8_t iface_num);
int __wur usb_webusb_read(uint8_t iface_num, uint8_t *buf, uint32_t len);
int __wur usb_webusb_write(uint8_t iface_num, const uint8_t *buf, uint32_t len);

int __wur usb_webusb_read_select(uint32_t timeout);
int __wur usb_webusb_read_blocking(uint8_t iface_num, uint8_t *buf,
                                   uint32_t len, int timeout);
int __wur usb_webusb_write_blocking(uint8_t iface_num, const uint8_t *buf,
                                    uint32_t len, int timeout);
