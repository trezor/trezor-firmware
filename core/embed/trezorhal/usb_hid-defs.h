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

typedef struct __attribute__((packed)) {
  uint8_t bLength;
  uint8_t bDescriptorType;
  uint16_t bcdHID;
  uint8_t bCountryCode;
  uint8_t bNumDescriptors;
  uint8_t bReportDescriptorType;
  uint16_t wReportDescriptorLength;
} usb_hid_descriptor_t;

typedef struct __attribute__((packed)) {
  usb_interface_descriptor_t iface;
  usb_hid_descriptor_t hid;
  usb_endpoint_descriptor_t ep_in;
  usb_endpoint_descriptor_t ep_out;
} usb_hid_descriptor_block_t;

/* usb_hid_info_t contains all information for setting up a HID interface.  All
 * passed pointers need to live at least until the interface is disabled
 * (usb_stop is called). */
typedef struct {
  const uint8_t *report_desc;  // With length of report_desc_len bytes
  uint8_t *rx_buffer;          // With length of max_packet_len bytes
  uint8_t iface_num;           // Address of this HID interface
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
  uint8_t report_desc_len;   // Length of report_desc
} usb_hid_info_t;

/* usb_hid_state_t encapsulates all state used by enabled HID interface.  It
 * needs to be completely initialized in usb_hid_add and reset in
 * usb_hid_class_init.  See usb_hid_info_t for details of the configuration
 * fields. */
typedef struct {
  const usb_hid_descriptor_block_t *desc_block;
  const uint8_t *report_desc;
  uint8_t *rx_buffer;
  uint8_t ep_in;
  uint8_t ep_out;
  uint8_t max_packet_len;
  uint8_t report_desc_len;

  uint8_t protocol;       // For SET_PROTOCOL/GET_PROTOCOL setup reqs
  uint8_t idle_rate;      // For SET_IDLE/GET_IDLE setup reqs
  uint8_t alt_setting;    // For SET_INTERFACE/GET_INTERFACE setup reqs
  uint8_t last_read_len;  // Length of data read into rx_buffer
  uint8_t ep_in_is_idle;  // Set to 1 after IN endpoint gets idle
} usb_hid_state_t;

secbool __wur usb_hid_add(const usb_hid_info_t *hid_info);
secbool __wur usb_hid_can_read(uint8_t iface_num);
secbool __wur usb_hid_can_write(uint8_t iface_num);
int __wur usb_hid_read(uint8_t iface_num, uint8_t *buf, uint32_t len);
int __wur usb_hid_write(uint8_t iface_num, const uint8_t *buf, uint32_t len);

int __wur usb_hid_read_select(uint32_t timeout);
int __wur usb_hid_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                                int timeout);
int __wur usb_hid_write_blocking(uint8_t iface_num, const uint8_t *buf,
                                 uint32_t len, int timeout);
