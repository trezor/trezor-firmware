typedef struct __attribute__((packed)) {
} usb_vcp_descriptor_t;

typedef struct __attribute__((packed)) {
    usb_interface_descriptor_t iface;
    usb_vcp_descriptor_t vcp;
    usb_endpoint_descriptor_t ep_in;
    usb_endpoint_descriptor_t ep_out;
    usb_endpoint_descriptor_t ep_cmd;
} usb_vcp_descriptor_block_t;

typedef struct {
    // Interface configuration
    uint8_t iface_num;  // Address of this VCP interface
    uint8_t ep_in;      // Address of IN endpoint (with the highest bit set)
    uint8_t ep_out;     // Address of OUT endpoint
    uint8_t ep_cmd;     // Address of CMD endpoint
} usb_vcp_info_t;

typedef struct {
    const usb_vcp_descriptor_block_t *desc_block;
} usb_vcp_state_t;

int usb_vcp_add(const usb_vcp_info_t *vcp_info);
int usb_vcp_can_read(uint8_t iface_num);
int usb_vcp_can_write(uint8_t iface_num);
int usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len);
int usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len);

int usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len, uint32_t timeout);
int usb_vcp_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len, uint32_t timeout);
