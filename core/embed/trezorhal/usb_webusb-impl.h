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

#define USB_CLASS_WEBUSB 0xFF

/* usb_webusb_add adds and configures new USB WebUSB interface according to
 * configuration options passed in `info`. */
secbool usb_webusb_add(const usb_webusb_info_t *info) {
  usb_iface_t *iface = usb_get_iface(info->iface_num);

  if (iface == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_DISABLED) {
    return secfalse;  // Interface is already enabled
  }

  usb_webusb_descriptor_block_t *d =
      usb_desc_alloc_iface(sizeof(usb_webusb_descriptor_block_t));

  if (d == NULL) {
    return secfalse;  // Not enough space in the configuration descriptor
  }

  if ((info->ep_in & USB_EP_DIR_MASK) != USB_EP_DIR_IN) {
    return secfalse;  // IN EP is invalid
  }
  if ((info->ep_out & USB_EP_DIR_MASK) != USB_EP_DIR_OUT) {
    return secfalse;  // OUT EP is invalid
  }
  if (info->rx_buffer == NULL) {
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
  d->ep_in.bEndpointAddress = info->ep_in;
  d->ep_in.bmAttributes = USBD_EP_TYPE_INTR;
  d->ep_in.wMaxPacketSize = info->max_packet_len;
  d->ep_in.bInterval = info->polling_interval;

  // OUT endpoint (receiving)
  d->ep_out.bLength = sizeof(usb_endpoint_descriptor_t);
  d->ep_out.bDescriptorType = USB_DESC_TYPE_ENDPOINT;
  d->ep_out.bEndpointAddress = info->ep_out;
  d->ep_out.bmAttributes = USBD_EP_TYPE_INTR;
  d->ep_out.wMaxPacketSize = info->max_packet_len;
  d->ep_out.bInterval = info->polling_interval;

  // Config descriptor
  usb_desc_add_iface(sizeof(usb_webusb_descriptor_block_t));

  // Interface state
  iface->type = USB_IFACE_TYPE_WEBUSB;
  iface->webusb.desc_block = d;
  iface->webusb.rx_buffer = info->rx_buffer;
  iface->webusb.ep_in = info->ep_in;
  iface->webusb.ep_out = info->ep_out;
  iface->webusb.max_packet_len = info->max_packet_len;
  iface->webusb.alt_setting = 0;
  iface->webusb.last_read_len = 0;
  iface->webusb.ep_in_is_idle = 1;

  return sectrue;
}

secbool usb_webusb_can_read(uint8_t iface_num) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_WEBUSB) {
    return secfalse;  // Invalid interface type
  }
  if (iface->webusb.last_read_len == 0) {
    return secfalse;  // Nothing in the receiving buffer
  }
  if (usb_dev_handle.dev_state != USBD_STATE_CONFIGURED) {
    return secfalse;  // Device is not configured
  }
  return sectrue;
}

secbool usb_webusb_can_write(uint8_t iface_num) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_WEBUSB) {
    return secfalse;  // Invalid interface type
  }
  if (iface->webusb.ep_in_is_idle == 0) {
    return secfalse;  // Last transmission is not over yet
  }
  if (usb_dev_handle.dev_state != USBD_STATE_CONFIGURED) {
    return secfalse;  // Device is not configured
  }
  return sectrue;
}

int usb_webusb_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return -1;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_WEBUSB) {
    return -2;  // Invalid interface type
  }
  volatile usb_webusb_state_t *state = &iface->webusb;

  // Copy maximum possible amount of data
  uint32_t last_read_len = state->last_read_len;
  if (len < last_read_len) {
    return 0;  // Not enough data in the read buffer
  }
  memcpy(buf, state->rx_buffer, last_read_len);

  // Reset the length to indicate we are ready to read next packet
  state->last_read_len = 0;

  // Prepare the OUT EP to receive next packet
  USBD_LL_PrepareReceive(&usb_dev_handle, state->ep_out, state->rx_buffer,
                         state->max_packet_len);

  return last_read_len;
}

int usb_webusb_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return -1;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_WEBUSB) {
    return -2;  // Invalid interface type
  }
  volatile usb_webusb_state_t *state = &iface->webusb;

  state->ep_in_is_idle = 0;
  USBD_LL_Transmit(&usb_dev_handle, state->ep_in, UNCONST(buf), (uint16_t)len);

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

static void usb_webusb_class_init(USBD_HandleTypeDef *dev,
                                  usb_webusb_state_t *state, uint8_t cfg_idx) {
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
}

static void usb_webusb_class_deinit(USBD_HandleTypeDef *dev,
                                    usb_webusb_state_t *state,
                                    uint8_t cfg_idx) {
  // Flush endpoints
  USBD_LL_FlushEP(dev, state->ep_in);
  USBD_LL_FlushEP(dev, state->ep_out);
  // Close endpoints
  USBD_LL_CloseEP(dev, state->ep_in);
  USBD_LL_CloseEP(dev, state->ep_out);
}

static int usb_webusb_class_setup(USBD_HandleTypeDef *dev,
                                  usb_webusb_state_t *state,
                                  USBD_SetupReqTypedef *req) {
  if ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_STANDARD) {
    return USBD_OK;
  }

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
}

static void usb_webusb_class_data_in(USBD_HandleTypeDef *dev,
                                     usb_webusb_state_t *state,
                                     uint8_t ep_num) {
  if ((ep_num | USB_EP_DIR_IN) == state->ep_in) {
    state->ep_in_is_idle = 1;
  }
}

static void usb_webusb_class_data_out(USBD_HandleTypeDef *dev,
                                      usb_webusb_state_t *state,
                                      uint8_t ep_num) {
  if (ep_num == state->ep_out) {
    // Save the report length to indicate we have read something, but don't
    // schedule next reading until user reads this one
    state->last_read_len = USBD_LL_GetRxDataSize(dev, ep_num);
  }
}
