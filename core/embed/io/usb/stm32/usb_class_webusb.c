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

#include <trezor_rtl.h>

#include <io/usb_webusb.h>
#include <sec/random_delays.h>
#include <sys/sysevent_source.h>

#ifdef USE_SUSPEND
#include <io/suspend.h>
#endif

#include "usb_internal.h"

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
  syshandle_t handle;
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
static const syshandle_vmt_t usb_webusb_handle_vmt;

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
  state->handle = info->handle;
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

bool usb_webusb_can_read(usb_webusb_state_t *state) {
  if (state->dev_handle == NULL) {
    return false;  // Class driver not initialized
  }
  if (state->last_read_len == 0) {
    return false;  // Nothing in the receiving buffer
  }
  if (state->dev_handle->dev_state != USBD_STATE_CONFIGURED) {
    return false;  // Device is not configured
  }
  return true;
}

bool usb_webusb_can_write(usb_webusb_state_t *state) {
  if (state->dev_handle == NULL) {
    return false;  // Class driver not initialized
  }
  if (state->ep_in_is_idle == 0) {
    return false;  // Last transmission is not over yet
  }
  if (state->dev_handle->dev_state != USBD_STATE_CONFIGURED) {
    return false;  // Device is not configured
  }
  return true;
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

  if (!syshandle_register(state->handle, &usb_webusb_handle_vmt, state)) {
    return USBD_FAIL;
  }

  return USBD_OK;
}

static uint8_t usb_webusb_class_deinit(USBD_HandleTypeDef *dev,
                                       uint8_t cfg_idx) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)dev->pUserData;

  syshandle_unregister(state->handle);

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
#ifdef USE_SUSPEND
    wakeup_flags_set(WAKEUP_FLAG_USB);
#endif
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

static void on_event_poll(void *context, bool read_awaited,
                          bool write_awaited) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)context;

  // Only one task can read or write at a time. Therefore, we can
  // assume that only one task is waiting for events and keep the
  // logic simple.

  if (read_awaited && usb_webusb_can_read(state)) {
    syshandle_signal_read_ready(state->handle, NULL);
  }

  if (write_awaited && usb_webusb_can_write(state)) {
    syshandle_signal_write_ready(state->handle, NULL);
  }
}

static bool on_check_read_ready(void *context, systask_id_t task_id,
                                void *param) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)context;

  UNUSED(task_id);
  UNUSED(param);

  return usb_webusb_can_read(state);
}

static bool on_check_write_ready(void *context, systask_id_t task_id,
                                 void *param) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)context;

  UNUSED(task_id);
  UNUSED(param);

  return usb_webusb_can_write(state);
}

static ssize_t on_read(void *context, void *buffer, size_t buffer_size) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)context;

  if (state->dev_handle == NULL) {
    return -1;  // Class driver not initialized
  }

  // Copy maximum possible amount of data
  uint32_t last_read_len = state->last_read_len;
  if (buffer_size < last_read_len) {
    return 0;  // Not enough data in the read buffer
  }
  memcpy(buffer, state->rx_buffer, last_read_len);

  // Reset the length to indicate we are ready to read next packet
  state->last_read_len = 0;

  // Prepare the OUT EP to receive next packet
  USBD_LL_PrepareReceive(state->dev_handle, state->ep_out, state->rx_buffer,
                         state->max_packet_len);

  return last_read_len;
}

static ssize_t on_write(void *context, const void *data, size_t data_size) {
  usb_webusb_state_t *state = (usb_webusb_state_t *)context;

  if (state->dev_handle == NULL) {
    return -1;  // Class driver not initialized
  }

  if (state->ep_in_is_idle == 0) {
    return 0;  // Last transmission is not over yet
  }

  state->ep_in_is_idle = 0;
  USBD_LL_Transmit(state->dev_handle, state->ep_in, UNCONST(data),
                   (uint16_t)data_size);

  return data_size;
}

static const syshandle_vmt_t usb_webusb_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = on_check_write_ready,
    .poll = on_event_poll,
    .read = on_read,
    .write = on_write,
};

#endif  // KERNEL_MODE
