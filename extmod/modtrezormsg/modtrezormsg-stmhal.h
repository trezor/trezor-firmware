extern struct _USBD_HandleTypeDef hUSBDDevice;
extern int switch_get(void);
extern uint8_t USBD_HID_SendReport(struct _USBD_HandleTypeDef *pdev, uint8_t *report, uint16_t len);
extern int USBD_HID_Rx(uint8_t *buf, uint32_t len, uint32_t timeout);

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
    static int lp = 0;
    uint32_t r = 0;
    int p = switch_get();
    if (lp == 0 && p == 1) {
        r = 0x00010000; // touch start
    } else
    if (lp == 1 && p == 1) {
        r = 0x00020000; // touch move
    }
    if (lp == 1 && p == 0) {
        r = 0x00040000; // touch end
    }
    lp = p;
    return r;
}
