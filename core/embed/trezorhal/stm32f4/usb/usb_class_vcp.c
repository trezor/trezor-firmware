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

#include "common.h"

#include "usb_internal.h"
#include "usb_vcp.h"

// Communications Device Class Code (bFunctionClass, bInterfaceClass)
#define USB_CLASS_CDC 0x02

// Data Interface Class Code (bInterfaceClass)
#define USB_CLASS_DATA 0x0A

// Class Subclass Code (bFunctionSubClass, bInterfaceSubClass)
#define USB_CDC_SUBCLASS_ACM 0x02

// Communications Interface Class Control Protocol Codes (bFunctionProtocol,
// bInterfaceProtocol)
#define USB_CDC_PROTOCOL_AT 0x01

// Descriptor Types (bDescriptorType)
#define USB_DESC_TYPE_ASSOCIATION 0x0B
#define USB_DESC_TYPE_CS_INTERACE 0x24

// Descriptor SubTypes (bDescriptorSubtype)
#define USB_DESC_TYPE_HEADER 0x00
#define USB_DESC_TYPE_CM 0x01
#define USB_DESC_TYPE_ACM 0x02
#define USB_DESC_TYPE_UNION 0x06

// Data Phase Transfer Direction (bmRequest)
#define USB_REQ_DIR_MASK 0x80
#define USB_REQ_DIR_H2D 0x00
#define USB_REQ_DIR_D2H 0x80

// Class-Specific Request Codes for PSTN subclasses
#define USB_CDC_SET_LINE_CODING 0x20
#define USB_CDC_GET_LINE_CODING 0x21
#define USB_CDC_SET_CONTROL_LINE_STATE 0x22

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
  USBD_HandleTypeDef *dev_handle;
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

_Static_assert(sizeof(usb_vcp_state_t) <= USBD_CLASS_STATE_MAX_SIZE);

// interface dispatch functions
static const USBD_ClassTypeDef usb_vcp_class;
static const USBD_ClassTypeDef usb_vcp_data_class;

#define usb_get_vcp_state(iface_num) \
  ((usb_vcp_state_t *)usb_get_iface_state(iface_num, &usb_vcp_class))

/* usb_vcp_add adds and configures new USB VCP interface according to
 * configuration options passed in `info`. */
