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

#define USB_CLASS_HID 0x03

#define USB_DESC_TYPE_HID 0x21
#define USB_DESC_TYPE_REPORT 0x22

#define USB_HID_REQ_SET_PROTOCOL 0x0B
#define USB_HID_REQ_GET_PROTOCOL 0x03
#define USB_HID_REQ_SET_IDLE 0x0A
#define USB_HID_REQ_GET_IDLE 0x02

/* usb_hid_add adds and configures new USB HID interface according to
 * configuration options passed in `info`. */
secbool usb_hid_add(const usb_hid_info_t *info) {
  usb_iface_t *iface = usb_get_iface(info->iface_num);

  if (iface == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_DISABLED) {
    return secfalse;  // Interface is already enabled
  }

  usb_hid_descriptor_block_t *d =
      usb_desc_alloc_iface(sizeof(usb_hid_descriptor_block_t));

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
  if (info->report_desc == NULL) {
    return secfalse;
  }

  // Interface descriptor
  d->iface.bLength = sizeof(usb_interface_descriptor_t);
  d->iface.bDescriptorType = USB_DESC_TYPE_INTERFACE;
  d->iface.bInterfaceNumber = info->iface_num;
  d->iface.bAlternateSetting = 0;
  d->iface.bNumEndpoints = 2;
  d->iface.bInterfaceClass = USB_CLASS_HID;
  d->iface.bInterfaceSubClass = info->subclass;
  d->iface.bInterfaceProtocol = info->protocol;
  d->iface.iInterface = USBD_IDX_INTERFACE_STR;

  // HID descriptor
  d->hid.bLength = sizeof(usb_hid_descriptor_t);
  d->hid.bDescriptorType = USB_DESC_TYPE_HID;
  d->hid.bcdHID = 0x0111;      // HID Class Spec release number (1.11)
  d->hid.bCountryCode = 0;     // Hardware target country
  d->hid.bNumDescriptors = 1;  // Number of HID class descriptors
  d->hid.bReportDescriptorType = USB_DESC_TYPE_REPORT;
  d->hid.wReportDescriptorLength = info->report_desc_len;

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
  usb_desc_add_iface(sizeof(usb_hid_descriptor_block_t));

  // Interface state
  iface->type = USB_IFACE_TYPE_HID;
  iface->hid.desc_block = d;
  iface->hid.report_desc = info->report_desc;
  iface->hid.rx_buffer = info->rx_buffer;
  iface->hid.ep_in = info->ep_in;
  iface->hid.ep_out = info->ep_out;
  iface->hid.max_packet_len = info->max_packet_len;
  iface->hid.report_desc_len = info->report_desc_len;
  iface->hid.protocol = 0;
  iface->hid.idle_rate = 0;
  iface->hid.alt_setting = 0;
  iface->hid.last_read_len = 0;
  iface->hid.ep_in_is_idle = 1;

  return sectrue;
}

secbool usb_hid_can_read(uint8_t iface_num) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_HID) {
    return secfalse;  // Invalid interface type
  }
  if (iface->hid.last_read_len == 0) {
    return secfalse;  // Nothing in the receiving buffer
  }
  if (usb_dev_handle.dev_state != USBD_STATE_CONFIGURED) {
    return secfalse;  // Device is not configured
  }
  return sectrue;
}

secbool usb_hid_can_write(uint8_t iface_num) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return secfalse;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_HID) {
    return secfalse;  // Invalid interface type
  }
  if (iface->hid.ep_in_is_idle == 0) {
    return secfalse;  // Last transmission is not over yet
  }
  if (usb_dev_handle.dev_state != USBD_STATE_CONFIGURED) {
    return secfalse;  // Device is not configured
  }
  return sectrue;
}

int usb_hid_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return -1;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_HID) {
    return -2;  // Invalid interface type
  }
  volatile usb_hid_state_t *state = &iface->hid;

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

int usb_hid_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  usb_iface_t *iface = usb_get_iface(iface_num);
  if (iface == NULL) {
    return -1;  // Invalid interface number
  }
  if (iface->type != USB_IFACE_TYPE_HID) {
    return -2;  // Invalid interface type
  }
  volatile usb_hid_state_t *state = &iface->hid;

  if (state->ep_in_is_idle == 0) {
    return 0;  // Last transmission is not over yet
  }

  state->ep_in_is_idle = 0;
  USBD_LL_Transmit(&usb_dev_handle, state->ep_in, UNCONST(buf), (uint16_t)len);

  return len;
}

