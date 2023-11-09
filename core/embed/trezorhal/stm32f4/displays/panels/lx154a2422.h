#ifndef LX154A2422_H_
#define LX154A2422_H_

#include "displays/st7789v.h"

void lx154a2422_init_seq(void);
void lx154a2422_gamma(void);
void lx154a2422_rotate(int degrees, display_padding_t* padding);
uint32_t lx154a2422_transform_touch_coords(uint16_t x, uint16_t y);

#endif