secbool usb_vcp_add(const usb_vcp_info_t *info) {
  usb_vcp_state_t *state = usb_get_iface_state(info->iface_num, NULL);

  if (state == NULL) {
    return secfalse;  // Invalid interface number
  }

  usb_vcp_descriptor_block_t *d =
      usb_alloc_class_descriptors(sizeof(usb_vcp_descriptor_block_t));

  if (d == NULL) {
    return secfalse;  // Not enough space in the configuration descriptor
  }

  if ((info->rx_buffer_len == 0) ||
      (info->rx_buffer_len & (info->rx_buffer_len - 1)) != 0) {
    return secfalse;  // Capacity needs to be a power of 2
  }
  if ((info->tx_buffer_len == 0) ||
      (info->tx_buffer_len & (info->tx_buffer_len - 1)) != 0) {
    return secfalse;  // Capacity needs to be a power of 2
  }
  if (info->rx_buffer == NULL) {
    return secfalse;
  }
  if (info->rx_packet == NULL) {
    return secfalse;
  }
  if (info->tx_buffer == NULL) {
    return secfalse;
  }
  if (info->tx_packet == NULL) {
    return secfalse;
  }
  if (info->ep_in >= USBD_MAX_NUM_INTERFACES) {
    return secfalse;
  }
  if (info->ep_out >= USBD_MAX_NUM_INTERFACES) {
    return secfalse;
  }
  if (info->ep_cmd >= USBD_MAX_NUM_INTERFACES) {
    return secfalse;
  }

  // Interface association descriptor
  d->assoc.bLength = sizeof(usb_interface_assoc_descriptor_t);
  d->assoc.bDescriptorType = USB_DESC_TYPE_ASSOCIATION;
  d->assoc.bFirstInterface = info->iface_num;
  d->assoc.bInterfaceCount = 2;
  d->assoc.bFunctionClass = USB_CLASS_CDC;
  d->assoc.bFunctionSubClass = USB_CDC_SUBCLASS_ACM;
  d->assoc.bFunctionProtocol = USB_CDC_PROTOCOL_AT;
  d->assoc.iFunction = 0;

  // Interface descriptor
  d->iface_cdc.bLength = sizeof(usb_interface_descriptor_t);
  d->iface_cdc.bDescriptorType = USB_DESC_TYPE_INTERFACE;
  d->iface_cdc.bInterfaceNumber = info->iface_num;
  d->iface_cdc.bAlternateSetting = 0;
  d->iface_cdc.bNumEndpoints = 1;
  d->iface_cdc.bInterfaceClass = USB_CLASS_CDC;
  d->iface_cdc.bInterfaceSubClass = USB_CDC_SUBCLASS_ACM;
  d->iface_cdc.bInterfaceProtocol = USB_CDC_PROTOCOL_AT;
  d->iface_cdc.iInterface = USBD_IDX_INTERFACE_STR;

  // Header Functional Descriptor
  d->fheader.bFunctionLength = sizeof(usb_vcp_header_descriptor_t);
  d->fheader.bDescriptorType = USB_DESC_TYPE_CS_INTERACE;
  d->fheader.bDescriptorSubtype = USB_DESC_TYPE_HEADER;
  d->fheader.bcdCDC = 0x1001;  // USB Class Definitions for Communication
                               // Devices Specification release number.

  // Call Management Functional Descriptor
  d->fcm.bFunctionLength = sizeof(usb_vcp_cm_descriptor_t);
  d->fcm.bDescriptorType = USB_DESC_TYPE_CS_INTERACE;
  d->fcm.bDescriptorSubtype = USB_DESC_TYPE_CM;
  // Device sends/receives call management information only over the
  // Communication Class interface. Device does not handle call management
  // itself.
  d->fcm.bmCapabilities = 0x00;
  d->fcm.bDataInterface = info->data_iface_num;

  // ACM Functional Descriptor
  d->facm.bFunctionLength = sizeof(usb_vcp_acm_descriptor_t);
  d->facm.bDescriptorType = USB_DESC_TYPE_CS_INTERACE;
  d->facm.bDescriptorSubtype = USB_DESC_TYPE_ACM;
  // Device supports the request combination of Set_Line_Coding,
  // Set_Control_Line_State, Get_Line_Coding, and the notification Serial_State.
  d->facm.bmCapabilities = 0x02;

  // Union Functional Descriptor
  d->funion.bFunctionLength = sizeof(usb_vcp_union_descriptor_t);
  d->funion.bDescriptorType = USB_DESC_TYPE_CS_INTERACE;
  d->funion.bDescriptorSubtype = USB_DESC_TYPE_UNION;
  d->funion.bControlInterface = info->iface_num;
  d->funion.bSubordinateInterface0 = info->data_iface_num;

  // IN CMD endpoint (control)
  d->ep_cmd.bLength = sizeof(usb_endpoint_descriptor_t);
  d->ep_cmd.bDescriptorType = USB_DESC_TYPE_ENDPOINT;
  d->ep_cmd.bEndpointAddress = info->ep_cmd | USB_EP_DIR_IN;
  d->ep_cmd.bmAttributes = USBD_EP_TYPE_INTR;
  d->ep_cmd.wMaxPacketSize = USB_CDC_MAX_CMD_PACKET_LEN;
  d->ep_cmd.bInterval = info->polling_interval;

  // Interface descriptor
  d->iface_data.bLength = sizeof(usb_interface_descriptor_t);
  d->iface_data.bDescriptorType = USB_DESC_TYPE_INTERFACE;
  d->iface_data.bInterfaceNumber = info->data_iface_num;
  d->iface_data.bAlternateSetting = 0;
  d->iface_data.bNumEndpoints = 2;
  d->iface_data.bInterfaceClass = USB_CLASS_DATA;
  d->iface_data.bInterfaceSubClass = 0;
  d->iface_data.bInterfaceProtocol = 0;
  d->iface_data.iInterface = USBD_IDX_INTERFACE_STR;

  // OUT endpoint (receiving)
  d->ep_out.bLength = sizeof(usb_endpoint_descriptor_t);
  d->ep_out.bDescriptorType = USB_DESC_TYPE_ENDPOINT;
  d->ep_out.bEndpointAddress = info->ep_out | USB_EP_DIR_OUT;
  d->ep_out.bmAttributes = USBD_EP_TYPE_BULK;
  d->ep_out.wMaxPacketSize = info->max_packet_len;
  d->ep_out.bInterval = 0;

  // IN endpoint (sending)
  d->ep_in.bLength = sizeof(usb_endpoint_descriptor_t);
  d->ep_in.bDescriptorType = USB_DESC_TYPE_ENDPOINT;
  d->ep_in.bEndpointAddress = info->ep_in | USB_EP_DIR_IN;
  d->ep_in.bmAttributes = USBD_EP_TYPE_BULK;
  d->ep_in.wMaxPacketSize = info->max_packet_len;
  d->ep_in.bInterval = 0;

  // Interface state
  state->desc_block = d;

  state->rx_ring.buf = info->rx_buffer;
  state->rx_ring.cap = info->rx_buffer_len;
  state->rx_ring.read = 0;
  state->rx_ring.write = 0;

  state->tx_ring.buf = info->tx_buffer;
  state->tx_ring.cap = info->tx_buffer_len;
  state->tx_ring.read = 0;
  state->tx_ring.write = 0;

  state->rx_packet = info->rx_packet;
  state->tx_packet = info->tx_packet;

  state->rx_intr_fn = info->rx_intr_fn;
  state->rx_intr_byte = info->rx_intr_byte;

  state->ep_cmd = info->ep_cmd | USB_EP_DIR_IN;
  state->ep_in = info->ep_in | USB_EP_DIR_IN;
  state->ep_out = info->ep_out | USB_EP_DIR_OUT;
  state->max_packet_len = info->max_packet_len;

  state->ep_in_is_idle = 1;

  usb_set_iface_class(info->iface_num, &usb_vcp_class);

  // This just make the data interface slot occupied so it can't be reused
  // by another class driver. Data interface dispatch functiona are not used.
  usb_set_iface_class(info->data_iface_num, &usb_vcp_data_class);

  return sectrue;
}

