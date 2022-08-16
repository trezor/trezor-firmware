
#include "common.h"
#include "irq.h"

extern __IO uint32_t uwTick;

__IO int64_t ticks = 0;
__IO int64_t ticks_ms_start = 0;
__IO int64_t ticks_ms_end = 0;
__IO int64_t systick_start = 0;
__IO int64_t systick_end = 0;
__IO int64_t ticks_diff = 0;
__IO int64_t ticks_acc = 0;
__IO int64_t total_acc = 0;

void init_ticks(void) {
  ticks_ms_start = hal_ticks_ms();
  systick_start = SysTick->VAL;
  ticks = (ticks_ms_start * 180000) + systick_start;
}

void get_ticks(void) {
  ticks_ms_end = hal_ticks_ms();
  systick_end = SysTick->VAL;
  volatile int64_t ticks_now = (ticks_ms_end * 180000) + systick_end;
  volatile int64_t ticks_diff_tmp = ticks_now - ticks;
  ticks = ticks_now;
  ticks_diff = ticks_diff_tmp;
  ticks_acc += ticks_diff_tmp;
  total_acc++;
}

void clear_acc(void) {
  ticks_acc = 0;
  total_acc = 0;
}
