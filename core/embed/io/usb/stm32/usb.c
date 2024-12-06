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
#include <trezor_rtl.h>

#include <io/usb.h>
#include <sec/random_delays.h>
#include <sys/systick.h>

#include "usb_internal.h"

#define USB_MAX_CONFIG_DESC_SIZE 256
#define USB_MAX_STR_SIZE 62
#define USB_MAX_STR_DESC_SIZE (USB_MAX_STR_SIZE * 2 + 2)

#if defined(USE_USB_FS)
#define USB_PHY_ID USB_PHY_FS_ID
#elif defined(USE_USB_HS) && defined(USE_USB_HS_IN_FS)
#define USB_PHY_ID USB_PHY_HS_ID
#elif defined(USE_USB_HS) && !defined(USE_USB_HS_IN_FS)
#define USB_PHY_ID USB_PHY_HS_ID
#else
#error Unable to determine proper USB_PHY_ID to use
#endif

typedef struct {
  const char *manufacturer;
  const char *product;
  const char *serial_number;
  const char *interface;
} usb_dev_string_table_t;

typedef struct {
  // USB class dispatch table
  const USBD_ClassTypeDef *class;
  // Internal state for USB class driver
  uint8_t state[USBD_CLASS_STATE_MAX_SIZE] __attribute__((aligned(8)));
} usb_iface_t;

typedef struct {
  // Set if the driver is initialized
  secbool initialized;
  // Handle to the USB device (lower layer driver)
  USBD_HandleTypeDef dev_handle;
  // Device descriptor
  usb_device_descriptor_t dev_desc;
  // Device string descriptors
  usb_dev_string_table_t str_table;
  // Interfaces of registered class drivers
  // (each class driver must add 1 or more interfaces)
  usb_iface_t ifaces[USBD_MAX_NUM_INTERFACES];
  // Buffer for configuration descriptor and additional descriptors
  // (interface, endpoint, ..) added by registered class drivers
  uint8_t desc_buffer[USB_MAX_CONFIG_DESC_SIZE] __attribute__((aligned(4)));
  // Configuration descriptor (located at the beginning of the desc_buffer)
  usb_config_descriptor_t *config_desc;
  // Temporary buffer for unicode strings
  uint8_t str_buf[USB_MAX_STR_DESC_SIZE] __attribute__((aligned(4)));

  secbool usb21_enabled;
  secbool usb21_landing;

  // Time (in ticks) when we've seen the USB ready last time
  uint32_t ready_time;
  // Set to `sectrue` if the USB stack was ready sinced the last start
  secbool was_ready;

  // Current state of USB configuration
  secbool configured;

} usb_driver_t;

// USB driver instance
static usb_driver_t g_usb_driver = {
    .initialized = secfalse,
};

// forward declarations of dispatch functions
static const USBD_ClassTypeDef usb_class;
static const USBD_DescriptorsTypeDef usb_descriptors;

static secbool __wur check_desc_str(const char *s) {
  if (NULL == s) return secfalse;
  if (strlen(s) > USB_MAX_STR_SIZE) return secfalse;
  return sectrue;
}

