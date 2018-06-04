/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include STM32_HAL_H

#include "common.h"
#include "usb.h"
#include "usbd_core.h"

#define USB_MAX_CONFIG_DESC_SIZE    256
#define USB_MAX_STR_SIZE            62
#define USB_MAX_STR_DESC_SIZE       (USB_MAX_STR_SIZE * 2 + 2)

#if defined(USE_USB_FS)
#define USB_PHY_ID  USB_PHY_FS_ID
#elif defined(USE_USB_HS) && defined(USE_USB_HS_IN_FS)
#define USB_PHY_ID  USB_PHY_HS_ID
#else
#error Unable to determine proper USB_PHY_ID to use
#endif

#define USB_WINUSB_VENDOR_CODE          '!'  // arbitrary, but must be equivalent to the last character in extra string
#define USB_WINUSB_EXTRA_STRING         'M', 0x00, 'S', 0x00, 'F', 0x00, 'T', 0x00, '1', 0x00, '0', 0x00, '0', 0x00, USB_WINUSB_VENDOR_CODE , 0x00  // MSFT100!
#define USB_WINUSB_EXTRA_STRING_INDEX   0xEE
#define USB_WINUSB_REQ_GET_COMPATIBLE_ID_FEATURE_DESCRIPTOR             0x04
#define USB_WINUSB_REQ_GET_EXTENDED_PROPERTIES_OS_FEATURE_DESCRIPTOR    0x05

#define UNCONST(X) ((uint8_t *)(X))

static usb_device_descriptor_t usb_dev_desc;

// Config descriptor
static uint8_t usb_config_buf[USB_MAX_CONFIG_DESC_SIZE] __attribute__((aligned(4)));
static usb_config_descriptor_t *usb_config_desc = (usb_config_descriptor_t *)(usb_config_buf);
static usb_interface_descriptor_t *usb_next_iface_desc;

// String descriptor
static uint8_t usb_str_buf[USB_MAX_STR_DESC_SIZE] __attribute__((aligned(4)));
static usb_dev_string_table_t usb_str_table;

static usb_iface_t usb_ifaces[USBD_MAX_NUM_INTERFACES];

static USBD_HandleTypeDef usb_dev_handle;
static const USBD_DescriptorsTypeDef usb_descriptors;
static const USBD_ClassTypeDef usb_class;

static secbool usb21_enabled = secfalse;
static secbool usb21_landing = secfalse;

static secbool __wur check_desc_str(const char *s) {
    if (NULL == s) return secfalse;
    if (strlen(s) > USB_MAX_STR_SIZE) return secfalse;
    return sectrue;
}

void usb_init(const usb_dev_info_t *dev_info) {

    // enable/disable USB 2.1 features
    usb21_enabled = dev_info->usb21_enabled;
    usb21_landing = dev_info->usb21_landing;

    // Device descriptor
    usb_dev_desc.bLength            = sizeof(usb_device_descriptor_t);
    usb_dev_desc.bDescriptorType    = USB_DESC_TYPE_DEVICE;
    usb_dev_desc.bcdUSB             = (sectrue == usb21_enabled) ? 0x0210 : 0x0200;  // USB 2.1 or USB 2.0
    usb_dev_desc.bDeviceClass       = dev_info->device_class;
    usb_dev_desc.bDeviceSubClass    = dev_info->device_subclass;
    usb_dev_desc.bDeviceProtocol    = dev_info->device_protocol;
    usb_dev_desc.bMaxPacketSize0    = USB_MAX_EP0_SIZE;
    usb_dev_desc.idVendor           = dev_info->vendor_id;
    usb_dev_desc.idProduct          = dev_info->product_id;
    usb_dev_desc.bcdDevice          = dev_info->release_num;
    usb_dev_desc.iManufacturer      = USBD_IDX_MFC_STR;      // Index of manufacturer string
    usb_dev_desc.iProduct           = USBD_IDX_PRODUCT_STR;  // Index of product string
    usb_dev_desc.iSerialNumber      = USBD_IDX_SERIAL_STR;   // Index of serial number string
    usb_dev_desc.bNumConfigurations = 1;

    // String table
    ensure(check_desc_str(dev_info->manufacturer), NULL);
    ensure(check_desc_str(dev_info->product), NULL);
    ensure(check_desc_str(dev_info->serial_number), NULL);
    ensure(check_desc_str(dev_info->interface), NULL);

    usb_str_table.manufacturer  = dev_info->manufacturer;
    usb_str_table.product       = dev_info->product;
    usb_str_table.serial_number = dev_info->serial_number;
    usb_str_table.interface     = dev_info->interface;

    // Configuration descriptor
    usb_config_desc->bLength             = sizeof(usb_config_descriptor_t);
    usb_config_desc->bDescriptorType     = USB_DESC_TYPE_CONFIGURATION;
    usb_config_desc->wTotalLength        = sizeof(usb_config_descriptor_t); // will be updated later via usb_desc_add_iface()
    usb_config_desc->bNumInterfaces      = 0;                               // will be updated later via usb_desc_add_iface()
    usb_config_desc->bConfigurationValue = 0x01;
    usb_config_desc->iConfiguration      = 0;
    usb_config_desc->bmAttributes        = 0x80; // 0x80 = bus powered; 0xC0 = self powered
    usb_config_desc->bMaxPower           = 0x32; // Maximum Power Consumption in 2mA units

    // Pointer to interface descriptor data
    usb_next_iface_desc = (usb_interface_descriptor_t *)(usb_config_buf + usb_config_desc->wTotalLength);

    ensure(sectrue * (USBD_OK == USBD_Init(&usb_dev_handle, (USBD_DescriptorsTypeDef*)&usb_descriptors, USB_PHY_ID)), NULL);
    ensure(sectrue * (USBD_OK == USBD_RegisterClass(&usb_dev_handle, (USBD_ClassTypeDef*)&usb_class)), NULL);
}

