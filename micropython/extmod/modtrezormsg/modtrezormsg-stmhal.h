/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

extern int usb_hid_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len, uint32_t timeout);
extern int usb_hid_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len, uint32_t timeout);

void msg_init(void)
{
}

ssize_t msg_recv(uint8_t *iface, uint8_t *buf, size_t len)
{
    *iface = 0; // TODO: return proper interface
    return usb_hid_read_blocking(0x00, buf, len, 1);
}

ssize_t msg_send(uint8_t iface, const uint8_t *buf, size_t len)
{
    (void)iface; // TODO: ignore interface for now
    if (len > 0) {
        usb_hid_write_blocking(0x00, buf, len, 1);
    }
    return len;
}
