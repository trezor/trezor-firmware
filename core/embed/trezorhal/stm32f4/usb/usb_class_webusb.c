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
#include "random_delays.h"

#include "usb_internal.h"
#include "usb_webusb.h"

#define USB_CLASS_WEBUSB 0xFF

typedef struct __attribute__((packed)) {
  usb_interface_descriptor_t iface;
  usb_endpoint_descriptor_t ep_in;
  usb_endpoint_descriptor_t ep_out;
} usb_webusb_descriptor_block_t;

/* usb_webusb_state_t encapsulates all state used by enabled WebUSB interface.
 * It needs to be completely initialized in usb_webusb_add and reset in
 * usb_webusb_class_init.  See usb_webusb_info_t for details of the
 * configuration fields. */
typedef struct {
  USBD_HandleTypeDef *dev_handle;
  const usb_webusb_descriptor_block_t *desc_block;
  uint8_t *rx_buffer;
  uint8_t ep_in;
  uint8_t ep_out;
  uint8_t max_packet_len;

  uint8_t alt_setting;    // For SET_INTERFACE/GET_INTERFACE setup reqs
  uint8_t last_read_len;  // Length of data read into rx_buffer
  uint8_t ep_in_is_idle;  // Set to 1 after IN endpoint gets idle
} usb_webusb_state_t;

_Static_assert(sizeof(usb_webusb_state_t) <= USBD_CLASS_STATE_MAX_SIZE);

// interface dispatch functions
static const USBD_ClassTypeDef usb_webusb_class;

#define usb_get_webusb_state(iface_num) \
  ((usb_webusb_state_t *)usb_get_iface_state(iface_num, &usb_webusb_class))

/* usb_webusb_add adds and configures new USB WebUSB interface according to
 * configuration options passed in `info`. */
secbool usb_webusb_add(const usb_webusb_info_t *info) {
  usb_webusb_state_t *state =
      (usb_webusb_state_t *)usb_get_iface_state(info->iface_num, NULL);

  if (state == NULL) {
    return secfalse;  // Invalid interface number
  }

  usb_webusb_descriptor_block_t *d =
      usb_alloc_class_descriptors(sizeof(usb_webusb_descriptor_block_t));

  if (d == NULL) {
    return secfalse;  // Not enough space in the configuration descriptor
  }

  if (info->rx_buffer == NULL) {
    return secfalse;
  }
  if (info->ep_in >= USBD_MAX_NUM_INTERFACES) {
    return secfalse;
  }
  if (info->ep_out >= USBD_MAX_NUM_INTERFACES) {
    return secfalse;
  }

  // Interface descriptor
  d->iface.bLength = sizeof(usb_interface_descriptor_t);
  d->iface.bDescriptorType = USB_DESC_TYPE_INTERFACE;
  d->iface.bInterfaceNumber = info->iface_num;
  d->iface.bAlternateSetting = 0;
  d->iface.bNumEndpoints = 2;
  d->iface.bInterfaceClass = USB_CLASS_WEBUSB;
  d->iface.bInterfaceSubClass = info->subclass;
  d->iface.bInterfaceProtocol = info->protocol;
  d->iface.iInterface = USBD_IDX_INTERFACE_STR;

  // IN endpoint (sending)
  d->ep_in.bLength = sizeof(usb_endpoint_descriptor_t);
  d->ep_in.bDescriptorType = USB_DESC_TYPE_ENDPOINT;
  d->ep_in.bEndpointAddress = info->ep_in | USB_EP_DIR_IN;
  d->ep_in.bmAttributes = USBD_EP_TYPE_INTR;
  d->ep_in.wMaxPacketSize = info->max_packet_len;
  d->ep_in.bInterval = info->polling_interval;

  // OUT endpoint (receiving)
  d->ep_out.bLength = sizeof(usb_endpoint_descriptor_t);
  d->ep_out.bDescriptorType = USB_DESC_TYPE_ENDPOINT;
  d->ep_out.bEndpointAddress = info->ep_out | USB_EP_DIR_OUT;
  d->ep_out.bmAttributes = USBD_EP_TYPE_INTR;
  d->ep_out.wMaxPacketSize = info->max_packet_len;
  d->ep_out.bInterval = info->polling_interval;

  // Interface state
  state->desc_block = d;
  state->rx_buffer = info->rx_buffer;
  state->ep_in = info->ep_in | USB_EP_DIR_IN;
  state->ep_out = info->ep_out | USB_EP_DIR_OUT;
  state->max_packet_len = info->max_packet_len;
  state->alt_setting = 0;
  state->last_read_len = 0;
  state->ep_in_is_idle = 1;

  usb_set_iface_class(info->iface_num, &usb_webusb_class);

  return sectrue;
}