void usb_deinit(void) {
    USBD_DeInit(&usb_dev_handle);
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
        usb_ifaces[i].type = USB_IFACE_TYPE_DISABLED;
    }
}

void usb_start(void) {
    USBD_Start(&usb_dev_handle);
}

void usb_stop(void) {
    USBD_Stop(&usb_dev_handle);
}

/*
 * Utility functions for USB interfaces
 */

static usb_iface_t *usb_get_iface(uint8_t iface_num) {
    if (iface_num < USBD_MAX_NUM_INTERFACES) {
        return &usb_ifaces[iface_num];
    } else {
        return NULL; // Invalid interface number
    }
}

static void *usb_desc_alloc_iface(size_t desc_len) {
    if (usb_config_desc->wTotalLength + desc_len < USB_MAX_CONFIG_DESC_SIZE) {
        return usb_next_iface_desc;
    } else {
        return NULL; // Not enough space in the descriptor
    }
}

static void usb_desc_add_iface(size_t desc_len) {
    usb_config_desc->bNumInterfaces++;
    usb_config_desc->wTotalLength += desc_len;
    usb_next_iface_desc = (usb_interface_descriptor_t *)(usb_config_buf + usb_config_desc->wTotalLength);
}

static uint8_t usb_ep_set_nak(USBD_HandleTypeDef *dev, uint8_t ep_num) {
    PCD_HandleTypeDef *hpcd = dev->pData;
    USB_OTG_GlobalTypeDef *USBx = hpcd->Instance;
    USBx_OUTEP(ep_num)->DOEPCTL |= USB_OTG_DOEPCTL_SNAK;
    return USBD_OK;
}

static uint8_t usb_ep_clear_nak(USBD_HandleTypeDef *dev, uint8_t ep_num) {
    PCD_HandleTypeDef *hpcd = dev->pData;
    USB_OTG_GlobalTypeDef *USBx = hpcd->Instance;
    USBx_OUTEP(ep_num)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
    return USBD_OK;
}

/*
 * USB interface implementations
 */

#include "usb_hid-impl.h"
#include "usb_vcp-impl.h"
#include "usb_webusb-impl.h"

/*
 * USB configuration (device & string descriptors)
 */

static uint8_t *usb_get_dev_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    *length = sizeof(usb_dev_desc);
    return (uint8_t *)(&usb_dev_desc);
}

static uint8_t *usb_get_langid_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    static const usb_langid_descriptor_t usb_langid_str_desc = {
        .bLength         = USB_LEN_LANGID_STR_DESC,
        .bDescriptorType = USB_DESC_TYPE_STRING,
        .wData           = USB_LANGID_ENGLISH_US,
    };
    *length = sizeof(usb_langid_str_desc);
    return UNCONST(&usb_langid_str_desc);
}

