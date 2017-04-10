#include "py/mphal.h"
#include "usb.h"

#define VCP_IFACE         0x01
#define VCP_READ_TIMEOUT  25
#define VCP_WRITE_TIMEOUT 5

int mp_hal_stdin_rx_chr(void) {
    uint8_t c = 0;
    while (usb_vcp_read_blocking(VCP_IFACE, &c, 1, VCP_READ_TIMEOUT) < 1);
    return c;
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
    usb_vcp_write_blocking(VCP_IFACE, (const uint8_t *)str, len, VCP_WRITE_TIMEOUT);
}