secbool usb_webusb_can_read(uint8_t iface_num) {
  usb_webusb_state_t *state = usb_get_webusb_state(iface_num);

  if (state == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (state->dev_handle == NULL) {
    return secfalse;  // Class driver not initialized
  }
  if (state->last_read_len == 0) {
    return secfalse;  // Nothing in the receiving buffer
  }
  if (state->dev_handle->dev_state != USBD_STATE_CONFIGURED) {
    return secfalse;  // Device is not configured
  }
  return sectrue;
}

secbool usb_webusb_can_write(uint8_t iface_num) {
  usb_webusb_state_t *state = usb_get_webusb_state(iface_num);
  if (state == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (state->dev_handle == NULL) {
    return secfalse;  // Class driver not initialized
  }
  if (state->ep_in_is_idle == 0) {
    return secfalse;  // Last transmission is not over yet
  }
  if (state->dev_handle->dev_state != USBD_STATE_CONFIGURED) {
    return secfalse;  // Device is not configured
  }
  return sectrue;
}

int usb_webusb_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  volatile usb_webusb_state_t *state = usb_get_webusb_state(iface_num);
  if (state == NULL) {
    return -1;  // Invalid interface number
  }

  if (state->dev_handle == NULL) {
    return -1;  // Class driver not initialized
  }

  // Copy maximum possible amount of data
  uint32_t last_read_len = state->last_read_len;
  if (len < last_read_len) {
    return 0;  // Not enough data in the read buffer
  }
  memcpy(buf, state->rx_buffer, last_read_len);

  // Reset the length to indicate we are ready to read next packet
  state->last_read_len = 0;

  // Prepare the OUT EP to receive next packet
  USBD_LL_PrepareReceive(state->dev_handle, state->ep_out, state->rx_buffer,
                         state->max_packet_len);

  return last_read_len;
}

int usb_webusb_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  volatile usb_webusb_state_t *state = usb_get_webusb_state(iface_num);
  if (state == NULL) {
    return -1;  // Invalid interface number
  }

  if (state->dev_handle == NULL) {
    return -1;  // Class driver not initialized
  }

  state->ep_in_is_idle = 0;
  USBD_LL_Transmit(state->dev_handle, state->ep_in, UNCONST(buf),
                   (uint16_t)len);

  return len;
}

int usb_webusb_read_select(uint32_t timeout) {
  const uint32_t start = HAL_GetTick();
  for (;;) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
      if (sectrue == usb_webusb_can_read(i)) {
        return i;
      }
    }
    if (HAL_GetTick() - start >= timeout) {
      break;
    }
    __WFI();  // Enter sleep mode, waiting for interrupt
  }
  return -1;  // Timeout
}

int usb_webusb_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                             int timeout) {
  const uint32_t start = HAL_GetTick();
  while (sectrue != usb_webusb_can_read(iface_num)) {
    if (timeout >= 0 && HAL_GetTick() - start >= timeout) {
      return 0;  // Timeout
    }
    __WFI();  // Enter sleep mode, waiting for interrupt
  }
  return usb_webusb_read(iface_num, buf, len);
}

