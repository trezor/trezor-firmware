// TODO: max size of user strings from dev_info

#include STM32_HAL_H

#include "usb.h"
#include "usbd_core.h"

#define UNCONST(X) ((uint8_t *)(X))

#define USB_MAX_CONFIG_DESC_SIZE     128
#define USB_MAX_STR_DESC_SIZE        256

extern PCD_HandleTypeDef pcd_fs_handle;

static USBD_HandleTypeDef usb_dev_handle;

static usb_device_descriptor_t usb_dev_desc;
static uint8_t usb_config_buf[USB_MAX_CONFIG_DESC_SIZE];
static uint8_t usb_str_buf[USB_MAX_STR_DESC_SIZE];
static const usb_string_descriptor_t usb_langid_str_desc = {
    .bLength         = USB_LEN_LANGID_STR_DESC,
    .bDescriptorType = USB_DESC_TYPE_STRING,
    .wData           = USB_LANGID_ENGLISH_US,
};
static usb_config_descriptor_t *usb_config_desc = (usb_config_descriptor_t *)(usb_config_buf);
static usb_interface_descriptor_t *usb_next_iface_desc;
static usb_string_table_t usb_str_table;
static usb_iface_t usb_ifaces[USBD_MAX_NUM_INTERFACES];

static const USBD_DescriptorsTypeDef usb_descriptors;
static const USBD_ClassTypeDef usb_class;

int usb_init(const usb_dev_info_t *dev_info) {

    // Device descriptor
    usb_dev_desc.bLength            = USB_LEN_DEV_DESC;
    usb_dev_desc.bDescriptorType    = USB_DESC_TYPE_DEVICE;
    usb_dev_desc.bcdUSB             = 0x00ef;
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
    usb_dev_desc.bNumConfigurations = 0x01;

    // String table
    usb_str_table.manufacturer_str = dev_info->manufacturer_str;
    usb_str_table.product_str      = dev_info->product_str;
    usb_str_table.serial_str       = dev_info->serial_number_str;
    usb_str_table.config_str       = dev_info->configuration_str;
    usb_str_table.interface_str    = dev_info->interface_str;

    // Configuration descriptor
    usb_config_desc->bLength             = USB_LEN_CFG_DESC;
    usb_config_desc->bDescriptorType     = USB_DESC_TYPE_CONFIGURATION;
    usb_config_desc->wTotalLength        = USB_LEN_CFG_DESC;
    usb_config_desc->bNumInterfaces      = 0x00;
    usb_config_desc->bConfigurationValue = 0x01; // Configuration value
    usb_config_desc->iConfiguration      = 0x00; // Index of string descriptor describing the configuration
    usb_config_desc->bmAttributes        = 0x80; // 0x80 = bus powered; 0xc0 = self powered
    usb_config_desc->bMaxPower           = 0xfa; // In units of 2mA

    // Pointer to interface descriptor data, see: usb_desc_alloc_iface, usb_desc_add_iface
    usb_next_iface_desc = (usb_interface_descriptor_t *)(usb_config_buf + usb_config_desc->wTotalLength);

    // Reset the iface state map
    memset(&usb_ifaces, 0, sizeof(usb_ifaces));

    USBD_Init(&usb_dev_handle, (USBD_DescriptorsTypeDef*)&usb_descriptors, USB_PHY_FS_ID);
    USBD_RegisterClass(&usb_dev_handle, (USBD_ClassTypeDef*)&usb_class);

    return 0;
}

int usb_start(void) {
    return USBD_Start(&usb_dev_handle);
}

int usb_stop(void) {
    return USBD_Stop(&usb_dev_handle);
}

static uint8_t *usb_get_dev_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    *length = sizeof(usb_dev_desc);
    return (uint8_t *)&usb_dev_desc;
}

static uint8_t *usb_get_langid_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    *length = sizeof(usb_langid_str_desc);
    return (uint8_t *)&usb_langid_str_desc;
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