secbool usb_init(const usb_dev_info_t *dev_info) {
  usb_driver_t *drv = &g_usb_driver;

  if (drv->initialized == sectrue) {
    // Already initialized
    return sectrue;
  }

  memset(drv, 0, sizeof(usb_driver_t));

  // enable/disable USB 2.1 features
  drv->usb21_enabled = dev_info->usb21_enabled;
  drv->usb21_landing = dev_info->usb21_landing;

  // Device descriptor
  drv->dev_desc.bLength = sizeof(usb_device_descriptor_t);
  drv->dev_desc.bDescriptorType = USB_DESC_TYPE_DEVICE;
  // USB 2.1 or USB 2.0
  drv->dev_desc.bcdUSB = (sectrue == drv->usb21_enabled) ? 0x0210 : 0x0200;
  drv->dev_desc.bDeviceClass = dev_info->device_class;
  drv->dev_desc.bDeviceSubClass = dev_info->device_subclass;
  drv->dev_desc.bDeviceProtocol = dev_info->device_protocol;
  drv->dev_desc.bMaxPacketSize0 = USB_MAX_EP0_SIZE;
  drv->dev_desc.idVendor = dev_info->vendor_id;
  drv->dev_desc.idProduct = dev_info->product_id;
  drv->dev_desc.bcdDevice = dev_info->release_num;
  // Index of manufacturer string
  drv->dev_desc.iManufacturer = USBD_IDX_MFC_STR;
  // Index of product string
  drv->dev_desc.iProduct = USBD_IDX_PRODUCT_STR;
  // Index of serial number string
  drv->dev_desc.iSerialNumber = USBD_IDX_SERIAL_STR;
  drv->dev_desc.bNumConfigurations = 1;

  // String table
  if (sectrue != check_desc_str(dev_info->manufacturer)) {
    return secfalse;
  }
  if (sectrue != check_desc_str(dev_info->product)) {
    return secfalse;
  }
  if (sectrue != check_desc_str(dev_info->serial_number)) {
    return secfalse;
  }
  if (sectrue != check_desc_str(dev_info->interface)) {
    return secfalse;
  }

  drv->str_table.manufacturer = dev_info->manufacturer;
  drv->str_table.product = dev_info->product;
  drv->str_table.serial_number = dev_info->serial_number;
  drv->str_table.interface = dev_info->interface;

  drv->config_desc = (usb_config_descriptor_t *)(drv->desc_buffer);

  // Configuration descriptor
  drv->config_desc->bLength = sizeof(usb_config_descriptor_t);
  drv->config_desc->bDescriptorType = USB_DESC_TYPE_CONFIGURATION;
  // will be updated later via usb_alloc_class_descriptors()
  drv->config_desc->wTotalLength = sizeof(usb_config_descriptor_t);
  // will be updated later via usb_set_iface_class()
  drv->config_desc->bNumInterfaces = 0;
  drv->config_desc->bConfigurationValue = 0x01;
  drv->config_desc->iConfiguration = 0;
  // 0x80 = bus powered; 0xC0 = self powered
  drv->config_desc->bmAttributes = 0x80;
  // Maximum Power Consumption in 2mA units
  drv->config_desc->bMaxPower = 0x32;

  // starting with this flag set, to avoid false warnings
  drv->configured = sectrue;
  drv->initialized = sectrue;

  return sectrue;
}

void usb_deinit(void) {
  usb_driver_t *drv = &g_usb_driver;

  if (drv->initialized != sectrue) {
    return;
  }

  usb_stop();

  drv->initialized = secfalse;
}

secbool usb_start(void) {
  usb_driver_t *drv = &g_usb_driver;

  if (drv->initialized != sectrue) {
    // The driver is not initialized
    return secfalse;
  }

  if (drv->dev_handle.dev_state != USBD_STATE_UNINITIALIZED) {
    // The driver has been started already
    return sectrue;
  }

  drv->was_ready = secfalse;

  if (USBD_OK != USBD_Init(&drv->dev_handle,
                           (USBD_DescriptorsTypeDef *)&usb_descriptors,
                           USB_PHY_ID)) {
    usb_stop();
    return secfalse;
  }

  if (USBD_OK !=
      USBD_RegisterClass(&drv->dev_handle, (USBD_ClassTypeDef *)&usb_class)) {
    usb_stop();
    return secfalse;
  }

  if (USBD_OK != USBD_Start(&drv->dev_handle)) {
    usb_stop();
    return secfalse;
  }

  return sectrue;
}

void usb_stop(void) {
  usb_driver_t *drv = &g_usb_driver;

  if (drv->initialized != sectrue) {
    // The driver is not initialized
    return;
  }

  if (drv->dev_handle.dev_state == USBD_STATE_UNINITIALIZED) {
    // The driver is already stopped
    return;
  }

  USBD_DeInit(&drv->dev_handle);

  // Set drv->dev_handle.dev_state to USBD_STATE_INITIALIZED
  memset(&drv->dev_handle, 0, sizeof(drv->dev_handle));
}

