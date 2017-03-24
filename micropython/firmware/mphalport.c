#include "py/mphal.h"

// void USBD_CDC_TxAlways(const uint8_t *buf, uint32_t len);
// int USBD_CDC_Rx(uint8_t *buf, uint32_t len, uint32_t timeout);

int mp_hal_stdin_rx_chr(void) {
    for (;;) {
    //     byte c;
    //     if (USBD_CDC_Rx(&c, 1, 0) != 0) {
    //         return c;
    //     }
    }
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
    // USBD_CDC_TxAlways((const uint8_t*)str, len);
}
