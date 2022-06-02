
#include "common.h"
#include "irq.h"

extern __IO uint32_t uwTick;

void mp_hal_delay_ms(uint32_t delay) { hal_delay(delay); }

uint32_t mp_hal_ticks_ms(void) { return uwTick; }