static secbool usb_configured(void) {
  usb_driver_t *drv = &g_usb_driver;

  if (drv->initialized != sectrue) {
    // The driver is not initialized
    return secfalse;
  }

  const USBD_HandleTypeDef *pdev = &drv->dev_handle;

  if (pdev->dev_state == USBD_STATE_UNINITIALIZED) {
    // The driver has not been started yet
    return secfalse;
  }

  secbool powered_from_usb = sectrue;  // TODO

  secbool ready = secfalse;

  if (pdev->dev_state == USBD_STATE_CONFIGURED) {
    // USB is configured, ready to transfer data
    ready = sectrue;
  } else if (pdev->dev_state == USBD_STATE_SUSPENDED &&
             pdev->dev_old_state == USBD_STATE_CONFIGURED) {
    // USB is suspended, but was configured before
    //
    // Linux has autosuspend device after 2 seconds by default.
    // So a suspended device that was seen as configured is reported as
    // configured.
    //
    ready = sectrue;
  } else if ((drv->was_ready == secfalse) && (powered_from_usb == sectrue)) {
    // First run after the startup with USB power
    drv->was_ready = sectrue;
    ready = sectrue;
  }

  // This is a workaround to handle the glitches in the USB connection,
  // especially for USB-powered-only devices. This should be
  // revisited and probably fixed elsewhere.

  uint32_t ticks = hal_ticks_ms();

  if (ready == sectrue) {
    drv->ready_time = ticks;
  } else if ((drv->was_ready == sectrue) && (ticks - drv->ready_time) < 2000) {
    // NOTE: When the timer overflows the timeout is shortened.
    //       We are ignoring it for now.
    ready = sectrue;
  }

  return ready;
}

usb_event_t usb_get_event(void) {
  usb_driver_t *drv = &g_usb_driver;

  if (drv->initialized != sectrue) {
    // The driver is not initialized
    return false;
  }

  secbool configured = usb_configured();
  if (configured != drv->configured) {
    drv->configured = configured;
    if (configured == sectrue) {
      return USB_EVENT_CONFIGURED;
    } else {
      return USB_EVENT_DECONFIGURED;
    }
  }

  return USB_EVENT_NONE;
}

void usb_get_state(usb_state_t *state) {
  usb_driver_t *drv = &g_usb_driver;

  usb_state_t s = {0};

  if (drv->initialized == sectrue) {
    s.configured = drv->configured == sectrue;
  }

  *state = s;
}

// ==========================================================================
// Utility functions for USB class drivers
// ==========================================================================

void *usb_get_iface_state(uint8_t iface_num, const USBD_ClassTypeDef *class) {
  usb_driver_t *drv = &g_usb_driver;

  if (iface_num < USBD_MAX_NUM_INTERFACES) {
    usb_iface_t *iface = &drv->ifaces[iface_num];

    if (iface->class == class) {
      return &iface->state;
    }
  }

  // Invalid interface number or type
  return NULL;
}

void usb_set_iface_class(uint8_t iface_num, const USBD_ClassTypeDef *class) {
  usb_driver_t *drv = &g_usb_driver;

  if (iface_num < USBD_MAX_NUM_INTERFACES) {
    if (drv->ifaces[iface_num].class == NULL && class != NULL) {
      drv->config_desc->bNumInterfaces++;
    }

    drv->ifaces[iface_num].class = class;
  }
}

USBD_HandleTypeDef *usb_get_dev_handle(void) {
  usb_driver_t *drv = &g_usb_driver;

  return &drv->dev_handle;
}

void *usb_alloc_class_descriptors(size_t desc_len) {
  usb_driver_t *drv = &g_usb_driver;

  if (drv->config_desc->wTotalLength + desc_len < USB_MAX_CONFIG_DESC_SIZE) {
    void *retval = &drv->desc_buffer[drv->config_desc->wTotalLength];
    drv->config_desc->wTotalLength += desc_len;
    return retval;
  } else {
    return NULL;  // Not enough space in the descriptor
  }
}

