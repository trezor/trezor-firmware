
#include <trezor_bsp.h>

#ifndef TREZORHAL_NFC_INTERNAL_H
#define TREZORHAL_NFC_INTERNAL_H

HAL_StatusTypeDef nfc_spi_transmit_receive(const uint8_t *txData,
                                           uint8_t *rxData, uint16_t length);

uint32_t nfc_create_timer(uint16_t time);

bool nfc_timer_is_expired(uint32_t timer);

void nfc_ext_irq_set_callback(void (*cb)(void));

#endif
