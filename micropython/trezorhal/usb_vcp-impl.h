#define USB_LEN_ASSOC_DESC            0x08

#define USB_DESC_TYPE_ASSOCIATION     0x0b
#define USB_DESC_TYPE_HEADER          0x00
#define USB_DESC_TYPE_CALL_MANAGEMENT 0x01
#define USB_DESC_TYPE_ACM             0x02
#define USB_DESC_TYPE_UNION           0x06

#define CDC_GET_LINE_CODING           0x21
#define CDC_SET_CONTROL_LINE_STATE    0x22

// static int ring_init(ring_buffer_t *b, uint8_t *buf, size_t cap) {
//     if (cap == 0 || (cap & (cap - 1)) != 0) {
//         return 1; // Capacity needs to be a power of 2
//     }
//     b->buf = buf;
//     b->cap = cap;
//     b->read = 0;
//     b->write = 0;
//     return 0;
// }

// static inline size_t ring_length(ring_buffer_t *b) {
//     return (b->write - b->read);
// }

// static inline int ring_empty(ring_buffer_t *b) {
//     return ring_length(b) == 0;
// }

// static inline int ring_full(ring_buffer_t *b) {
//     return ring_length(b) == b->cap;
// }

// uint32_t ring_read(ring_buffer_t *b, uint8_t *buf, uint32_t len) {
//     const uint32_t mask = b->cap - 1;
//     uint32_t i;
//     for (i = 0; (i < len) && !ring_empty(b); i++) {
//         buf[i] = b->buf[b->read & mask];
//         b->read++;
//     }
//     return i;
// }

// uint32_t ring_write(ring_buffer_t *b, const uint8_t *buf, uint32_t len) {
//     const uint32_t mask = b->cap - 1;
//     uint32_t i;
//     for (i = 0; (i < len) && !ring_full(b); i++) {
//         b->buf[b->write & mask] = buf[i];
//         b->write++;
//     }
//     return i;
// }

/* usb_vcp_add adds and configures new USB VCP interface according to
 * configuration options passed in `info`. */
