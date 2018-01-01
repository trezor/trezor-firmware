#include "py/mphal.h"
#include "usb.h"
#include "common.h"

static int vcp_iface_num = -1;

int mp_hal_stdin_rx_chr(void) {
    ensure(sectrue * (vcp_iface_num >= 0), "vcp stdio is not configured");
    uint8_t c = 0;
    int r = usb_vcp_read_blocking(vcp_iface_num, &c, 1, -1);
    (void)r;
    return c;
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
    if (vcp_iface_num >= 0) {
        int r = usb_vcp_write_blocking(vcp_iface_num, (const uint8_t *)str, len, 0);
        (void)r;
    }
}

void mp_hal_set_vcp_iface(int iface_num) {
    vcp_iface_num = iface_num;
}
