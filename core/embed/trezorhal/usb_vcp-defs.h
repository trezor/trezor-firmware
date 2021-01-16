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

#include <stddef.h>

typedef struct __attribute__((packed)) {
  uint8_t bFunctionLength;
  uint8_t bDescriptorType;
  uint8_t bDescriptorSubtype;
  uint16_t bcdCDC;
} usb_vcp_header_descriptor_t;

typedef struct __attribute__((packed)) {
  uint8_t bFunctionLength;
  uint8_t bDescriptorType;
  uint8_t bDescriptorSubtype;
  uint8_t bmCapabilities;
  uint8_t bDataInterface;
} usb_vcp_cm_descriptor_t;

typedef struct __attribute__((packed)) {
  uint8_t bFunctionLength;
  uint8_t bDescriptorType;
  uint8_t bDescriptorSubtype;
  uint8_t bmCapabilities;
} usb_vcp_acm_descriptor_t;

typedef struct __attribute__((packed)) {
  uint8_t bFunctionLength;
  uint8_t bDescriptorType;
  uint8_t bDescriptorSubtype;
  uint8_t bControlInterface;
  uint8_t bSubordinateInterface0;
} usb_vcp_union_descriptor_t;

typedef struct __attribute__((packed)) {
  usb_interface_assoc_descriptor_t assoc;
  usb_interface_descriptor_t iface_cdc;
  usb_vcp_header_descriptor_t
      fheader;                  // Class-Specific Descriptor Header Format
  usb_vcp_cm_descriptor_t fcm;  // Call Management Functional Descriptor
  usb_vcp_acm_descriptor_t
      facm;  // Abstract Control Management Functional Descriptor
  usb_vcp_union_descriptor_t funion;  // Union Interface Functional Descriptor
  usb_endpoint_descriptor_t ep_cmd;
  usb_interface_descriptor_t iface_data;
  usb_endpoint_descriptor_t ep_in;
  usb_endpoint_descriptor_t ep_out;
} usb_vcp_descriptor_block_t;

typedef struct __attribute__((packed)) {
  uint32_t dwDTERate;
  uint8_t bCharFormat;  // usb_cdc_line_coding_bCharFormat_t
  uint8_t bParityType;  // usb_cdc_line_coding_bParityType_t
  uint8_t bDataBits;
} usb_cdc_line_coding_t;

typedef enum {
  USB_CDC_1_STOP_BITS = 0,
  USB_CDC_1_5_STOP_BITS = 1,
  USB_CDC_2_STOP_BITS = 2,
} usb_cdc_line_coding_bCharFormat_t;

typedef enum {
  USB_CDC_NO_PARITY = 0,
  USB_CDC_ODD_PARITY = 1,
  USB_CDC_EVEN_PARITY = 2,
  USB_CDC_MARK_PARITY = 3,
  USB_CDC_SPACE_PARITY = 4,
} usb_cdc_line_coding_bParityType_t;

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

/* usb_rbuf_t is used internally for the RX/TX buffering. */
typedef struct {
  size_t cap;
  volatile size_t read;
  volatile size_t write;
  uint8_t *buf;
} usb_rbuf_t;

// Maximal length of packets on IN CMD EP
#define USB_CDC_MAX_CMD_PACKET_LEN 0x08

/* usb_vcp_state_t encapsulates all state used by enabled VCP interface.  It
 * needs to be completely initialized in usb_vcp_add and reset in
 * usb_vcp_class_init.  See usb_vcp_info_t for details of the configuration
 * fields. */
typedef struct {
  const usb_vcp_descriptor_block_t *desc_block;
  usb_rbuf_t rx_ring;
  usb_rbuf_t tx_ring;
  uint8_t *rx_packet;
  uint8_t *tx_packet;
  void (*rx_intr_fn)(void);
  uint8_t rx_intr_byte;
  uint8_t ep_cmd;
  uint8_t ep_in;
  uint8_t ep_out;
  uint8_t max_packet_len;
  uint8_t ep_in_is_idle;  // Set to 1 after IN endpoint gets idle
  uint8_t cmd_buffer[USB_CDC_MAX_CMD_PACKET_LEN];
} usb_vcp_state_t;

secbool __wur usb_vcp_add(const usb_vcp_info_t *vcp_info);
secbool __wur usb_vcp_can_read(uint8_t iface_num);
secbool __wur usb_vcp_can_write(uint8_t iface_num);
int __wur usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len);
int __wur usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len);

int __wur usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                                int timeout);
int __wur usb_vcp_write_blocking(uint8_t iface_num, const uint8_t *buf,
                                 uint32_t len, int timeout);
