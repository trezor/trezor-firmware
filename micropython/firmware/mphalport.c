#include "py/mphal.h"
#include "usb.h"

#define VCP_IFACE         0x01
#define VCP_WRITE_TIMEOUT 25

int mp_hal_stdin_rx_chr(void) {
    for (;;) {

    }
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
    usb_vcp_write_blocking(VCP_IFACE, (const uint8_t *)str, len, VCP_WRITE_TIMEOUT);
}