// ==========================================================================
// USB configuration (device & string descriptors)
// ==========================================================================

static uint8_t *usb_get_dev_descriptor(USBD_SpeedTypeDef speed,
                                       uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  *length = sizeof(drv->dev_desc);
  return (uint8_t *)(&drv->dev_desc);
}

static uint8_t *usb_get_langid_str_descriptor(USBD_SpeedTypeDef speed,
                                              uint16_t *length) {
  static const usb_langid_descriptor_t usb_langid_str_desc = {
      .bLength = USB_LEN_LANGID_STR_DESC,
      .bDescriptorType = USB_DESC_TYPE_STRING,
      .wData = USB_LANGID_ENGLISH_US,
  };
  *length = sizeof(usb_langid_str_desc);
  return UNCONST(&usb_langid_str_desc);
}

static uint8_t *usb_get_manufacturer_str_descriptor(USBD_SpeedTypeDef speed,
                                                    uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  USBD_GetString((uint8_t *)drv->str_table.manufacturer, drv->str_buf, length);
  return drv->str_buf;
}

static uint8_t *usb_get_product_str_descriptor(USBD_SpeedTypeDef speed,
                                               uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  USBD_GetString((uint8_t *)drv->str_table.product, drv->str_buf, length);
  return drv->str_buf;
}

static uint8_t *usb_get_serial_str_descriptor(USBD_SpeedTypeDef speed,
                                              uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  USBD_GetString((uint8_t *)drv->str_table.serial_number, drv->str_buf, length);
  return drv->str_buf;
}

static uint8_t *usb_get_configuration_str_descriptor(USBD_SpeedTypeDef speed,
                                                     uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  USBD_GetString((uint8_t *)"", drv->str_buf, length);
  return drv->str_buf;
}

static uint8_t *usb_get_interface_str_descriptor(USBD_SpeedTypeDef speed,
                                                 uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  USBD_GetString((uint8_t *)drv->str_table.interface, drv->str_buf, length);
  return drv->str_buf;
}

static uint8_t *usb_get_bos_descriptor(USBD_SpeedTypeDef speed,
                                       uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  if (sectrue == drv->usb21_enabled) {
    static uint8_t bos[] = {
        // usb_bos_descriptor {
        0x05,               // uint8_t  bLength
        USB_DESC_TYPE_BOS,  // uint8_t  bDescriptorType
        0x1d, 0x0,          // uint16_t wTotalLength
        0x01,               // uint8_t  bNumDeviceCaps
        // }
        // usb_device_capability_descriptor {
        0x18,                             // uint8_t  bLength
        USB_DESC_TYPE_DEVICE_CAPABILITY,  // uint8_t  bDescriptorType
        USB_DEVICE_CAPABILITY_PLATFORM,   // uint8_t  bDevCapabilityType
        0x00,                             // uint8_t  bReserved
        0x38, 0xb6, 0x08, 0x34, 0xa9, 0x09, 0xa0, 0x47, 0x8b, 0xfd, 0xa0, 0x76,
        0x88, 0x15, 0xb6, 0x65,   // uint128_t platformCompatibilityUUID
        0x00, 0x01,               // uint16_t bcdVersion
        USB_WEBUSB_VENDOR_CODE,   // uint8_t  bVendorCode
        USB_WEBUSB_LANDING_PAGE,  // uint8_t  iLandingPage
                                  // }
    };
    bos[28] = (sectrue == drv->usb21_landing) ? USB_WEBUSB_LANDING_PAGE : 0;
    *length = sizeof(bos);
    return UNCONST(bos);
  } else {
    *length = 0;
    return NULL;
  }
}

