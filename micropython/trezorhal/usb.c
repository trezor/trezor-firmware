/*
 * Copyright (c) Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include STM32_HAL_H

#include "usb.h"
#include "usbd_core.h"

#define UNCONST(X) ((uint8_t *)(X))

#define USB_MAX_CONFIG_DESC_SIZE 128
#define USB_MAX_STR_SIZE         62
#define USB_MAX_STR_DESC_SIZE    (USB_MAX_STR_SIZE * 2 + 2)

static usb_device_descriptor_t usb_dev_desc;

// Config descriptor
static uint8_t usb_config_buf[USB_MAX_CONFIG_DESC_SIZE];
static usb_config_descriptor_t *usb_config_desc = (usb_config_descriptor_t *)(usb_config_buf);
static usb_interface_descriptor_t *usb_next_iface_desc;

// String descriptor
static uint8_t usb_str_buf[USB_MAX_STR_DESC_SIZE];
static usb_dev_string_table_t usb_str_table;

static usb_iface_t usb_ifaces[USBD_MAX_NUM_INTERFACES];

static USBD_HandleTypeDef usb_dev_handle;
static const USBD_DescriptorsTypeDef usb_descriptors;
static const USBD_ClassTypeDef usb_class;

static int check_desc_str(const uint8_t *s) {
    if (!s || strlen((const char *)s) > USB_MAX_STR_SIZE) {
        return 1;
    } else {
        return 0;
    }
}

int usb_init(const usb_dev_info_t *dev_info) {

    // Device descriptor
    usb_dev_desc.bLength            = sizeof(usb_device_descriptor_t);
    usb_dev_desc.bDescriptorType    = USB_DESC_TYPE_DEVICE;
    usb_dev_desc.bcdUSB             = 0x0200;
    usb_dev_desc.bDeviceClass       = 0xef;                  // Composite Device Class
    usb_dev_desc.bDeviceSubClass    = 0x02;                  // Common Class
    usb_dev_desc.bDeviceProtocol    = 0x01;                  // Interface Association Descriptor
    usb_dev_desc.bMaxPacketSize0    = USB_MAX_EP0_SIZE;
    usb_dev_desc.idVendor           = dev_info->vendor_id;
    usb_dev_desc.idProduct          = dev_info->product_id;
    usb_dev_desc.bcdDevice          = dev_info->release_num;
    usb_dev_desc.iManufacturer      = USBD_IDX_MFC_STR;      // Index of manufacturer string
    usb_dev_desc.iProduct           = USBD_IDX_PRODUCT_STR;  // Index of product string
    usb_dev_desc.iSerialNumber      = USBD_IDX_SERIAL_STR;   // Index of serial number string
    usb_dev_desc.bNumConfigurations = 1;

    // String table
    if ((0 != check_desc_str(dev_info->manufacturer_str)) ||
        (0 != check_desc_str(dev_info->product_str)) ||
        (0 != check_desc_str(dev_info->serial_number_str)) ||
        (0 != check_desc_str(dev_info->configuration_str)) ||
        (0 != check_desc_str(dev_info->interface_str))) {
        return 1; // Invalid descriptor string
    }
    usb_str_table.manufacturer_str = dev_info->manufacturer_str;
    usb_str_table.product_str      = dev_info->product_str;
    usb_str_table.serial_str       = dev_info->serial_number_str;
    usb_str_table.config_str       = dev_info->configuration_str;
    usb_str_table.interface_str    = dev_info->interface_str;

    // Configuration descriptor
    usb_config_desc->bLength             = sizeof(usb_config_descriptor_t);
    usb_config_desc->bDescriptorType     = USB_DESC_TYPE_CONFIGURATION;
    usb_config_desc->wTotalLength        = sizeof(usb_config_descriptor_t);
    usb_config_desc->bNumInterfaces      = 0;
    usb_config_desc->bConfigurationValue = 0x01;
    usb_config_desc->iConfiguration      = 0;
    usb_config_desc->bmAttributes        = 0x80; // 0x80 = bus powered; 0xc0 = self powered
    usb_config_desc->bMaxPower           = 0xfa; // Maximum Power Consumption in 2mA units

    // Reset pointer to interface descriptor data
    usb_next_iface_desc = (usb_interface_descriptor_t *)(usb_config_buf + usb_config_desc->wTotalLength);

    // Reset the iface state map
    memset(&usb_ifaces, 0, sizeof(usb_ifaces));

    if (0 != USBD_Init(&usb_dev_handle, (USBD_DescriptorsTypeDef*)&usb_descriptors, USB_PHY_FS_ID)) {
        return 1;
    }
    if (0 != USBD_RegisterClass(&usb_dev_handle, (USBD_ClassTypeDef*)&usb_class)) {
        return 1;
    }

    return 0;
}

int usb_deinit(void) {
    return USBD_DeInit(&usb_dev_handle);
}

int usb_start(void) {
    return USBD_Start(&usb_dev_handle);
}

int usb_stop(void) {
    return USBD_Stop(&usb_dev_handle);
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
    return (uint8_t *)(&usb_langid_str_desc);
}

static uint8_t *usb_get_manufacturer_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString(UNCONST(usb_str_table.manufacturer_str), usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_product_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString(UNCONST(usb_str_table.product_str), usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_serial_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString(UNCONST(usb_str_table.serial_str), usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_config_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString(UNCONST(usb_str_table.config_str), usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_interface_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString(UNCONST(usb_str_table.interface_str), usb_str_buf, length);
    return usb_str_buf;
}

static const USBD_DescriptorsTypeDef usb_descriptors = {
    .GetDeviceDescriptor           = usb_get_dev_descriptor,
    .GetLangIDStrDescriptor        = usb_get_langid_str_descriptor,
    .GetManufacturerStrDescriptor  = usb_get_manufacturer_str_descriptor,
    .GetProductStrDescriptor       = usb_get_product_str_descriptor,
    .GetSerialStrDescriptor        = usb_get_serial_str_descriptor,
    .GetConfigurationStrDescriptor = usb_get_config_str_descriptor,
    .GetInterfaceStrDescriptor     = usb_get_interface_str_descriptor,
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
        default:
            break;
        }
    }
    return USBD_OK;
}

static uint8_t usb_class_setup(USBD_HandleTypeDef *dev, USBD_SetupReqTypedef *req) {
    if (((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_CLASS) &&
        ((req->bmRequest & USB_REQ_TYPE_MASK) != USB_REQ_TYPE_STANDARD)) {
        return USBD_OK;
    }
    if (req->wIndex >= USBD_MAX_NUM_INTERFACES) {
        return USBD_FAIL;
    }
    switch (usb_ifaces[req->wIndex].type) {
    case USB_IFACE_TYPE_HID:
        return usb_hid_class_setup(dev, &usb_ifaces[req->wIndex].hid, req);
    case USB_IFACE_TYPE_VCP:
        return usb_vcp_class_setup(dev, &usb_ifaces[req->wIndex].vcp, req);
    default:
        return USBD_FAIL;
    }
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
};
