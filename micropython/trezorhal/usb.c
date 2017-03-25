// TODO: max size of user strings from dev_info

#include STM32_HAL_H

#include "usb.h"
#include "usbd_core.h"

#define USB_MAX_CONFIG_DESC_SIZE     128
#define USB_MAX_STR_DESC_SIZE        256

#define USB_DESC_TYPE_HID            0x21
#define USB_DESC_TYPE_REPORT         0x22

#define HID_REQ_SET_PROTOCOL         0x0b
#define HID_REQ_GET_PROTOCOL         0x03
#define HID_REQ_SET_IDLE             0x0a
#define HID_REQ_GET_IDLE             0x02

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
    USBD_GetString((uint8_t *)usb_str_table.manufacturer_str, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_product_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.product_str, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_serial_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.serial_str, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_config_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.config_str, usb_str_buf, length);
    return usb_str_buf;
}

static uint8_t *usb_get_interface_str_descriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
    USBD_GetString((uint8_t *)usb_str_table.interface_str, usb_str_buf, length);
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

/* usb_hid_add adds and configures new USB HID interface according to
 * configuration options passed in `info`. */
int usb_hid_add(const usb_hid_info_t *info) {
    usb_hid_descriptor_block_t *d = usb_desc_alloc_iface(sizeof(*d));

    if (!d) {
        return 1; // Not enough space in the configuration descriptor
    }

    if ((info->iface_num < usb_config_desc->bNumInterfaces) ||
        (info->iface_num >= USBD_MAX_NUM_INTERFACES) ||
        ((info->ep_in & 0x80) == 0) ||
        ((info->ep_out & 0x80) != 0)) {

        return 1; // Invalid configuration values
    }

    // Interface descriptor
    d->iface.bLength            = USB_LEN_IF_DESC;
    d->iface.bDescriptorType    = USB_DESC_TYPE_INTERFACE;
    d->iface.bInterfaceNumber   = info->iface_num;
    d->iface.bAlternateSetting  = 0x00;
    d->iface.bNumEndpoints      = 0x02;
    d->iface.bInterfaceClass    = 0x03; // HID Class
    d->iface.bInterfaceSubClass = info->subclass;
    d->iface.bInterfaceProtocol = info->protocol;
    d->iface.iInterface         = 0x00; // Index of string descriptor describing the interface

    // HID descriptor
    d->hid.bLength                 = sizeof(usb_hid_descriptor_t);
    d->hid.bDescriptorType         = USB_DESC_TYPE_HID;
    d->hid.bcdHID                  = 0x1101; // HID Class Spec release number
    d->hid.bCountryCode            = 0x00;   // Hardware target country
    d->hid.bNumDescriptors         = 0x01;   // Number of HID class descriptors to follow
    d->hid.bReportDescriptorType   = USB_DESC_TYPE_REPORT;
    d->hid.wReportDescriptorLength = info->report_desc_len;

    // IN endpoint (sending)
    d->ep_in.bLength          = USB_LEN_EP_DESC;
    d->ep_in.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_in.bEndpointAddress = info->ep_in;
    d->ep_in.bmAttributes     = USBD_EP_TYPE_INTR;
    d->ep_in.wMaxPacketSize   = info->max_packet_len;
    d->ep_in.bInterval        = info->polling_interval;

    // OUT endpoint (receiving)
    d->ep_out.bLength          = USB_LEN_EP_DESC;
    d->ep_out.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_out.bEndpointAddress = info->ep_out;
    d->ep_out.bmAttributes     = USBD_EP_TYPE_INTR;
    d->ep_out.wMaxPacketSize   = info->max_packet_len;
    d->ep_out.bInterval        = info->polling_interval;

    // Config descriptor
    usb_desc_add_iface(sizeof(*d));

    // Interface state
    usb_iface_t *i = &usb_ifaces[info->iface_num];
    i->type = USB_IFACE_TYPE_HID;
    i->hid.ep_in = info->ep_in;
    i->hid.ep_out = info->ep_out;
    i->hid.rx_buffer = info->rx_buffer;
    i->hid.max_packet_len = info->max_packet_len;
    i->hid.report_desc_len = info->report_desc_len;
    i->hid.report_desc = info->report_desc;
    i->hid.desc_block = d;

    return 0;
}

int usb_hid_can_read(uint8_t iface_num) {
    return ((iface_num < USBD_MAX_NUM_INTERFACES) &&
            (usb_ifaces[iface_num].type == USB_IFACE_TYPE_HID) &&
            (usb_ifaces[iface_num].hid.rx_buffer_len > 0) &&
            (usb_dev_handle.dev_state == USBD_STATE_CONFIGURED));
}

int usb_hid_can_write(uint8_t iface_num) {
    return ((iface_num < USBD_MAX_NUM_INTERFACES) &&
            (usb_ifaces[iface_num].type == USB_IFACE_TYPE_HID) &&
            (usb_ifaces[iface_num].hid.in_idle) &&
            (usb_dev_handle.dev_state == USBD_STATE_CONFIGURED));
}

int usb_hid_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
    if (iface_num >= USBD_MAX_NUM_INTERFACES) {
        return -1;  // Invalid interface number
    }
    if (usb_ifaces[iface_num].type != USB_IFACE_TYPE_HID) {
        return -2;  // Invalid interface type
    }
    usb_hid_state_t *state = &usb_ifaces[iface_num].hid;
    if (len < state->rx_buffer_len) {
        return 0;  // Not enough data in the read buffer
    }

    memcpy(buf, state->rx_buffer, state->rx_buffer_len);

    // Clear NAK to indicate we are ready to read more data
    usb_ep_clear_nak(&usb_dev_handle, state->ep_out);

    return state->rx_buffer_len;
}