static const USBD_DescriptorsTypeDef usb_descriptors = {
    .GetDeviceDescriptor = usb_get_dev_descriptor,
    .GetLangIDStrDescriptor = usb_get_langid_str_descriptor,
    .GetManufacturerStrDescriptor = usb_get_manufacturer_str_descriptor,
    .GetProductStrDescriptor = usb_get_product_str_descriptor,
    .GetSerialStrDescriptor = usb_get_serial_str_descriptor,
    .GetConfigurationStrDescriptor = usb_get_configuration_str_descriptor,
    .GetInterfaceStrDescriptor = usb_get_interface_str_descriptor,
    .GetBOSDescriptor = usb_get_bos_descriptor,
};

// ==========================================================================
// USB class (interface dispatch, configuration descriptor)
// ==========================================================================

#define USB_WINUSB_VENDOR_CODE \
  '!'  // arbitrary, but must be equivalent to the last character in extra
       // string
#define USB_WINUSB_EXTRA_STRING                                                \
  'M', 0x00, 'S', 0x00, 'F', 0x00, 'T', 0x00, '1', 0x00, '0', 0x00, '0', 0x00, \
      USB_WINUSB_VENDOR_CODE, 0x00  // MSFT100!
#define USB_WINUSB_EXTRA_STRING_INDEX 0xEE
#define USB_WINUSB_REQ_GET_COMPATIBLE_ID_FEATURE_DESCRIPTOR 0x04
#define USB_WINUSB_REQ_GET_EXTENDED_PROPERTIES_OS_FEATURE_DESCRIPTOR 0x05

static uint8_t usb_class_init(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
  usb_driver_t *drv = &g_usb_driver;

  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &drv->ifaces[i];
    if (iface->class != NULL && iface->class->Init != NULL) {
      dev->pUserData = iface->state;
      iface->class->Init(dev, cfg_idx);
    }
  }

  dev->pUserData = NULL;

  return USBD_OK;
}

static uint8_t usb_class_deinit(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
  usb_driver_t *drv = &g_usb_driver;

  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &drv->ifaces[i];
    if (iface->class != NULL && iface->class->DeInit != NULL) {
      dev->pUserData = iface->state;
      iface->class->DeInit(dev, cfg_idx);
    }
  }

  dev->pUserData = NULL;

  return USBD_OK;
}

#define USB_WEBUSB_REQ_GET_URL 0x02
#define USB_WEBUSB_DESCRIPTOR_TYPE_URL 0x03
#define USB_WEBUSB_URL_SCHEME_HTTP 0
#define USB_WEBUSB_URL_SCHEME_HTTPS 1

