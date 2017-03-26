/* usb_vcp_add adds and configures new USB VCP interface according to
 * configuration options passed in `info`. */
int usb_vcp_add(const usb_vcp_info_t *info) {
    return 0;
}

int usb_vcp_can_read(uint8_t iface_num) {
    return 0;
}

int usb_vcp_can_write(uint8_t iface_num) {
    return 0;
}

int usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
    return 0;
}

int usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
    return 0;
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
            return 0;  // Timeout
        }
        __WFI();  // Enter sleep mode, waiting for interrupt
    }
    return usb_vcp_write(iface_num, buf, len);
}

static int usb_vcp_class_init(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t cfg_idx) {
    return USBD_OK;
}

static int usb_vcp_class_deinit(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t cfg_idx) {
    return USBD_OK;
}

static int usb_vcp_class_setup(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, USBD_SetupReqTypedef *req) {
    return USBD_OK;
}

static uint8_t usb_vcp_class_data_in(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t ep_num) {
    return USBD_OK;
}

static uint8_t usb_vcp_class_data_out(USBD_HandleTypeDef *dev, usb_vcp_state_t *state, uint8_t ep_num) {
    return USBD_OK;
}
