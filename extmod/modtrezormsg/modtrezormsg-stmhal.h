extern struct _USBD_HandleTypeDef hUSBDDevice;
extern uint8_t USBD_HID_SendReport(struct _USBD_HandleTypeDef *pdev, uint8_t *report, uint16_t len);
extern int USBD_HID_Rx(uint8_t *buf, uint32_t len, uint32_t timeout);

extern I2C_HandleTypeDef I2CHandle1;
extern HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint8_t *pData, uint16_t Size, uint32_t Timeout);

void msg_init(void)
{
}

ssize_t msg_recv(uint8_t *iface, uint8_t *buf, size_t len)
{
    *iface = 0; // use always interface 0 for now
    return USBD_HID_Rx(buf, len, 1);
}

ssize_t msg_send(uint8_t iface, const uint8_t *buf, size_t len)
{
    (void)iface; // ignore interface for now
    USBD_HID_SendReport(&hUSBDDevice, (uint8_t *)buf, len);
    return len;
}

// this should match values used in trezorui_poll_sdl_event() in modtrezorui/display-unix.h
uint32_t msg_poll_ui_event(void)
{
    static uint8_t data[16], old_data[16];
    if (HAL_OK != HAL_I2C_Master_Receive(&I2CHandle1, 56 << 1, data, 16, 1)) {
        return 0; // read failure
    }
    if (0 == memcmp(data, old_data, 16)) {
        return 0; // no new event
    }
    uint32_t r = 0;
    if (old_data[2] == 0 && data[2] == 1) {
        r = 0x00010000 + (data[4] << 8) + data[6]; // touch start
    } else
    if (old_data[2] == 1 && data[2] == 1) {
        r = 0x00020000 + (data[4] << 8) + data[6]; // touch move
    }
    if (old_data[2] == 1 && data[2] == 0) {
        r = 0x00040000 + (data[4] << 8) + data[6]; // touch end
    }
    memcpy(old_data, data, 16);
    return r;
}
