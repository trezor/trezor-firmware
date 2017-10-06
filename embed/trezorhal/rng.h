#ifndef __TREZORHAL_RNG_H__
#define __TREZORHAL_RNG_H__

int rng_init(void);
uint32_t rng_get(void);
uint32_t rng_read(const uint32_t previous, const uint32_t compare_previous);

#endif
