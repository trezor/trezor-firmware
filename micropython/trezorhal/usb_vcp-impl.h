/*
 * Copyright (c) Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

// Communications Device Class Code (bFunctionClass, bInterfaceClass)
#define USB_CLASS_CDC 0x02

// Data Interface Class Code (bInterfaceClass)
#define USB_CLASS_DATA 0x0A

// Class Subclass Code (bFunctionSubClass, bInterfaceSubClass)
#define USB_CDC_SUBCLASS_ACM 0x02

// Communications Interface Class Control Protocol Codes (bFunctionProtocol, bInterfaceProtocol)
#define USB_CDC_PROTOCOL_AT 0x01

// Descriptor Types (bDescriptorType)
#define USB_DESC_TYPE_ASSOCIATION 0x0b
#define USB_DESC_TYPE_CS_INTERACE 0x24

// Descriptor SubTypes (bDescriptorSubtype)
#define USB_DESC_TYPE_HEADER 0x00
#define USB_DESC_TYPE_CM     0x01
#define USB_DESC_TYPE_ACM    0x02
#define USB_DESC_TYPE_UNION  0x06

// Data Phase Transfer Direction (bmRequest)
#define USB_REQ_DIR_MASK     0x80
#define USB_H2D              0x00
#define USB_D2H              0x80

// Class-Specific Request Codes for PSTN subclasses
#define USB_CDC_GET_LINE_CODING        0x21

// Maximal length of packets on IN CMD EP
#define USB_CDC_MAX_CMD_PACKET_LEN 0x08

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
        return 1; // IN CMD EP is invalid
    }
    if ((info->ep_in & USB_EP_DIR_MSK) != USB_EP_DIR_IN) {
        return 1; // IN EP is invalid
    }
    if ((info->ep_out & USB_EP_DIR_MSK) != USB_EP_DIR_OUT) {
        return 1; // OUT EP is invalid
    }
    if ((info->rx_buffer_len == 0) || (info->rx_buffer_len & (info->rx_buffer_len - 1)) != 0) {
        return 1; // Capacity needs to be a power of 2
    }
    if ((info->tx_buffer_len == 0) || (info->tx_buffer_len & (info->tx_buffer_len - 1)) != 0) {
        return 1; // Capacity needs to be a power of 2
    }
    if (info->rx_buffer == NULL) {
        return 1;
    }
    if (info->rx_packet == NULL) {
        return 1;
    }
    if (info->tx_buffer == NULL) {
        return 1;
    }
    if (info->tx_packet == NULL) {
        return 1;
    }

    // Interface association descriptor
    d->assoc.bLength           = sizeof(usb_interface_assoc_descriptor_t);
    d->assoc.bDescriptorType   = USB_DESC_TYPE_ASSOCIATION;
    d->assoc.bFirstInterface   = info->iface_num;
    d->assoc.bInterfaceCount   = 2;
    d->assoc.bFunctionClass    = USB_CLASS_CDC;
    d->assoc.bFunctionSubClass = USB_CDC_SUBCLASS_ACM;
    d->assoc.bFunctionProtocol = USB_CDC_PROTOCOL_AT;
    d->assoc.iFunction         = 0;

    // Interface descriptor
    d->iface_cdc.bLength            = sizeof(usb_interface_descriptor_t);
    d->iface_cdc.bDescriptorType    = USB_DESC_TYPE_INTERFACE;
    d->iface_cdc.bInterfaceNumber   = info->iface_num;
    d->iface_cdc.bAlternateSetting  = 0;
    d->iface_cdc.bNumEndpoints      = 1;
    d->iface_cdc.bInterfaceClass    = USB_CLASS_CDC;
    d->iface_cdc.bInterfaceSubClass = USB_CDC_SUBCLASS_ACM;
    d->iface_cdc.bInterfaceProtocol = USB_CDC_PROTOCOL_AT;
    d->iface_cdc.iInterface         = 0;

    // Header Functional Descriptor
    d->fheader.bFunctionLength    = sizeof(usb_vcp_header_descriptor_t);
    d->fheader.bDescriptorType    = USB_DESC_TYPE_CS_INTERACE;
    d->fheader.bDescriptorSubtype = USB_DESC_TYPE_HEADER;
    d->fheader.bcdCDC             = 0x1001; // USB Class Definitions for Communication Devices Specification release number.

    // Call Management Functional Descriptor
    d->fcm.bFunctionLength    = sizeof(usb_vcp_cm_descriptor_t);
    d->fcm.bDescriptorType    = USB_DESC_TYPE_CS_INTERACE;
    d->fcm.bDescriptorSubtype = USB_DESC_TYPE_CM;
    // Device sends/receives call management information only over the Communication Class interface.
    // Device does not handle call management itself.
    d->fcm.bmCapabilities     = 0x00;
    d->fcm.bDataInterface     = info->data_iface_num;

    // ACM Functional Descriptor
    d->facm.bFunctionLength    = sizeof(usb_vcp_acm_descriptor_t);
    d->facm.bDescriptorType    = USB_DESC_TYPE_CS_INTERACE;
    d->facm.bDescriptorSubtype = USB_DESC_TYPE_ACM;
    // Device supports the request combination of Set_Line_Coding, Set_Control_Line_State,
    // Get_Line_Coding, and the notification Serial_State.
    d->facm.bmCapabilities     = 0x02;

    // Union Functional Descriptor
    d->funion.bFunctionLength        = sizeof(usb_vcp_union_descriptor_t);
    d->funion.bDescriptorType        = USB_DESC_TYPE_CS_INTERACE;
    d->funion.bDescriptorSubtype     = USB_DESC_TYPE_UNION;
    d->funion.bControlInterface      = info->iface_num;
    d->funion.bSubordinateInterface0 = info->data_iface_num;

    // IN CMD endpoint (control)
    d->ep_cmd.bLength          = sizeof(usb_endpoint_descriptor_t);
    d->ep_cmd.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_cmd.bEndpointAddress = info->ep_cmd;
    d->ep_cmd.bmAttributes     = USBD_EP_TYPE_INTR;
    d->ep_cmd.wMaxPacketSize   = USB_CDC_MAX_CMD_PACKET_LEN;
    d->ep_cmd.bInterval        = info->polling_interval;

    // Interface descriptor
    d->iface_data.bLength            = sizeof(usb_interface_descriptor_t);
    d->iface_data.bDescriptorType    = USB_DESC_TYPE_INTERFACE;
    d->iface_data.bInterfaceNumber   = info->data_iface_num;
    d->iface_data.bAlternateSetting  = 0;
    d->iface_data.bNumEndpoints      = 2;
    d->iface_data.bInterfaceClass    = USB_CLASS_DATA;
    d->iface_data.bInterfaceSubClass = 0;
    d->iface_data.bInterfaceProtocol = 0;
    d->iface_data.iInterface         = 0;

    // OUT endpoint (receiving)
    d->ep_out.bLength          = sizeof(usb_endpoint_descriptor_t);
    d->ep_out.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_out.bEndpointAddress = info->ep_out;
    d->ep_out.bmAttributes     = USBD_EP_TYPE_BULK;
    d->ep_out.wMaxPacketSize   = info->max_packet_len;
    d->ep_out.bInterval        = 0;

    // IN endpoint (sending)
    d->ep_in.bLength          = sizeof(usb_endpoint_descriptor_t);
    d->ep_in.bDescriptorType  = USB_DESC_TYPE_ENDPOINT;
    d->ep_in.bEndpointAddress = info->ep_in;
    d->ep_in.bmAttributes     = USBD_EP_TYPE_BULK;
    d->ep_in.wMaxPacketSize   = info->max_packet_len;
    d->ep_in.bInterval        = 0;

    // Config descriptor
    usb_desc_add_iface(sizeof(usb_vcp_descriptor_block_t));
    usb_config_desc->bNumInterfaces++; // usb_vcp_descriptor_block_t contains 2 interfaces

    // Interface state

    iface->type = USB_IFACE_TYPE_VCP;
    iface->vcp.desc_block = d;

    iface->vcp.rx_ring.buf   = info->rx_buffer;
    iface->vcp.rx_ring.cap   = info->rx_buffer_len;
    iface->vcp.rx_ring.read  = 0;
    iface->vcp.rx_ring.write = 0;

    iface->vcp.tx_ring.buf   = info->tx_buffer;
    iface->vcp.tx_ring.cap   = info->tx_buffer_len;
    iface->vcp.tx_ring.read  = 0;
    iface->vcp.tx_ring.write = 0;

    iface->vcp.rx_packet = info->rx_packet;
    iface->vcp.tx_packet = info->tx_packet;

    iface->vcp.rx_intr_fn   = info->rx_intr_fn;
    iface->vcp.rx_intr_byte = info->rx_intr_byte;

    iface->vcp.ep_cmd         = info->ep_cmd;
    iface->vcp.ep_in          = info->ep_in;
    iface->vcp.ep_out         = info->ep_out;
    iface->vcp.max_packet_len = info->max_packet_len;

    iface->vcp.ep_in_is_idle = 1;

    return 0;
}

static inline size_t ring_length(usb_rbuf_t *b) {
    return (b->write - b->read);
}

static inline int ring_empty(usb_rbuf_t *b) {
    return ring_length(b) == 0;
}

static inline int ring_full(usb_rbuf_t *b) {
    return ring_length(b) == b->cap;
}

int usb_vcp_can_read(uint8_t iface_num) {
    usb_iface_t *iface = usb_get_iface(iface_num);
    if (iface == NULL) {
        return 0; // Invalid interface number
    }
    if (iface->type != USB_IFACE_TYPE_VCP) {
        return 0; // Invalid interface type
    }
    if (ring_empty(&iface->vcp.rx_ring)) {
        return 0; // Nothing in the rx buffer
    }
    return 1;
}

int usb_vcp_can_write(uint8_t iface_num) {
    usb_iface_t *iface = usb_get_iface(iface_num);
    if (iface == NULL) {
        return 0; // Invalid interface number
    }
    if (iface->type != USB_IFACE_TYPE_VCP) {
        return 0; // Invalid interface type
    }
    if (ring_full(&iface->vcp.tx_ring)) {
        return 0; // Tx ring buffer is full
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
    usb_vcp_state_t *state = &iface->vcp;

    // Read from the rx ring buffer
    usb_rbuf_t *b = &state->rx_ring;
    size_t mask = b->cap - 1;
    size_t i;
    for (i = 0; (i < len) && !ring_empty(b); i++) {
        buf[i] = b->buf[b->read & mask];
        b->read++;
    }
    return i;
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

    // Write into the tx ring buffer
    usb_rbuf_t *b = &state->tx_ring;
    size_t mask = b->cap - 1;
    size_t i;
    for (i = 0; (i < len) && !ring_full(b); i++) {
        b->buf[b->write & mask] = buf[i];
        b->write++;
    }

    return len;
}

int usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len, uint32_t timeout) {
    uint32_t start = HAL_GetTick();
    while (!usb_vcp_can_read(iface_num)) {
        if (HAL_GetTick() - start >= timeout) {
            return 0; // Timeout
        }
        __WFI(); // Enter sleep mode, waiting for interrupt
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
    USBD_LL_OpenEP(dev, state->ep_in, USBD_EP_TYPE_BULK,  state->max_packet_len);
    USBD_LL_OpenEP(dev, state->ep_out, USBD_EP_TYPE_BULK, state->max_packet_len);
    USBD_LL_OpenEP(dev, state->ep_cmd, USBD_EP_TYPE_INTR, USB_CDC_MAX_CMD_PACKET_LEN);

    // Reset the state
    state->rx_ring.read = 0;
    state->rx_ring.write = 0;
    state->tx_ring.read = 0;
    state->tx_ring.write = 0;
    state->ep_in_is_idle = 1;

    // Prepare the OUT EP to receive next packet
    USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_packet, state->max_packet_len);

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
    static const usb_cdc_line_coding_t line_coding = {
        .dwDTERate   = 115200,
        .bCharFormat = USB_CDC_1_STOP_BITS,
        .bParityType = USB_CDC_NO_PARITY,
        .bDataBits   = 8,
    };

    switch (req->bmRequest & USB_REQ_TYPE_MASK) {

    case USB_REQ_TYPE_CLASS:
        switch (req->bmRequest & USB_REQ_DIR_MASK) {

        case USB_D2H:
            switch (req->bRequest) {

            case USB_CDC_GET_LINE_CODING:
                USBD_CtlSendData(dev, (uint8_t *)(&line_coding), MIN(req->wLength, sizeof(line_coding)));
                break;
            }
            break;
        }
        break;
    }

    return USBD_OK;
}

static uint8_t usb_vcp_class_data_in(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t ep_num) {
    if ((ep_num | USB_EP_DIR_IN) == state->ep_in) {
        state->ep_in_is_idle = 1;
    }
    return USBD_OK;
}

static uint8_t usb_vcp_class_data_out(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t ep_num) {
    if (ep_num == state->ep_out) {
        uint32_t len = USBD_LL_GetRxDataSize(dev, ep_num);

        // Write into the rx ring buffer
        usb_rbuf_t *b = &state->rx_ring;
        size_t mask = b->cap - 1;
        size_t i;
        for (i = 0; i < len; i++) {
            if (state->rx_intr_fn != NULL) {
                if (state->rx_packet[i] == state->rx_intr_byte) {
                    state->rx_intr_fn();
                }
            }
            if (!ring_full(b)) {
                b->buf[b->write & mask] = state->rx_packet[i];
                b->write++;
            }
        }

        // Prepare the OUT EP to receive next packet
        USBD_LL_PrepareReceive(dev, state->ep_out, state->rx_packet, state->max_packet_len);
    }
    return USBD_OK;
}

static uint8_t usb_vcp_class_sof(USBD_HandleTypeDef *dev, usb_vcp_state_t *state) {
    if (!state->ep_in_is_idle) {
        return USBD_OK;
    }

    // Read from the tx ring buffer
    usb_rbuf_t *b = &state->tx_ring;
    uint8_t *buf = state->tx_packet;
    size_t len = state->max_packet_len;
    size_t mask = b->cap - 1;
    size_t i;
    for (i = 0; (i < len) && !ring_empty(b); i++) {
        buf[i] = b->buf[b->read & mask];
        b->read++;
    }

    if (i > 0) {
        state->ep_in_is_idle = 0;
        USBD_LL_Transmit(&usb_dev_handle, state->ep_in, buf, (uint16_t)i);
    }

    return USBD_OK;
}
