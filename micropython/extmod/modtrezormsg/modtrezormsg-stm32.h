/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "usb.h"

void msg_init(void)
{
}

ssize_t msg_recv(uint8_t *iface, uint8_t *buf, size_t len)
{
    int i = usb_hid_read_select(0);
    if (i < 0) {
        return 0;
    }
    *iface = i;
    return usb_hid_read(i, buf, len);
}

ssize_t msg_send(uint8_t iface, const uint8_t *buf, size_t len)
{
    return usb_hid_write_blocking(iface, buf, len, 1000); // 1s timeout
}