static uint8_t usb_class_setup(USBD_HandleTypeDef *dev,
                               USBD_SetupReqTypedef *req) {
  usb_driver_t *drv = &g_usb_driver;

  if (((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_CLASS) &&
      ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_STANDARD) &&
      ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_VENDOR)) {
    return USBD_OK;
  }

  if ((req->bmRequest & USB_REQ_TYPE_MASK) == USB_REQ_TYPE_VENDOR) {
    if ((req->bmRequest & USB_REQ_RECIPIENT_MASK) == USB_REQ_RECIPIENT_DEVICE) {
      if (sectrue == drv->usb21_enabled &&
          req->bRequest == USB_WEBUSB_VENDOR_CODE) {
        if (req->wIndex == USB_WEBUSB_REQ_GET_URL &&
            req->wValue == USB_WEBUSB_LANDING_PAGE) {
          static const char webusb_url[] = {
              3 + 15,                          // uint8_t bLength
              USB_WEBUSB_DESCRIPTOR_TYPE_URL,  // uint8_t bDescriptorType
              USB_WEBUSB_URL_SCHEME_HTTPS,     // uint8_t bScheme
              't',
              'r',
              'e',
              'z',
              'o',
              'r',
              '.',
              'i',
              'o',
              '/',
              's',
              't',
              'a',
              'r',
              't',  // char URL[]
          };
          wait_random();
          USBD_CtlSendData(dev, UNCONST(webusb_url),
                           MIN_8bits(req->wLength, sizeof(webusb_url)));
          return USBD_OK;
        } else {
          wait_random();
          USBD_CtlError(dev, req);
          return USBD_FAIL;
        }
      } else if (sectrue == drv->usb21_enabled &&
                 req->bRequest == USB_WINUSB_VENDOR_CODE) {
        if (req->wIndex ==
            USB_WINUSB_REQ_GET_COMPATIBLE_ID_FEATURE_DESCRIPTOR) {
          static const uint8_t winusb_wcid[] = {
              // header
              0x28, 0x00, 0x00, 0x00,                    // dwLength
              0x00, 0x01,                                // bcdVersion
              0x04, 0x00,                                // wIndex
              0x01,                                      // bNumSections
              0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // reserved
              // functions
              0x00,  // bInterfaceNumber - HACK: we present only interface 0 as
                     // WinUSB
              0x01,  // reserved
              'W', 'I', 'N', 'U', 'S', 'B', 0x00, 0x00,  // compatibleId
              0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
              0x00,                                // subCompatibleId
              0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // reserved
          };
          wait_random();
          USBD_CtlSendData(dev, UNCONST(winusb_wcid),
                           MIN_8bits(req->wLength, sizeof(winusb_wcid)));
          return USBD_OK;
        } else {
          wait_random();
          USBD_CtlError(dev, req);
          return USBD_FAIL;
        }
      }
    }
    if ((req->bmRequest & USB_REQ_RECIPIENT_MASK) ==
        USB_REQ_RECIPIENT_INTERFACE) {
      if (sectrue == drv->usb21_enabled &&
          req->bRequest == USB_WINUSB_VENDOR_CODE) {
        if (req->wIndex ==
                USB_WINUSB_REQ_GET_EXTENDED_PROPERTIES_OS_FEATURE_DESCRIPTOR &&
            (req->wValue & 0xFF) == 0) {  // reply only if interface is 0
          static const uint8_t winusb_guid[] = {
              // header
              0x92, 0x00, 0x00, 0x00,  // dwLength
              0x00, 0x01,              // bcdVersion
              0x05, 0x00,              // wIndex
              0x01, 0x00,              // wNumFeatures
              // features
              0x88, 0x00, 0x00, 0x00,  // dwLength
              0x07, 0x00, 0x00, 0x00,  // dwPropertyDataType
              0x2A, 0x00,              // wNameLength
              'D', 0x00, 'e', 0x00, 'v', 0x00, 'i', 0x00, 'c', 0x00, 'e', 0x00,
              'I', 0x00, 'n', 0x00, 't', 0x00, 'e', 0x00, 'r', 0x00, 'f', 0x00,
              'a', 0x00, 'c', 0x00, 'e', 0x00, 'G', 0x00, 'U', 0x00, 'I', 0x00,
              'D', 0x00, 's', 0x00, 0x00, 0x00,  // .name
              0x50, 0x00, 0x00, 0x00,            // dwPropertyDataLength
              '{', 0x00, 'c', 0x00, '6', 0x00, 'c', 0x00, '3', 0x00, '7', 0x00,
              '4', 0x00, 'a', 0x00, '6', 0x00, '-', 0x00, '2', 0x00, '2', 0x00,
              '8', 0x00, '5', 0x00, '-', 0x00, '4', 0x00, 'c', 0x00, 'b', 0x00,
              '8', 0x00, '-', 0x00, 'a', 0x00, 'b', 0x00, '4', 0x00, '3', 0x00,
              '-', 0x00, '1', 0x00, '7', 0x00, '6', 0x00, '4', 0x00, '7', 0x00,
              'c', 0x00, 'e', 0x00, 'a', 0x00, '5', 0x00, '0', 0x00, '3', 0x00,
              'd', 0x00, '}', 0x00, 0x00, 0x00, 0x00, 0x00,  // propertyData
          };
          wait_random();
          USBD_CtlSendData(dev, UNCONST(winusb_guid),
                           MIN_8bits(req->wLength, sizeof(winusb_guid)));
          return USBD_OK;
        } else {
          wait_random();
          USBD_CtlError(dev, req);
          return USBD_FAIL;
        }
      }
    }
  } else if ((req->bmRequest & USB_REQ_RECIPIENT_MASK) ==
             USB_REQ_RECIPIENT_INTERFACE) {
    if (req->wIndex >= USBD_MAX_NUM_INTERFACES) {
      wait_random();
      USBD_CtlError(dev, req);
      return USBD_FAIL;
    }

    usb_iface_t *iface = &drv->ifaces[req->wIndex];
    if (iface->class != NULL && iface->class->Setup != NULL) {
      dev->pUserData = iface->state;
      iface->class->Setup(dev, req);
      dev->pUserData = NULL;
    } else {
      wait_random();
      USBD_CtlError(dev, req);
      return USBD_FAIL;
    }
  }
  return USBD_OK;
}