int usb_hid_read_select(uint32_t timeout) {
  const uint32_t start = HAL_GetTick();
  for (;;) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
      if (sectrue == usb_hid_can_read(i)) {
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

int usb_hid_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                          int timeout) {
  const uint32_t start = HAL_GetTick();
  while (sectrue != usb_hid_can_read(iface_num)) {
    if (timeout >= 0 && HAL_GetTick() - start >= timeout) {
      return 0;  // Timeout
    }
    __WFI();  // Enter sleep mode, waiting for interrupt
  }
  return usb_hid_read(iface_num, buf, len);
}

int usb_hid_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len,
                           int timeout) {
  const uint32_t start = HAL_GetTick();
  while (sectrue != usb_hid_can_write(iface_num)) {
    if (timeout >= 0 && HAL_GetTick() - start >= timeout) {
      return 0;  // Timeout
    }
    __WFI();  // Enter sleep mode, waiting for interrupt
  }
  return usb_hid_write(iface_num, buf, len);
}

static void usb_hid_class_init(USBD_HandleTypeDef *dev, usb_hid_state_t *state,
                               uint8_t cfg_idx) {
  // Open endpoints
  USBD_LL_OpenEP(dev, state->ep_in, USBD_EP_TYPE_INTR, state->max_packet_len);
  USBD_LL_OpenEP(dev, state->ep_out, USBD_EP_TYPE_INTR, state->max_packet_len);

  // Reset the state
  state->protocol = 0;
  state->idle_rate = 0;
  state->alt_setting = 0;
  state->last_read_len = 0;
  state->ep_in_is_idle = 1;

  // Prepare the OUT EP to receive next packet
  USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_buffer,
                         state->max_packet_len);
}

static void usb_hid_class_deinit(USBD_HandleTypeDef *dev,
                                 usb_hid_state_t *state, uint8_t cfg_idx) {
  // Flush endpoints
  USBD_LL_FlushEP(dev, state->ep_in);
  USBD_LL_FlushEP(dev, state->ep_out);
  // Close endpoints
  USBD_LL_CloseEP(dev, state->ep_in);
  USBD_LL_CloseEP(dev, state->ep_out);
}

static int usb_hid_class_setup(USBD_HandleTypeDef *dev, usb_hid_state_t *state,
                               USBD_SetupReqTypedef *req) {
  switch (req->bmRequest & USB_REQ_TYPE_MASK) {
    // Class request
    case USB_REQ_TYPE_CLASS:
      switch (req->bRequest) {
        case USB_HID_REQ_SET_PROTOCOL:
          state->protocol = req->wValue;
          USBD_CtlSendStatus(dev);
          return USBD_OK;

        case USB_HID_REQ_GET_PROTOCOL:
          USBD_CtlSendData(dev, &state->protocol, sizeof(state->protocol));
          return USBD_OK;

        case USB_HID_REQ_SET_IDLE:
          state->idle_rate = req->wValue >> 8;
          USBD_CtlSendStatus(dev);
          return USBD_OK;

        case USB_HID_REQ_GET_IDLE:
          USBD_CtlSendData(dev, &state->idle_rate, sizeof(state->idle_rate));
          return USBD_OK;

        default:
          USBD_CtlError(dev, req);
          return USBD_FAIL;
      }
      break;

    // Interface & Endpoint request
    case USB_REQ_TYPE_STANDARD:
      switch (req->bRequest) {
        case USB_REQ_SET_INTERFACE:
          state->alt_setting = req->wValue;
          USBD_CtlSendStatus(dev);
          return USBD_OK;

        case USB_REQ_GET_INTERFACE:
          USBD_CtlSendData(dev, &state->alt_setting,
                           sizeof(state->alt_setting));
          return USBD_OK;

        case USB_REQ_GET_DESCRIPTOR:
          switch (req->wValue >> 8) {
            case USB_DESC_TYPE_HID:
              USBD_CtlSendData(
                  dev, UNCONST(&state->desc_block->hid),
                  MIN_8bits(req->wLength, sizeof(state->desc_block->hid)));
              return USBD_OK;

            case USB_DESC_TYPE_REPORT:
              USBD_CtlSendData(dev, UNCONST(state->report_desc),
                               MIN_8bits(req->wLength, state->report_desc_len));
              return USBD_OK;

            default:
              USBD_CtlError(dev, req);
              return USBD_FAIL;
          }
          break;

        default:
          USBD_CtlError(dev, req);
          return USBD_FAIL;
      }
      break;
  }

  return USBD_OK;
}

static void usb_hid_class_data_in(USBD_HandleTypeDef *dev,
                                  usb_hid_state_t *state, uint8_t ep_num) {
  if ((ep_num | USB_EP_DIR_IN) == state->ep_in) {
    state->ep_in_is_idle = 1;
  }
}

static void usb_hid_class_data_out(USBD_HandleTypeDef *dev,
                                   usb_hid_state_t *state, uint8_t ep_num) {
  if (ep_num == state->ep_out) {
    // Save the report length to indicate we have read something, but don't
    // schedule next reading until user reads this one
    state->last_read_len = USBD_LL_GetRxDataSize(dev, ep_num);
  }
}