int usb_vcp_add(const usb_vcp_info_t *info) {

    usb_iface_t *iface = usb_get_iface(info->iface_num);

    if (iface == NULL) {
        return 1; // Invalid interface number
    }
    if (iface->type != USB_IFACE_TYPE_DISABLED) {
        return 1; // Interface is already enabled
    }

    usb_vcp_descriptor_block_t *d = usb_desc_alloc_iface(sizeof(usb_vcp_descriptor_block_t));

    if (d == NULL) {
        return 1; // Not enough space in the configuration descriptor
    }

    if ((info->ep_cmd & USB_EP_DIR_MSK) != USB_EP_DIR_IN) {
        return 1; // CMD EP is invalid
    }
    if ((info->ep_in & USB_EP_DIR_MSK) != USB_EP_DIR_IN) {
        return 1; // IN EP is invalid
    }
    if ((info->ep_out & USB_EP_DIR_MSK) != USB_EP_DIR_OUT) {
        return 1; // OUT EP is invalid
    }

    // Interface association descriptor
    d->assoc.bLength           = USB_LEN_ASSOC_DESC;
    d->assoc.bDescriptorType   = USB_DESC_TYPE_ASSOCIATION;
    d->assoc.bFirstInterface   = info->iface_num;
    d->assoc.bInterfaceCount   = 2;
    d->assoc.bFunctionClass    = 0x02; // Communication Interface Class
    d->assoc.bFunctionSubClass = 0x02; // Abstract Control Model
    d->assoc.bFunctionProtocol = 0x01; // Common AT commands
    d->assoc.iFunction         = 0x00; // Index of string descriptor describing the function

    // Interface descriptor
    d->iface_cdc.bLength            = USB_LEN_IF_DESC;
    d->iface_cdc.bDescriptorType    = USB_DESC_TYPE_INTERFACE;
    d->iface_cdc.bInterfaceNumber   = info->iface_num;
    d->iface_cdc.bAlternateSetting  = 0x00;
    d->iface_cdc.bNumEndpoints      = 1;
    d->iface_cdc.bInterfaceClass    = 0x02; // Communication Interface Class
    d->iface_cdc.bInterfaceSubClass = 0x02; // Abstract Control Model
    d->iface_cdc.bInterfaceProtocol = 0x01; // Common AT commands
    d->iface_cdc.iInterface         = 0x00; // Index of string descriptor describing the interface

    // Header Functional Descriptor
    d->fheader.bFunctionLength    = sizeof(usb_vcp_header_descriptor_t);
    d->fheader.bDescriptorType    = 0x24;   // CS_INTERFACE
    d->fheader.bDescriptorSubtype = 0x00;   // Header Func desc
    d->fheader.bcdCDC             = 0x1001; // Spec release number

    // Call Management Functional Descriptor
    d->fcm.bFunctionLength    = sizeof(usb_vcp_cm_descriptor_t);
    d->fcm.bDescriptorType    = 0x24; // CS_INTERFACE
    d->fcm.bDescriptorSubtype = 0x01; // Call Management Func desc
    d->fcm.bmCapabilities     = 0x00; // D0+D1
    d->fcm.bDataInterface     = info->data_iface_num;

    // ACM Functional Descriptor
    d->facm.bFunctionLength    = sizeof(usb_vcp_acm_descriptor_t);
    d->facm.bDescriptorType    = 0x24; // CS_INTERFACE
    d->facm.bDescriptorSubtype = 0x02; // Abstract Control Management desc
    d->facm.bmCapabilities     = 0x02;

    // Union Functional Descriptor
    d->funion.bFunctionLength        = sizeof(usb_vcp_union_descriptor_t);
    d->funion.bDescriptorType        = 0x24; // CS_INTERFACE
    d->funion.bDescriptorSubtype     = 0x06; // Union Func desc
    d->funion.bControlInterface      = info->iface_num;
    d->funion.bSubordinateInterface0 = info->data_iface_num;

    // IN CMD endpoint (control)
    d->ep_cmd.bLength          = USB_LEN_EP_DESC;
    d->ep_cmd.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_cmd.bEndpointAddress = info->ep_cmd;
    d->ep_cmd.bmAttributes     = USBD_EP_TYPE_INTR;
    d->ep_cmd.wMaxPacketSize   = info->max_cmd_packet_len;
    d->ep_cmd.bInterval        = info->polling_interval;

    // Interface descriptor
    d->iface_data.bLength            = USB_LEN_IF_DESC;
    d->iface_data.bDescriptorType    = USB_DESC_TYPE_INTERFACE;
    d->iface_data.bInterfaceNumber   = info->data_iface_num;
    d->iface_data.bAlternateSetting  = 0x00;
    d->iface_data.bNumEndpoints      = 2;
    d->iface_data.bInterfaceClass    = 0x0A; // CDC
    d->iface_data.bInterfaceSubClass = 0x00;
    d->iface_data.bInterfaceProtocol = 0x00;
    d->iface_data.iInterface         = 0x00; // Index of string descriptor describing the interface

    // OUT endpoint (receiving)
    d->ep_out.bLength          = USB_LEN_EP_DESC;
    d->ep_out.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_out.bEndpointAddress = info->ep_out;
    d->ep_out.bmAttributes     = USBD_EP_TYPE_BULK;
    d->ep_out.wMaxPacketSize   = info->max_data_packet_len;
    d->ep_out.bInterval        = 0x00; // Ignored for bulk endpoints

    // IN endpoint (sending)
    d->ep_in.bLength          = USB_LEN_EP_DESC;
    d->ep_in.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_in.bEndpointAddress = info->ep_in;
    d->ep_in.bmAttributes     = USBD_EP_TYPE_BULK;
    d->ep_in.wMaxPacketSize   = info->max_data_packet_len;
    d->ep_in.bInterval        = 0x00; // Ignored for bulk endpoints

    // Config descriptor
    // TODO: do this in a clean way
    usb_desc_add_iface(sizeof(usb_vcp_descriptor_block_t));
    usb_config_desc->bNumInterfaces++;

    // Interface state
    iface->type = USB_IFACE_TYPE_VCP;
    iface->vcp.data_iface_num = info->data_iface_num;
    iface->vcp.ep_cmd = info->ep_cmd;
    iface->vcp.ep_in = info->ep_in;
    iface->vcp.ep_out = info->ep_out;
    iface->vcp.max_cmd_packet_len = info->max_cmd_packet_len;
    iface->vcp.max_data_packet_len = info->max_data_packet_len;
    iface->vcp.desc_block = d;

    return 0;
}

int usb_vcp_can_read(uint8_t iface_num) {
    return 0;
}