static inline size_t ring_length(usb_rbuf_t *b) { return (b->write - b->read); }

static inline int ring_empty(usb_rbuf_t *b) { return ring_length(b) == 0; }

static inline int ring_full(usb_rbuf_t *b) { return ring_length(b) == b->cap; }

secbool usb_vcp_can_read(uint8_t iface_num) {
  usb_vcp_state_t *state = usb_get_vcp_state(iface_num);
  if (state == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (ring_empty(&state->rx_ring)) {
    return secfalse;  // Nothing in the rx buffer
  }
  return sectrue;
}

secbool usb_vcp_can_write(uint8_t iface_num) {
  usb_vcp_state_t *state = usb_get_vcp_state(iface_num);
  if (state == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (ring_full(&state->tx_ring)) {
    return secfalse;  // Tx ring buffer is full
  }
  return sectrue;
}

int usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  usb_vcp_state_t *state = usb_get_vcp_state(iface_num);
  if (state == NULL) {
    return -1;  // Invalid interface number
  }

  // Read from the rx ring buffer
  usb_rbuf_t *b = &state->rx_ring;
  size_t mask = b->cap - 1;
  size_t i;
  for (i = 0; (i < len) && !ring_empty(b); i++) {
    buf[i] = b->buf[b->read & mask];
    b->read++;
  }
  return i;
}

int usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  usb_vcp_state_t *state = usb_get_vcp_state(iface_num);
  if (state == NULL) {
    return -1;  // Invalid interface number
  }

  // Write into the tx ring buffer
  usb_rbuf_t *b = &state->tx_ring;
  size_t mask = b->cap - 1;
  size_t i;
  for (i = 0; (i < len) && !ring_full(b); i++) {
    b->buf[b->write & mask] = buf[i];
    b->write++;
  }

  return i;
}

int usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                          int timeout) {
  uint32_t start = HAL_GetTick();
  while (sectrue != usb_vcp_can_read(iface_num)) {
    if (timeout >= 0 && HAL_GetTick() - start >= timeout) {
      return 0;  // Timeout
    }
    __WFI();  // Enter sleep mode, waiting for interrupt
  }
  return usb_vcp_read(iface_num, buf, len);
}

int usb_vcp_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len,
                           int timeout) {
  uint32_t start = HAL_GetTick();
  uint32_t i = 0;
  while (i < len) {
    while (sectrue != usb_vcp_can_write(iface_num)) {
      if (timeout >= 0 && HAL_GetTick() - start >= timeout) {
        return i;  // Timeout
      }
      __WFI();  // Enter sleep mode, waiting for interrupt
    }
    int ret = usb_vcp_write(iface_num, buf + i, len - i);
    if (ret < 0) return ret;
    i += ret;
  }
  return i;
}

static uint8_t usb_vcp_class_init(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
  usb_vcp_state_t *state = (usb_vcp_state_t *)dev->pUserData;

  state->dev_handle = dev;

  // Open endpoints
  USBD_LL_OpenEP(dev, state->ep_in, USBD_EP_TYPE_BULK, state->max_packet_len);
  USBD_LL_OpenEP(dev, state->ep_out, USBD_EP_TYPE_BULK, state->max_packet_len);
  USBD_LL_OpenEP(dev, state->ep_cmd, USBD_EP_TYPE_INTR,
                 USB_CDC_MAX_CMD_PACKET_LEN);

  // Reset the state
  state->rx_ring.read = 0;
  state->rx_ring.write = 0;
  state->tx_ring.read = 0;
  state->tx_ring.write = 0;
  state->ep_in_is_idle = 1;

  // Prepare the OUT EP to receive next packet
  USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_packet,
                         state->max_packet_len);

  return USBD_OK;
}

static uint8_t usb_vcp_class_deinit(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
  usb_vcp_state_t *state = (usb_vcp_state_t *)dev->pUserData;

  // Flush endpoints
  USBD_LL_FlushEP(dev, state->ep_in);
  USBD_LL_FlushEP(dev, state->ep_out);
  USBD_LL_FlushEP(dev, state->ep_cmd);
  // Close endpoints
  USBD_LL_CloseEP(dev, state->ep_in);
  USBD_LL_CloseEP(dev, state->ep_out);
  USBD_LL_CloseEP(dev, state->ep_cmd);

  state->dev_handle = NULL;

  return USBD_OK;
}

static uint8_t usb_vcp_class_setup(USBD_HandleTypeDef *dev,
                                   USBD_SetupReqTypedef *req) {
  usb_vcp_state_t *state = (usb_vcp_state_t *)dev->pUserData;

  static const usb_cdc_line_coding_t line_coding = {
      .dwDTERate = 115200,
      .bCharFormat = USB_CDC_1_STOP_BITS,
      .bParityType = USB_CDC_NO_PARITY,
      .bDataBits = 8,
  };

  if ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_CLASS) {
    return USBD_OK;
  }

  if ((req->bmRequest & USB_REQ_DIR_MASK) == USB_REQ_DIR_D2H) {
    if (req->bRequest == USB_CDC_GET_LINE_CODING) {
      USBD_CtlSendData(dev, UNCONST(&line_coding),
                       MIN_8bits(req->wLength, sizeof(line_coding)));
    } else {
      USBD_CtlSendData(dev, state->cmd_buffer,
                       MIN_8bits(req->wLength, USB_CDC_MAX_CMD_PACKET_LEN));
    }
  } else {  // USB_REQ_DIR_H2D
    if (req->wLength > 0) {
      USBD_CtlPrepareRx(dev, state->cmd_buffer,
                        MIN_8bits(req->wLength, USB_CDC_MAX_CMD_PACKET_LEN));
    }
  }

  return USBD_OK;
}