int usb_hid_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
    if (iface_num >= USBD_MAX_NUM_INTERFACES) {
        return -1;  // Invalid interface number
    }
    if (usb_ifaces[iface_num].type != USB_IFACE_TYPE_HID) {
        return -2;  // Invalid interface type
    }
    usb_hid_state_t *state = &usb_ifaces[iface_num].hid;

    state->in_idle = 0;
    USBD_LL_Transmit(&usb_dev_handle, state->ep_in, (uint8_t *)buf, (uint16_t)len);

    return len;
}

int usb_hid_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len, uint32_t timeout) {
    uint32_t start = HAL_GetTick();
    while (!usb_hid_can_read(iface_num)) {
        if (HAL_GetTick() - start >= timeout) {
            return 0;  // Timeout
        }
        __WFI();  // Enter sleep mode, waiting for interrupt
    }
    return usb_hid_read(iface_num, buf, len);
}

int usb_hid_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len, uint32_t timeout) {
    uint32_t start = HAL_GetTick();
    while (!usb_hid_can_write(iface_num)) {
        if (HAL_GetTick() - start >= timeout) {
            return 0;  // Timeout
        }
        __WFI();  // Enter sleep mode, waiting for interrupt
    }
    return usb_hid_write(iface_num, buf, len);
}

static int usb_hid_class_init(USBD_HandleTypeDef *dev, usb_hid_state_t *state, uint8_t cfg_idx) {
    // Open endpoints
    USBD_LL_OpenEP(dev, state->ep_in, USBD_EP_TYPE_INTR, state->max_packet_len);
    USBD_LL_OpenEP(dev, state->ep_out, USBD_EP_TYPE_INTR, state->max_packet_len);

    // Reset the state
    state->in_idle = 1;
    state->protocol = 0;
    state->idle_rate = 0;
    state->alt_setting = 0;

    // Prepare Out endpoint to receive next packet
    USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_buffer, state->max_packet_len);

    return USBD_OK;
}

static int usb_hid_class_deinit(USBD_HandleTypeDef *dev, usb_hid_state_t *state, uint8_t cfg_idx) {
    // Close endpoints
    USBD_LL_CloseEP(dev, state->ep_in);
    USBD_LL_CloseEP(dev, state->ep_out);

    return USBD_OK;
}

static int usb_hid_class_setup(USBD_HandleTypeDef *dev, usb_hid_state_t *state, USBD_SetupReqTypedef *req) {
    switch (req->bmRequest & USB_REQ_TYPE_MASK) {

    // Class request
    case USB_REQ_TYPE_CLASS:
        switch (req->bRequest) {

        case HID_REQ_SET_PROTOCOL:
            state->protocol = req->wValue;
            break;

        case HID_REQ_GET_PROTOCOL:
            USBD_CtlSendData(dev, &state->protocol, sizeof(state->protocol));
            break;

        case HID_REQ_SET_IDLE:
            state->idle_rate = req->wValue >> 8;
            break;

        case HID_REQ_GET_IDLE:
            USBD_CtlSendData(dev, &state->idle_rate, sizeof(state->idle_rate));
            break;

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
            break;

        case USB_REQ_GET_INTERFACE:
            USBD_CtlSendData(dev, &state->alt_setting, sizeof(state->alt_setting));
            break;

        case USB_REQ_GET_DESCRIPTOR:
            switch (req->wValue >> 8) {

            case USB_DESC_TYPE_HID:
                USBD_CtlSendData(dev, (uint8_t*)&state->desc_block->hid, MIN(req->wLength, sizeof(state->desc_block->hid)));
                break;

            case USB_DESC_TYPE_REPORT:
                USBD_CtlSendData(dev, (uint8_t*)state->report_desc, MIN(req->wLength, state->report_desc_len));
                break;
            }
            break;
        }
        break;
    }
    return USBD_OK;
}

static uint8_t usb_hid_class_data_in(USBD_HandleTypeDef *dev, usb_hid_state_t *state, uint8_t ep_num) {
    if (ep_num == state->ep_in) {
        // Ensure that the FIFO is empty before a new transfer,
        // this condition could be caused by a new transfer
        // before the end of the previous transfer.
        state->in_idle = 1;
    }
    return USBD_OK;
}

static uint8_t usb_hid_class_data_out(USBD_HandleTypeDef *dev, usb_hid_state_t *state, uint8_t ep_num) {
    if (ep_num == state->ep_out) {
        // User should provide state->rx_buffer_len that is big
        // enough for state->max_packet_len bytes.
        state->rx_buffer_len = USBD_LL_GetRxDataSize(dev, ep_num);

        if (state->rx_buffer_len > 0) {
            // Block the OUT EP until we process received data
            usb_ep_set_nak(dev, ep_num);
        }
    }
    return USBD_OK;
}

static uint8_t usb_class_init(USBD_HandleTypeDef *dev, uint8_t cfg_idx) {
    for (int i = 0; i < USBD_MAX_NUM_INTERFACES; i++) {
        switch (usb_ifaces[i].type) {
        case USB_IFACE_TYPE_HID:
            usb_hid_class_init(dev, &usb_ifaces[i].hid, cfg_idx);
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