int usb_vcp_can_write(uint8_t iface_num) {
    usb_iface_t *iface = usb_get_iface(iface_num);
    if (iface == NULL) {
        return 0; // Invalid interface number
    }
    if (iface->type != USB_IFACE_TYPE_VCP) {
        return 0; // Invalid interface type
    }
    if (iface->vcp.in_idle == 0) {
        return 0; // Last transmission is not over yet
    }
    if (usb_dev_handle.dev_state != USBD_STATE_CONFIGURED) {
        return 0; // Device is not configured
    }
    return 1;
}

int usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
    usb_iface_t *iface = usb_get_iface(iface_num);
    if (iface == NULL) {
        return -1; // Invalid interface number
    }
    if (iface->type != USB_IFACE_TYPE_VCP) {
        return -2; // Interface interface type
    }
    // usb_vcp_state_t *state = &iface->vcp;
    // TODO

    return 0;
}

int usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
    usb_iface_t *iface = usb_get_iface(iface_num);
    if (iface == NULL) {
        return -1; // Invalid interface number
    }
    if (iface->type != USB_IFACE_TYPE_VCP) {
        return -2; // Interface interface type
    }
    usb_vcp_state_t *state = &iface->vcp;

    if (!state->is_connected) {
        return 0;
    }

    state->in_idle = 0;
    USBD_LL_Transmit(&usb_dev_handle, state->ep_in, UNCONST(buf), (uint16_t)len);

    return len;
}

int usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len, uint32_t timeout) {
    uint32_t start = HAL_GetTick();
    while (!usb_vcp_can_read(iface_num)) {
        if (HAL_GetTick() - start >= timeout) {
            return 0;  // Timeout
        }
        __WFI();  // Enter sleep mode, waiting for interrupt
    }
    return usb_vcp_read(iface_num, buf, len);
}

int usb_vcp_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len, uint32_t timeout) {
    uint32_t start = HAL_GetTick();
    while (!usb_vcp_can_write(iface_num)) {
        if (HAL_GetTick() - start >= timeout) {
            return 0; // Timeout
        }
        __WFI(); // Enter sleep mode, waiting for interrupt
    }
    return usb_vcp_write(iface_num, buf, len);
}

static int usb_vcp_class_init(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t cfg_idx) {
    // Open endpoints
    USBD_LL_OpenEP(dev, state->ep_in, USBD_EP_TYPE_BULK, state->max_data_packet_len);
    USBD_LL_OpenEP(dev, state->ep_out, USBD_EP_TYPE_BULK, state->max_data_packet_len);
    USBD_LL_OpenEP(dev, state->ep_cmd, USBD_EP_TYPE_INTR, state->max_cmd_packet_len);

    // Reset the state
    state->in_idle = 1;

    // TODO
    // Prepare the OUT EP to receive next packet
    // USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_buffer, state->max_data_packet_len);

    return USBD_OK;
}

static int usb_vcp_class_deinit(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t cfg_idx) {
    // Close endpoints
    USBD_LL_CloseEP(dev, state->ep_in);
    USBD_LL_CloseEP(dev, state->ep_out);
    USBD_LL_CloseEP(dev, state->ep_cmd);

    return USBD_OK;
}

static int usb_vcp_class_setup(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, USBD_SetupReqTypedef *req) {
    static const uint8_t line_coding[] = {
        (uint8_t)(115200 >> 0),
        (uint8_t)(115200 >> 8),
        (uint8_t)(115200 >> 16),
        (uint8_t)(115200 >> 24),
        0, // Stop bits
        0, // Parity
        8, // Number of bits
    };

    switch (req->bmRequest & USB_REQ_TYPE_MASK) {

    // Class request
    case USB_REQ_TYPE_CLASS :
        switch (req->bRequest) {

        case USB_CDC_GET_LINE_CODING:
            USBD_CtlSendData(dev, UNCONST(line_coding), sizeof(line_coding));
            break;

        case USB_CDC_SET_CONTROL_LINE_STATE:
            state->is_connected = req->wLength & 1;
            break;
        }
        break;
    }

    return USBD_OK;
}

static uint8_t usb_vcp_class_data_in(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t ep_num) {
    if ((ep_num | USB_EP_DIR_IN) == state->ep_in) {
        state->in_idle = 1;
    }
    return USBD_OK;
}

static uint8_t usb_vcp_class_data_out(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t ep_num) {
    // TODO: process received data
    return USBD_OK;
}
