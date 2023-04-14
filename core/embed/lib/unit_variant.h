#ifndef _UNIT_VARIANT_H
#define _UNIT_VARIANT_H

#include <stdbool.h>
#include <stdint.h>

void unit_variant_init(void);
bool unit_variant_present(void);
uint8_t unit_variant_get_color(void);
bool unit_variant_get_btconly(void);

#endif  //_UNIT_VARIANT_H
