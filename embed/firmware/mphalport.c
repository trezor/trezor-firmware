#include "py/mphal.h"
#include "usb.h"
#include "common.h"

static int vcp_iface_num = -1;

int mp_hal_stdin_rx_chr(void) {
    #define VCP_READ_TIMEOUT  25

    if (vcp_iface_num != -1) {
        uint8_t c = 0;
        while (usb_vcp_read_blocking(vcp_iface_num, &c, 1, VCP_READ_TIMEOUT) < 1) {
            // Wait until we read a byte
        }
        return c;
    } else {
        __fatal_error("vcp stdio is not configured", __FILE__, __LINE__, __func__);
    }
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
    #define VCP_WRITE_TIMEOUT 0

    if (vcp_iface_num != -1) {
        usb_vcp_write_blocking(vcp_iface_num, (const uint8_t *)str, len, VCP_WRITE_TIMEOUT);
    } else {
        // no-op
    }
}

void mp_hal_set_vcp_iface(int iface_num) {
    vcp_iface_num = iface_num;
}