static uint8_t usb_vcp_class_data_in(USBD_HandleTypeDef *dev, uint8_t ep_num) {
  usb_vcp_state_t *state = (usb_vcp_state_t *)dev->pUserData;

  if ((ep_num | USB_EP_DIR_IN) == state->ep_in) {
    state->ep_in_is_idle = 1;
  }

  return USBD_OK;
}

static uint8_t usb_vcp_class_data_out(USBD_HandleTypeDef *dev, uint8_t ep_num) {
  usb_vcp_state_t *state = (usb_vcp_state_t *)dev->pUserData;

  if (ep_num == state->ep_out) {
    uint32_t len = USBD_LL_GetRxDataSize(dev, ep_num);

    // Write into the rx ring buffer
    usb_rbuf_t *b = &state->rx_ring;
    size_t mask = b->cap - 1;
    size_t i;
    for (i = 0; i < len; i++) {
      if (state->rx_intr_fn != NULL) {
        if (state->rx_packet[i] == state->rx_intr_byte) {
          state->rx_intr_fn();
        }
      }
      if (!ring_full(b)) {
        b->buf[b->write & mask] = state->rx_packet[i];
        b->write++;
      }
    }

    // Prepare the OUT EP to receive next packet
    USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_packet,
                           state->max_packet_len);
  }

  return USBD_OK;
}

static uint8_t usb_vcp_class_sof(USBD_HandleTypeDef *dev) {
  usb_vcp_state_t *state = (usb_vcp_state_t *)dev->pUserData;

  if (!state->ep_in_is_idle) {
    return USBD_OK;
  }

  // Read from the tx ring buffer
  usb_rbuf_t *b = &state->tx_ring;
  uint8_t *buf = state->tx_packet;
  // We avoid sending full packets as they stall the hosts pipeline, see:
  // <http://www.cypress.com/?id=4&rID=92719>
  size_t len = state->max_packet_len - 1;
  size_t mask = b->cap - 1;
  size_t i;
  for (i = 0; (i < len) && !ring_empty(b); i++) {
    buf[i] = b->buf[b->read & mask];
    b->read++;
  }

  if (i > 0) {
    state->ep_in_is_idle = 0;
    USBD_LL_Transmit(dev, state->ep_in, buf, (uint16_t)i);
  }

  return USBD_OK;
}

static const USBD_ClassTypeDef usb_vcp_class = {
    .Init = usb_vcp_class_init,
    .DeInit = usb_vcp_class_deinit,
    .Setup = usb_vcp_class_setup,
    .EP0_TxSent = NULL,
    .EP0_RxReady = NULL,
    .DataIn = usb_vcp_class_data_in,
    .DataOut = usb_vcp_class_data_out,
    .SOF = usb_vcp_class_sof,
    .IsoINIncomplete = NULL,
    .IsoOUTIncomplete = NULL,
    .GetHSConfigDescriptor = NULL,
    .GetFSConfigDescriptor = NULL,
    .GetOtherSpeedConfigDescriptor = NULL,
    .GetDeviceQualifierDescriptor = NULL,
    .GetUsrStrDescriptor = NULL,
};

static const USBD_ClassTypeDef usb_vcp_data_class = {};

#endif  // KERNEL_MODE