static uint8_t *usb_get_manufacturer_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.manufacturer, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_product_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.product, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_serial_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.serial_number, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_configuration_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)"", usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_interface_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.interface, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_bos_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    if (sectrue == usb21_enabled) {
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
            0x38, 0xb6, 0x08, 0x34, 0xa9, 0x09, 0xa0, 0x47, 0x8b, 0xfd, 0xa0, 0x76, 0x88, 0x15, 0xb6, 0x65,  // uint128_t platformCompatibilityUUID
            0x00, 0x01,                       // uint16_t bcdVersion
            USB_WEBUSB_VENDOR_CODE,           // uint8_t  bVendorCode
            USB_WEBUSB_LANDING_PAGE,          // uint8_t  iLandingPage
            // }
        };
        bos[28] = (sectrue == usb21_landing) ? USB_WEBUSB_LANDING_PAGE : 0;
        *length = sizeof(bos);
        return UNCONST(bos);
    } else {
        *length = 0;
        return NULL;
    }
}

static const USBD_DescriptorsTypeDef usb_descriptors = {
    .GetDeviceDescriptor           = usb_get_dev_descriptor,
    .GetLangIDStrDescriptor        = usb_get_langid_str_descriptor,
    .GetManufacturerStrDescriptor  = usb_get_manufacturer_str_descriptor,
    .GetProductStrDescriptor       = usb_get_product_str_descriptor,
    .GetSerialStrDescriptor        = usb_get_serial_str_descriptor,
    .GetConfigurationStrDescriptor = usb_get_configuration_str_descriptor,
    .GetInterfaceStrDescriptor     = usb_get_interface_str_descriptor,
    .GetBOSDescriptor              = usb_get_bos_descriptor,
};

/*
 * USB class (interface dispatch, configuration descriptor)
 */

static uint8_t usb_class_init(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
        switch (usb_ifaces[i].type) {
            case USB_IFACE_TYPE_HID:
                usb_hid_class_init(dev, &usb_ifaces[i].hid, cfg_idx);
                break;
            case USB_IFACE_TYPE_VCP:
                usb_vcp_class_init(dev, &usb_ifaces[i].vcp, cfg_idx);
                break;
            case USB_IFACE_TYPE_WEBUSB:
                usb_webusb_class_init(dev, &usb_ifaces[i].webusb, cfg_idx);
                break;
            default:
                break;
        }
    }
    return USBD_OK;
}

static uint8_t usb_class_deinit(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
        switch (usb_ifaces[i].type) {
            case USB_IFACE_TYPE_HID:
                usb_hid_class_deinit(dev, &usb_ifaces[i].hid, cfg_idx);
                break;
            case USB_IFACE_TYPE_VCP:
                usb_vcp_class_deinit(dev, &usb_ifaces[i].vcp, cfg_idx);
                break;
            case USB_IFACE_TYPE_WEBUSB:
                usb_webusb_class_deinit(dev, &usb_ifaces[i].webusb, cfg_idx);
                break;
            default:
                break;
        }
    }
    return USBD_OK;
}

#define USB_WEBUSB_REQ_GET_URL          0x02
#define USB_WEBUSB_DESCRIPTOR_TYPE_URL  0x03
#define USB_WEBUSB_URL_SCHEME_HTTP      0
#define USB_WEBUSB_URL_SCHEME_HTTPS     1

