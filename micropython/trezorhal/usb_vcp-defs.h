/*
 * Copyright (c) Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

typedef struct __attribute__((packed)) {
    uint8_t bFunctionLength;
    uint8_t bDescriptorType;
    uint8_t bDescriptorSubtype;
    uint16_t bcdCDC;
} usb_vcp_header_descriptor_t;

typedef struct __attribute__((packed)) {
    uint8_t bFunctionLength;
    uint8_t bDescriptorType;
    uint8_t bDescriptorSubtype;
    uint8_t bmCapabilities;
    uint8_t bDataInterface;
} usb_vcp_cm_descriptor_t;

typedef struct __attribute__((packed)) {
    uint8_t bFunctionLength;
    uint8_t bDescriptorType;
    uint8_t bDescriptorSubtype;
    uint8_t bmCapabilities;
} usb_vcp_acm_descriptor_t;

typedef struct __attribute__((packed)) {
    uint8_t bFunctionLength;
    uint8_t bDescriptorType;
    uint8_t bDescriptorSubtype;
    uint8_t bControlInterface;
    uint8_t bSubordinateInterface0;
} usb_vcp_union_descriptor_t;

typedef struct __attribute__((packed)) {
    usb_interface_assoc_descriptor_t assoc;
    usb_interface_descriptor_t iface_cdc;
    usb_vcp_header_descriptor_t fheader; // Class-Specific Descriptor Header Format
    usb_vcp_cm_descriptor_t fcm;         // Call Management Functional Descriptor
    usb_vcp_acm_descriptor_t facm;       // Abstract Control Management Functional Descriptor
    usb_vcp_union_descriptor_t funion;   // Union Interface Functional Descriptor
    usb_endpoint_descriptor_t ep_cmd;
    usb_interface_descriptor_t iface_data;
    usb_endpoint_descriptor_t ep_in;
    usb_endpoint_descriptor_t ep_out;
} usb_vcp_descriptor_block_t;

typedef struct __attribute__((packed)) {
    uint32_t dwDTERate;
    uint8_t bCharFormat; // usb_cdc_line_coding_bCharFormat_t
    uint8_t bParityType; // usb_cdc_line_coding_bParityType_t
    uint8_t bDataBits;
} usb_cdc_line_coding_t;

typedef enum {
    USB_CDC_1_STOP_BITS   = 0,
    USB_CDC_1_5_STOP_BITS = 1,
    USB_CDC_2_STOP_BITS   = 2,
} usb_cdc_line_coding_bCharFormat_t;

typedef enum {
    USB_CDC_NO_PARITY    = 0,
    USB_CDC_ODD_PARITY   = 1,
    USB_CDC_EVEN_PARITY  = 2,
    USB_CDC_MARK_PARITY  = 3,
    USB_CDC_SPACE_PARITY = 4,
} usb_cdc_line_coding_bParityType_t;

typedef struct {
    uint8_t iface_num;           // Address of this VCP interface
    uint8_t data_iface_num;      // Address of data interface of the VCP interface association
    uint8_t ep_cmd;              // Address of IN CMD endpoint (with the highest bit set)
    uint8_t ep_in;               // Address of IN endpoint (with the highest bit set)
    uint8_t ep_out;              // Address of OUT endpoint
    uint8_t polling_interval;    // In units of 1ms
    uint8_t max_data_packet_len;
} usb_vcp_info_t;

typedef struct {
    uint8_t is_connected;
    uint8_t in_idle;
    // uint8_t cmd_op_code;
    // uint8_t cmd_length;

    // Configuration (copied from usb_vcp_info_t on init)
    uint8_t data_iface_num;
    uint8_t ep_cmd;
    uint8_t ep_in;
    uint8_t ep_out;
    uint8_t polling_interval;
    uint8_t max_data_packet_len;

    const usb_vcp_descriptor_block_t *desc_block;
} usb_vcp_state_t;

int usb_vcp_add(const usb_vcp_info_t *vcp_info);
int usb_vcp_can_read(uint8_t iface_num);
int usb_vcp_can_write(uint8_t iface_num);
int usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len);
int usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len);

int usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len, uint32_t timeout);
int usb_vcp_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len, uint32_t timeout);
