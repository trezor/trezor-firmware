typedef struct __attribute__((packed)) {
    uint8_t bLength;
    uint8_t bDescriptorType;
    uint16_t bcdHID;
    uint8_t bCountryCode;
    uint8_t bNumDescriptors;
    uint8_t bReportDescriptorType;
    uint16_t wReportDescriptorLength;
} usb_hid_descriptor_t;

typedef struct __attribute__((packed)) {
    usb_interface_descriptor_t iface;
    usb_hid_descriptor_t hid;
    usb_endpoint_descriptor_t ep_in;
    usb_endpoint_descriptor_t ep_out;
} usb_hid_descriptor_block_t;

typedef enum {
    USB_HID_SUBCLASS_NONE = 0,
    USB_HID_SUBCLASS_BOOT = 1,
} usb_hid_subclass_t;

typedef enum {
    USB_HID_PROTOCOL_NONE = 0,
    USB_HID_PROTOCOL_KEYBOARD = 1,
    USB_HID_PROTOCOL_MOUSE = 2,
} usb_hid_protocol_t;

typedef struct {
    // Interface configuration
    uint8_t iface_num;  // Address of this HID interface
    uint8_t ep_in;      // Address of IN endpoint (with the highest bit set)
    uint8_t ep_out;     // Address of OUT endpoint

    // HID configuration
    uint8_t subclass;          // usb_iface_subclass_t
    uint8_t protocol;          // usb_iface_protocol_t
    uint8_t max_packet_len;    // rx_buffer should be big enough
    uint8_t polling_interval;  // In units of 1ms
    uint8_t report_desc_len;
    const uint8_t *report_desc;

    // HID read buffer
    uint8_t *rx_buffer;  // Big enough for max_packet_len
} usb_hid_info_t;

typedef struct {
    // HID state
    uint8_t in_idle;       // Set to 1 after IN endpoint gets idle
    uint8_t protocol;      // For SET_PROTOCOL/GET_PROTOCOL setup reqs
    uint8_t idle_rate;     // For SET_IDLE/GET_IDLE setup reqs
    uint8_t alt_setting;   // For SET_INTERFACE/GET_INTERFACE setup reqs
    uint8_t rx_buffer_len; // Length of data read into rx_buffer

    // HID configuration (copied from usb_hid_info_t on init)
    uint8_t ep_in;
    uint8_t ep_out;
    uint8_t max_packet_len;
    uint8_t report_desc_len;
    uint8_t *rx_buffer;
    const uint8_t *report_desc;
    const usb_hid_descriptor_block_t *desc_block;
} usb_hid_state_t;

int usb_hid_add(const usb_hid_info_t *hid_info);
int usb_hid_can_read(uint8_t iface_num);
int usb_hid_can_write(uint8_t iface_num);
int usb_hid_read(uint8_t iface_num, uint8_t *buf, uint32_t len);
int usb_hid_write(uint8_t iface_num, const uint8_t *buf, uint32_t len);

int usb_hid_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len, uint32_t timeout);
int usb_hid_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len, uint32_t timeout);