static uint8_t usb_class_setup(USBD_HandleTypeDef *dev, USBD_SetupReqTypedef *req) {
    if (((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_CLASS) &&
        ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_STANDARD) &&
        ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_VENDOR)) {
        return USBD_OK;
    }

    if ((req->bmRequest & USB_REQ_TYPE_MASK) == USB_REQ_TYPE_VENDOR) {
        if ((req->bmRequest & USB_REQ_RECIPIENT_MASK) == USB_REQ_RECIPIENT_DEVICE) {
            if (sectrue == usb21_enabled && req->bRequest == USB_WEBUSB_VENDOR_CODE) {
                if (req->wIndex == USB_WEBUSB_REQ_GET_URL && req->wValue == USB_WEBUSB_LANDING_PAGE) {
                    static const char webusb_url[] = {
                        3 + 15,                             // uint8_t bLength
                        USB_WEBUSB_DESCRIPTOR_TYPE_URL,     // uint8_t bDescriptorType
                        USB_WEBUSB_URL_SCHEME_HTTPS,        // uint8_t bScheme
                        't', 'r', 'e', 'z', 'o', 'r', '.', 'i', 'o', '/', 's', 't', 'a', 'r', 't',  // char URL[]
                    };
                    USBD_CtlSendData(dev, UNCONST(webusb_url), MIN(req->wLength, sizeof(webusb_url)));
                    return USBD_OK;
                } else {
                    USBD_CtlError(dev, req);
                    return USBD_FAIL;
                }
            }
            else
            if (sectrue == usb21_enabled && req->bRequest == USB_WINUSB_VENDOR_CODE) {
                if (req->wIndex == USB_WINUSB_REQ_GET_COMPATIBLE_ID_FEATURE_DESCRIPTOR) {
                    static const uint8_t winusb_wcid[] = {
                        // header
                        0x28, 0x00, 0x00, 0x00, // dwLength
                        0x00, 0x01,             // bcdVersion
                        0x04, 0x00,             // wIndex
                        0x01,                   // bNumSections
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // reserved
                        // functions
                        0x00,                   // bInterfaceNumber - HACK: we present only interface 0 as WinUSB
                        0x01,                   // reserved
                        'W', 'I', 'N', 'U', 'S', 'B', 0x00, 0x00,       // compatibleId
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // subCompatibleId
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00,             // reserved
                    };
                    USBD_CtlSendData(dev, UNCONST(winusb_wcid), MIN(req->wLength, sizeof(winusb_wcid)));
                    return USBD_OK;
                } else {
                    USBD_CtlError(dev, req);
                    return USBD_FAIL;
                }
            }
        }
        if ((req->bmRequest & USB_REQ_RECIPIENT_MASK) == USB_REQ_RECIPIENT_INTERFACE) {
            if (sectrue == usb21_enabled && req->bRequest == USB_WINUSB_VENDOR_CODE) {
                if (req->wIndex == USB_WINUSB_REQ_GET_EXTENDED_PROPERTIES_OS_FEATURE_DESCRIPTOR &&
                    (req->wValue & 0xFF) == 0) {    // reply only if interface is 0
                    static const uint8_t winusb_guid[] = {
                        // header
                        0x92, 0x00, 0x00, 0x00, // dwLength
                        0x00, 0x01,             // bcdVersion
                        0x05, 0x00,             // wIndex
                        0x01, 0x00,             // wNumFeatures
                        // features
                        0x88, 0x00, 0x00, 0x00, // dwLength
                        0x07, 0x00, 0x00, 0x00, // dwPropertyDataType
                        0x2A, 0x00,             // wNameLength
                        'D', 0x00, 'e', 0x00, 'v', 0x00, 'i', 0x00, 'c', 0x00, 'e', 0x00, 'I', 0x00, 'n', 0x00, 't', 0x00, 'e', 0x00, 'r', 0x00, 'f', 0x00, 'a', 0x00, 'c', 0x00, 'e', 0x00, 'G', 0x00, 'U', 0x00, 'I', 0x00, 'D', 0x00, 's', 0x00, 0x00, 0x00, // .name
                        0x50, 0x00, 0x00, 0x00, // dwPropertyDataLength
                        '{', 0x00, 'c', 0x00, '6', 0x00, 'c', 0x00, '3', 0x00, '7', 0x00, '4', 0x00, 'a', 0x00, '6', 0x00, '-', 0x00, '2', 0x00, '2', 0x00, '8', 0x00, '5', 0x00, '-', 0x00, '4', 0x00, 'c', 0x00, 'b', 0x00, '8', 0x00, '-', 0x00, 'a', 0x00, 'b', 0x00, '4', 0x00, '3', 0x00, '-', 0x00, '1', 0x00, '7', 0x00, '6', 0x00, '4', 0x00, '7', 0x00, 'c', 0x00, 'e', 0x00, 'a', 0x00, '5', 0x00, '0', 0x00, '3', 0x00, 'd', 0x00, '}', 0x00, 0x00, 0x00, 0x00, 0x00,  // propertyData
                    };
                    USBD_CtlSendData(dev, UNCONST(winusb_guid), MIN(req->wLength, sizeof(winusb_guid)));
                    return USBD_OK;
                } else {
                    USBD_CtlError(dev, req);
                    return USBD_FAIL;
                }
            }
        }
    } else
    if ((req->bmRequest & USB_REQ_RECIPIENT_MASK) == USB_REQ_RECIPIENT_INTERFACE) {
        if (req->wIndex >= USBD_MAX_NUM_INTERFACES) {
            USBD_CtlError(dev, req);
            return USBD_FAIL;
        }
        switch (usb_ifaces[req->wIndex].type) {
            case USB_IFACE_TYPE_HID:
                return usb_hid_class_setup(dev, &usb_ifaces[req->wIndex].hid, req);
            case USB_IFACE_TYPE_VCP:
                return usb_vcp_class_setup(dev, &usb_ifaces[req->wIndex].vcp, req);
            case USB_IFACE_TYPE_WEBUSB:
                return usb_webusb_class_setup(dev, &usb_ifaces[req->wIndex].webusb, req);
            default:
                USBD_CtlError(dev, req);
                return USBD_FAIL;
        }
    }
    return USBD_OK;
}