static uint8_t usb_class_data_in(USBD_HandleTypeDef *dev, uint8_t ep_num) {
  usb_driver_t *drv = &g_usb_driver;

#ifdef RDI
  random_delays_refresh_rdi();
#endif

  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &drv->ifaces[i];
    if (iface->class != NULL && iface->class->DataIn != NULL) {
      dev->pUserData = iface->state;
      iface->class->DataIn(dev, ep_num);
    }
  }

  dev->pUserData = NULL;

  return USBD_OK;
}

static uint8_t usb_class_data_out(USBD_HandleTypeDef *dev, uint8_t ep_num) {
  usb_driver_t *drv = &g_usb_driver;

#ifdef RDI
  random_delays_refresh_rdi();
#endif

  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &drv->ifaces[i];
    if (iface->class != NULL && iface->class->DataOut != NULL) {
      dev->pUserData = iface->state;
      iface->class->DataOut(dev, ep_num);
    }
  }

  dev->pUserData = NULL;

  return USBD_OK;
}

static uint8_t usb_class_sof(USBD_HandleTypeDef *dev) {
  usb_driver_t *drv = &g_usb_driver;

  for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
    usb_iface_t *iface = &drv->ifaces[i];
    if (iface->class != NULL && iface->class->SOF != NULL) {
      dev->pUserData = iface->state;
      iface->class->SOF(dev);
    }
  }

  dev->pUserData = NULL;

  return USBD_OK;
}

static uint8_t *usb_class_get_cfg_desc(uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  *length = drv->config_desc->wTotalLength;
  return drv->desc_buffer;
}

static uint8_t *usb_class_get_usrstr_desc(USBD_HandleTypeDef *dev,
                                          uint8_t index, uint16_t *length) {
  usb_driver_t *drv = &g_usb_driver;

  if (sectrue == drv->usb21_enabled && index == USB_WINUSB_EXTRA_STRING_INDEX) {
    static const uint8_t winusb_string_descriptor[] = {
        0x12,                    // bLength
        USB_DESC_TYPE_STRING,    // bDescriptorType
        USB_WINUSB_EXTRA_STRING  // wData
    };
    *length = sizeof(winusb_string_descriptor);
    return UNCONST(winusb_string_descriptor);
  } else {
    *length = 0;
    return NULL;
  }
}

static const USBD_ClassTypeDef usb_class = {
    .Init = usb_class_init,
    .DeInit = usb_class_deinit,
    .Setup = usb_class_setup,
    .EP0_TxSent = NULL,
    .EP0_RxReady = NULL,
    .DataIn = usb_class_data_in,
    .DataOut = usb_class_data_out,
    .SOF = usb_class_sof,
    .IsoINIncomplete = NULL,
    .IsoOUTIncomplete = NULL,
    .GetHSConfigDescriptor = usb_class_get_cfg_desc,
    .GetFSConfigDescriptor = usb_class_get_cfg_desc,
    .GetOtherSpeedConfigDescriptor = usb_class_get_cfg_desc,
    .GetDeviceQualifierDescriptor = NULL,
    .GetUsrStrDescriptor = usb_class_get_usrstr_desc,
};

#endif  // KERNEL_MODE
