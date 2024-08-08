#ifndef _UNIT_VARIANT_H
#define _UNIT_VARIANT_H

#include <stdbool.h>
#include <stdint.h>

#ifdef KERNEL_MODE

void unit_variant_init(void);

#endif  // KERNEL_MODE

bool unit_variant_present(void);
uint8_t unit_variant_get_color(void);
uint8_t unit_variant_get_packaging(void);
bool unit_variant_get_btconly(void);

bool unit_variant_is_sd_hotswap_enabled(void);

#endif  //_UNIT_VARIANT_H
