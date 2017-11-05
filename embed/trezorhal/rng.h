#ifndef TREZORHAL_RNG_H
#define TREZORHAL_RNG_H

#include STM32_HAL_H

void rng_init(void);
uint32_t rng_read(const uint32_t previous, const uint32_t compare_previous);
uint32_t rng_get(void);

#endif
