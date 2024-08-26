#ifndef LX154A2422_H_
#define LX154A2422_H_

#include "displays/st7789v.h"

void lx154a2482_init_seq(void);
void lx154a2482_gamma(void);
void lx154a2482_rotate(int degrees, display_padding_t* padding);

#endif
