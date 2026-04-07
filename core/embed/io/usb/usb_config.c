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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/usb.h>
#include <io/usb_config.h>
#include <io/usb_hid.h>
#include <io/usb_vcp.h>
#include <io/usb_webusb.h>

#ifdef TREZOR_EMULATOR
#include <stdlib.h>
#endif

#define USB_IFACE_BASE_PORT 21324

#define USB_IFACE_WIRE_PORT_OFFSET 0
#define USB_IFACE_DEBUG_PORT_OFFSET 1
#define USB_IFACE_WEBAUTHN_PORT_OFFSET 2
#define USB_IFACE_VCP_PORT_OFFSET 3

static secbool usb_device_init(void) {
#if defined(BOOTLOADER)
  usb_dev_info_t dev_info_default = {
      .device_class = 0x00,
      .device_subclass = 0x00,
      .device_protocol = 0x00,
      .vendor_id = 0x1209,
      .product_id = 0x53C0,
      .release_num = 0x0200,
      .manufacturer = MODEL_USB_MANUFACTURER,
      .product = MODEL_USB_PRODUCT,
      .serial_number = "000000000000000000000000",
      .interface = "TREZOR Interface",
      .usb21_enabled = sectrue,
      .usb21_landing = secfalse,
  };
#elif defined(PRODTEST)
  static const usb_dev_info_t dev_info_default = {
      .device_class = 0xEF,     // Composite Device Class
      .device_subclass = 0x02,  // Common Class
      .device_protocol = 0x01,  // Interface Association Descriptor
      .vendor_id = 0x1209,
      .product_id = 0x53C1,
      .release_num = 0x0400,
      .manufacturer = MODEL_USB_MANUFACTURER,
      .product = MODEL_USB_PRODUCT,
      .serial_number = "000000000000",
      .interface = "TREZOR Interface",
      .usb21_enabled = secfalse,
      .usb21_landing = secfalse,
  };
#else
  static const usb_dev_info_t dev_info_default = {
      .device_class = 0x00,
      .device_subclass = 0x00,
      .device_protocol = 0x00,
      .vendor_id = 0x1209,
      .product_id = 0x53C1,
      .release_num = 0x0200,
      .manufacturer = MODEL_USB_MANUFACTURER,
      .product = MODEL_USB_PRODUCT,
      .serial_number = "000000000000000000000000",
      .interface = "TREZOR Interface",
      .usb21_enabled = sectrue,
      .usb21_landing = secfalse,
  };
#endif

  usb_dev_info_t dev_info = dev_info_default;

  return usb_init(&dev_info);
}

#ifdef TREZOR_EMULATOR
static uint16_t usb_emu_port(uint16_t port_offset) {
  const char *base_port = getenv("TREZOR_UDP_PORT");
  return port_offset + (base_port ? atoi(base_port) : USB_IFACE_BASE_PORT);
}
#endif

// ----------------------------------------------------------------

#ifdef USE_USB_IFACE_WIRE
static secbool usb_wire_iface_init(uint8_t *iface_num) {
  static uint8_t wire_iface_buffer[USB_PACKET_LEN];

  const usb_webusb_info_t wire_iface = {
      .handle = SYSHANDLE_USB_WIRE,
      .rx_buffer = wire_iface_buffer,
      .iface_num = *iface_num,
#ifdef TREZOR_EMULATOR
      .emu_port = usb_emu_port(USB_IFACE_WIRE_PORT_OFFSET),
#else
      .ep_in = 0x01 + *iface_num,
      .ep_out = 0x01 + *iface_num,
#endif
      .subclass = 0x00,
      .protocol = 0x00,
      .polling_interval = 1,
      .max_packet_len = sizeof(wire_iface_buffer),
  };

  if (sectrue != usb_webusb_add(&wire_iface)) {
    return secfalse;
  }

  *iface_num += 1;

  return sectrue;
}
#endif  // USE_USB_IFACE_WIRE

#ifdef USE_USB_IFACE_DEBUG
static secbool usb_debug_iface_init(uint8_t *iface_num) {
  static uint8_t debug_iface_buffer[USB_PACKET_LEN];

  const usb_webusb_info_t debug_iface = {
      .handle = SYSHANDLE_USB_DEBUG,
      .rx_buffer = debug_iface_buffer,
      .iface_num = *iface_num,
#ifdef TREZOR_EMULATOR
      .emu_port = usb_emu_port(USB_IFACE_DEBUG_PORT_OFFSET),
#else
      .ep_in = 0x01 + *iface_num,
      .ep_out = 0x01 + *iface_num,
#endif
      .subclass = 0x00,
      .protocol = 0x00,
      .polling_interval = 1,
      .max_packet_len = sizeof(debug_iface_buffer),
  };

  if (sectrue != usb_webusb_add(&debug_iface)) {
    return secfalse;
  }

  *iface_num += 1;

  return sectrue;
}
#endif  // USE_USB_IFACE_DEBUG