static uint8_t usb_class_data_in(USBD_HandleTypeDef *dev, uint8_t ep_num) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
        switch (usb_ifaces[i].type) {
            case USB_IFACE_TYPE_HID:
                usb_hid_class_data_in(dev, &usb_ifaces[i].hid, ep_num);
                break;
            case USB_IFACE_TYPE_VCP:
                usb_vcp_class_data_in(dev, &usb_ifaces[i].vcp, ep_num);
                break;
            case USB_IFACE_TYPE_WEBUSB:
                usb_webusb_class_data_in(dev, &usb_ifaces[i].webusb, ep_num);
                break;
            default:
                break;
        }
    }
    return USBD_OK;
}

static uint8_t usb_class_data_out(USBD_HandleTypeDef *dev, uint8_t ep_num) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
        switch (usb_ifaces[i].type) {
            case USB_IFACE_TYPE_HID:
                usb_hid_class_data_out(dev, &usb_ifaces[i].hid, ep_num);
                break;
            case USB_IFACE_TYPE_VCP:
                usb_vcp_class_data_out(dev, &usb_ifaces[i].vcp, ep_num);
                break;
            case USB_IFACE_TYPE_WEBUSB:
                usb_webusb_class_data_out(dev, &usb_ifaces[i].webusb, ep_num);
                break;
            default:
                break;
        }
    }
    return USBD_OK;
}

static uint8_t usb_class_sof(USBD_HandleTypeDef *dev) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
        switch (usb_ifaces[i].type) {
            case USB_IFACE_TYPE_VCP:
                usb_vcp_class_sof(dev, &usb_ifaces[i].vcp);
                break;
            default:
                break;
        }
    }
    return USBD_OK;
}

static uint8_t *usb_class_get_cfg_desc(uint16_t *length) {
    *length = usb_config_desc->wTotalLength;
    return usb_config_buf;
}

static uint8_t *usb_class_get_usrstr_desc(USBD_HandleTypeDef *dev, uint8_t index, uint16_t *length) {
    if (sectrue == usb21_enabled && index == USB_WINUSB_EXTRA_STRING_INDEX) {
        static const uint8_t winusb_string_descriptor[] = {
            0x12,                   // bLength
            USB_DESC_TYPE_STRING,   // bDescriptorType
            USB_WINUSB_EXTRA_STRING // wData
        };
        *length = sizeof(winusb_string_descriptor);
        return UNCONST(winusb_string_descriptor);
    } else {
        *length = 0;
        return NULL;
    }
}

static const USBD_ClassTypeDef usb_class = {
    .Init                          = usb_class_init,
    .DeInit                        = usb_class_deinit,
    .Setup                         = usb_class_setup,
    .EP0_TxSent                    = NULL,
    .EP0_RxReady                   = NULL,
    .DataIn                        = usb_class_data_in,
    .DataOut                       = usb_class_data_out,
    .SOF                           = usb_class_sof,
    .IsoINIncomplete               = NULL,
    .IsoOUTIncomplete              = NULL,
    .GetHSConfigDescriptor         = usb_class_get_cfg_desc,
    .GetFSConfigDescriptor         = usb_class_get_cfg_desc,
    .GetOtherSpeedConfigDescriptor = usb_class_get_cfg_desc,
    .GetDeviceQualifierDescriptor  = NULL,
    .GetUsrStrDescriptor           = usb_class_get_usrstr_desc,
};