static void *usb_desc_alloc_iface(size_t desc_len) {
    if (usb_config_desc->wTotalLength + desc_len > USB_MAX_CONFIG_DESC_SIZE) {
        return NULL;  // Not enough space in the descriptor
    }
    if (usb_config_desc->bNumInterfaces + 1 >= USBD_MAX_NUM_INTERFACES) {
        return NULL;  // Already using all the interfaces
    }
    return usb_next_iface_desc;
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

#include "usb_hid-impl.h"
#include "usb_vcp-impl.h"

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

static uint8_t usb_class_ep0_rx_ready(USBD_HandleTypeDef *dev) {
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

static uint8_t *usb_class_get_cfg_desc(uint16_t *length) {
    *length = usb_config_desc->wTotalLength;
    return usb_config_buf;
}

static const USBD_ClassTypeDef usb_class = {
    .Init                          = usb_class_init,
    .DeInit                        = usb_class_deinit,
    .Setup                         = usb_class_setup,
    .EP0_TxSent                    = NULL,
    .EP0_RxReady                   = usb_class_ep0_rx_ready,
    .DataIn                        = usb_class_data_in,
    .DataOut                       = usb_class_data_out,
    .SOF                           = NULL,
    .IsoINIncomplete               = NULL,
    .IsoOUTIncomplete              = NULL,
    .GetHSConfigDescriptor         = usb_class_get_cfg_desc,
    .GetFSConfigDescriptor         = usb_class_get_cfg_desc,
    .GetOtherSpeedConfigDescriptor = usb_class_get_cfg_desc,
    .GetDeviceQualifierDescriptor  = NULL,
};

/**
  * @brief  This function handles USB-On-The-Go FS global interrupt request.
  * @param  None
  * @retval None
  */
void OTG_FS_IRQHandler(void) {
    HAL_PCD_IRQHandler(&pcd_fs_handle);
}

/**
  * @brief  This function handles USB OTG Common FS/HS Wakeup functions.
  * @param  *pcd_handle for FS or HS
  * @retval None
  */
static void OTG_CMD_WKUP_Handler(PCD_HandleTypeDef *pcd_handle) {
    if (!(pcd_handle->Init.low_power_enable)) {
        return;
    }

    /* Reset SLEEPDEEP bit of Cortex System Control Register */
    SCB->SCR &= (uint32_t) ~((uint32_t)(SCB_SCR_SLEEPDEEP_Msk | SCB_SCR_SLEEPONEXIT_Msk));

    /* Configures system clock after wake-up from STOP: enable HSE, PLL and select
    PLL as system clock source (HSE and PLL are disabled in STOP mode) */

    __HAL_RCC_HSE_CONFIG(RCC_HSE_ON);

    /* Wait till HSE is ready */
    while (__HAL_RCC_GET_FLAG(RCC_FLAG_HSERDY) == RESET) {}

    /* Enable the main PLL. */
    __HAL_RCC_PLL_ENABLE();

    /* Wait till PLL is ready */
    while (__HAL_RCC_GET_FLAG(RCC_FLAG_PLLRDY) == RESET) {}

    /* Select PLL as SYSCLK */
    MODIFY_REG(RCC->CFGR, RCC_CFGR_SW, RCC_SYSCLKSOURCE_PLLCLK);

    while (__HAL_RCC_GET_SYSCLK_SOURCE() != RCC_CFGR_SWS_PLL) {}

    /* ungate PHY clock */
    __HAL_PCD_UNGATE_PHYCLOCK(pcd_handle);
}

/**
  * @brief  This function handles USB OTG FS Wakeup IRQ Handler.
  * @param  None
  * @retval None
  */
void OTG_FS_WKUP_IRQHandler(void) {
    OTG_CMD_WKUP_Handler(&pcd_fs_handle);

    /* Clear EXTI pending Bit*/
    __HAL_USB_FS_EXTI_CLEAR_FLAG();
}
