
#ifndef CORE_LHS200KB_IF21_H
#define CORE_LHS200KB_IF21_H
// ST7789_V IC controller

#include "displays/st7789v.h"

void lhs200kb_if21_init_seq(void);
void lhs200kb_if21_rotate(int degrees, buffer_offset_t* offset);
uint32_t lhs200kb_if21_transform_touch_coords(uint16_t x, uint16_t y);

#endif  // CORE_LHS200KB_IF21_H
