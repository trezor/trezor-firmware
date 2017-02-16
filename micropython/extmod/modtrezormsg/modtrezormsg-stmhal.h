/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "touch.h"

extern struct _USBD_HandleTypeDef hUSBDDevice;
extern uint8_t USBD_HID_SendReport(struct _USBD_HandleTypeDef *pdev, uint8_t *report, uint16_t len);
extern int USBD_HID_Rx(uint8_t *buf, uint32_t len, uint32_t timeout);

void msg_init(void)
{
    touch_init();
}

ssize_t msg_recv(uint8_t *iface, uint8_t *buf, size_t len)
{
    *iface = 0; // TODO: return proper interface
    return USBD_HID_Rx(buf, len, 1);
}

ssize_t msg_send(uint8_t iface, const uint8_t *buf, size_t len)
{
    (void)iface; // TODO: ignore interface for now
    if (len > 0) {
        USBD_HID_SendReport(&hUSBDDevice, (uint8_t *)buf, len);
    }
    return len;
}

// this should match values used in trezorui_poll_sdl_event() in modtrezorui/display-unix.h
uint32_t msg_poll_ui_event(void)
{
    return touch_event();
}