#ifdef USE_USB_IFACE_WEBAUTHN
static secbool usb_webauthn_iface_init(uint8_t *iface_num) {
  static const uint8_t webauthn_report_map[] = {
      0x06, 0xd0, 0xf1,  // USAGE_PAGE (FIDO Alliance)
      0x09, 0x01,        // USAGE (U2F HID Authenticator Device)
      0xa1, 0x01,        // COLLECTION (Application)
      0x09, 0x20,        //  USAGE (Input Report Data)
      0x15, 0x00,        //  LOGICAL_MINIMUM (0)
      0x26, 0xff, 0x00,  //  LOGICAL_MAXIMUM (255)
      0x75, 0x08,        //  REPORT_SIZE (8)
      0x95, 0x40,        //  REPORT_COUNT (64)
      0x81, 0x02,        //  INPUT (Data,Var,Abs)
      0x09, 0x21,        //  USAGE (Output Report Data)
      0x15, 0x00,        //  LOGICAL_MINIMUM (0)
      0x26, 0xff, 0x00,  //  LOGICAL_MAXIMUM (255)
      0x75, 0x08,        //  REPORT_SIZE (8)
      0x95, 0x40,        //  REPORT_COUNT (64)
      0x91, 0x02,        //  OUTPUT (Data,Var,Abs)
      0xc0,              // END_COLLECTION
  };

  static uint8_t webauthn_iface_buffer[USB_PACKET_LEN];

  const usb_hid_info_t webauthn_iface = {
      .handle = SYSHANDLE_USB_WEBAUTHN,
      .report_desc = webauthn_report_map,
      .report_desc_len = sizeof(webauthn_report_map),
      .rx_buffer = webauthn_iface_buffer,
      .max_packet_len = sizeof(webauthn_iface_buffer),
      .iface_num = *iface_num,
#ifdef TREZOR_EMULATOR
      .emu_port = usb_emu_port(USB_IFACE_WEBAUTHN_PORT_OFFSET),
#else
      .ep_in = 0x01 + *iface_num,
      .ep_out = 0x01 + *iface_num,
#endif
      .subclass = 0x00,
      .protocol = 0x00,
      .polling_interval = 1,
  };

  if (sectrue != usb_hid_add(&webauthn_iface)) {
    return secfalse;
  }

  *iface_num += 1;

  return sectrue;
}
#endif  // USE_USB_IFACE_WEBAUTHN

#if defined(USE_USB_HS) && !defined(USE_USB_HS_IN_FS)
#define VCP_PACKET_LEN 512  // HS periperal in HS mode
#elif defined(USE_USB_HS) && defined(USE_USB_HS_IN_FS)
#define VCP_PACKET_LEN 64  // HS peripheral in FS mode
#elif defined(USE_USB_FS)
#define VCP_PACKET_LEN 64
#elif defined(TREZOR_EMULATOR)
#define VCP_PACKET_LEN 64
#else
#error "USB type not defined"
#endif

#define VCP_TX_BUFFER_LEN 2048
#define VCP_RX_BUFFER_LEN 2048

#ifdef USE_USB_IFACE_VCP
static secbool usb_vcp_iface_init(uint8_t *iface_num,
                                  usb_vcp_intr_callback_t vcp_intr_callback) {
  static uint8_t vcp_tx_packet[VCP_PACKET_LEN];
  static uint8_t vcp_tx_buffer[VCP_TX_BUFFER_LEN];
  static uint8_t vcp_rx_packet[VCP_PACKET_LEN];
  static uint8_t vcp_rx_buffer[VCP_RX_BUFFER_LEN];

  const usb_vcp_info_t vcp_info = {
      .handle = SYSHANDLE_USB_VCP,
      .tx_packet = vcp_tx_packet,
      .tx_buffer = vcp_tx_buffer,
      .rx_packet = vcp_rx_packet,
      .rx_buffer = vcp_rx_buffer,
      .tx_buffer_len = sizeof(vcp_tx_buffer),
      .rx_buffer_len = sizeof(vcp_rx_buffer),
      .max_packet_len = VCP_PACKET_LEN,
      .rx_intr_fn = vcp_intr_callback,
      .rx_intr_byte = 3,  // Ctrl-C
      .iface_num = *iface_num,
      .data_iface_num = *iface_num + 1,
#ifdef TREZOR_EMULATOR
      .emu_port = usb_emu_port(USB_IFACE_VCP_PORT_OFFSET),
#else
      .ep_cmd = 0x01 + *iface_num + 1,
      .ep_in = 0x01 + *iface_num,
      .ep_out = 0x01 + *iface_num,
#endif
      .polling_interval = 10,
  };

  if (sectrue != usb_vcp_add(&vcp_info)) {
    return secfalse;
  }

  *iface_num += 2;  // increment by data iface

  return sectrue;
}
#endif  // USE_USB_IFACE_VCP

secbool usb_configure(usb_vcp_intr_callback_t vcp_intr_callback) {
  if (sectrue != usb_device_init()) {
    goto cleanup;
  }

  uint8_t iface_num = 0;

#ifdef USE_USB_IFACE_WIRE
  if (sectrue != usb_wire_iface_init(&iface_num)) {
    goto cleanup;
  }
#endif

#ifdef USE_USB_IFACE_DEBUG
  if (sectrue != usb_debug_iface_init(&iface_num)) {
    goto cleanup;
  }
#endif

#ifdef USE_USB_IFACE_WEBAUTHN
  if (sectrue != usb_webauthn_iface_init(&iface_num)) {
    goto cleanup;
  }
#endif

#ifdef USE_USB_IFACE_VCP
  if (sectrue != usb_vcp_iface_init(&iface_num, vcp_intr_callback)) {
    goto cleanup;
  }
#endif

  return sectrue;

cleanup:

  usb_deinit();
  return secfalse;
}

#endif  // KERNEL_MODE