int usb_webusb_write_blocking(uint8_t iface_num, const uint8_t *buf,
                              uint32_t len, int timeout) {
  const uint32_t start = HAL_GetTick();
  while (sectrue != usb_webusb_can_write(iface_num)) {
    if (timeout >= 0 && HAL_GetTick() - start >= timeout) {
      return 0;  // Timeout
    }
    __WFI();  // Enter sleep mode, waiting for interrupt
  }
  return usb_webusb_write(iface_num, buf, len);
}

static uint8_t usb_webusb_class_init(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)dev->pUserData;

  state->dev_handle = dev;

  // Open endpoints
  USBD_LL_OpenEP(dev, state->ep_in, USBD_EP_TYPE_INTR, state->max_packet_len);
  USBD_LL_OpenEP(dev, state->ep_out, USBD_EP_TYPE_INTR, state->max_packet_len);

  // Reset the state
  state->alt_setting = 0;
  state->last_read_len = 0;
  state->ep_in_is_idle = 1;

  // Prepare the OUT EP to receive next packet
  USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_buffer,
                         state->max_packet_len);

  return USBD_OK;
}

static uint8_t usb_webusb_class_deinit(USBD_HandleTypeDef *dev,
                                       uint8_t cfg_idx) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)dev->pUserData;

  // Flush endpoints
  USBD_LL_FlushEP(dev, state->ep_in);
  USBD_LL_FlushEP(dev, state->ep_out);
  // Close endpoints
  USBD_LL_CloseEP(dev, state->ep_in);
  USBD_LL_CloseEP(dev, state->ep_out);

  state->dev_handle = NULL;

  return USBD_OK;
}

static uint8_t usb_webusb_class_setup(USBD_HandleTypeDef *dev,
                                      USBD_SetupReqTypedef *req) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)dev->pUserData;

  wait_random();

  if ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_STANDARD) {
    return USBD_OK;
  }

  wait_random();

  switch (req->bRequest) {
    case USB_REQ_SET_INTERFACE:
      state->alt_setting = req->wValue;
      USBD_CtlSendStatus(dev);
      return USBD_OK;

    case USB_REQ_GET_INTERFACE:
      USBD_CtlSendData(dev, &state->alt_setting, sizeof(state->alt_setting));
      return USBD_OK;

    default:
      USBD_CtlError(dev, req);
      return USBD_FAIL;
  }

  return USBD_OK;
}

static uint8_t usb_webusb_class_data_in(USBD_HandleTypeDef *dev,
                                        uint8_t ep_num) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)dev->pUserData;

  if ((ep_num | USB_EP_DIR_IN) == state->ep_in) {
    wait_random();
    state->ep_in_is_idle = 1;
  }

  return USBD_OK;
}

static uint8_t usb_webusb_class_data_out(USBD_HandleTypeDef *dev,
                                         uint8_t ep_num) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)dev->pUserData;

  if (ep_num == state->ep_out) {
    wait_random();
    // Save the report length to indicate we have read something, but don't
    // schedule next reading until user reads this one
    state->last_read_len = USBD_LL_GetRxDataSize(dev, ep_num);
  }

  return USBD_OK;
}

static const USBD_ClassTypeDef usb_webusb_class = {
    .Init = usb_webusb_class_init,
    .DeInit = usb_webusb_class_deinit,
    .Setup = usb_webusb_class_setup,
    .EP0_TxSent = NULL,
    .EP0_RxReady = NULL,
    .DataIn = usb_webusb_class_data_in,
    .DataOut = usb_webusb_class_data_out,
    .SOF = NULL,
    .IsoINIncomplete = NULL,
    .IsoOUTIncomplete = NULL,
    .GetHSConfigDescriptor = NULL,
    .GetFSConfigDescriptor = NULL,
    .GetOtherSpeedConfigDescriptor = NULL,
    .GetDeviceQualifierDescriptor = NULL,
    .GetUsrStrDescriptor = NULL,
};

#endif  // KERNEL_MODE
