#ifndef LX154A2422_H_
#define LX154A2422_H_

#include "displays/st7789v.h"

void lx154a2422_init_seq();
void lx154a2422_gamma();
void lx154a2422_rotate(int degrees, buffer_offset_t* offset);
uint32_t lx154a2422_transform_touch_coords(uint16_t x, uint16_t y);

#endif
