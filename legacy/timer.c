/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2016 Saleem Rashid <trezor@saleemrashid.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>

#include <libopencm3/cm3/systick.h>
#include <libopencm3/cm3/vector.h>
#include <libopencm3/stm32/rcc.h>

#include "buttons.h"
#include "layout.h"
#include "sys.h"
#include "timer.h"

/* 1 tick = 1 ms */
extern volatile uint32_t system_millis;
uint8_t ucTimeFlag;

/*
 * delay ms
 */
void delay_ms(uint32_t uiDelay_Ms) {
  uint32_t uiTimeout = uiDelay_Ms * 30000;
  while (uiTimeout--) {
    __asm__("nop");
  }
}
void delay_us(uint32_t uiDelay_us) {
  uint32_t uiTimeout = uiDelay_us * 30;
  while (uiTimeout--) {
    __asm__("nop");
  }
}

#define TIMER_NUM 2
typedef struct {
  char name[32];
  uint32_t current;
  uint32_t cycle;
  timer_func fp;
} TimerDsec;

TimerDsec timer_array[TIMER_NUM] = {0};

void register_timer(char *name, uint32_t cyc, timer_func fp) {
  int i;

  for (i = 0; i < TIMER_NUM; i++) {
    if (!timer_array[i].fp) {
      strcpy(timer_array[i].name, name);
      timer_array[i].current = system_millis;
      timer_array[i].cycle = cyc;
      timer_array[i].fp = fp;
      return;
    }
  }
}

void unregister_timer(char *name) {
  int i;

  for (i = 0; i < TIMER_NUM; i++) {
    if (!strcmp(timer_array[i].name, name)) {
      memset(timer_array[i].name, 0x00, 32);
      timer_array[i].fp = NULL;
      return;
    }
  }
}

/*
 * Initialise the Cortex-M3 SysTick timer
 */
void timer_init(void) {
  system_millis = 0;
  ucTimeFlag = 0;

  /*
   * MCU clock (120 MHz) as source
   *
   *     (120 MHz / 8) = 15 clock pulses
   *
   */
  systick_set_clocksource(STK_CSR_CLKSOURCE_AHB_DIV8);
  STK_CVR = 0;

  /*
   * 1 tick = 1 ms @ 120 MHz
   *
   *     (15 clock pulses * 1000 ms) = 15000 clock pulses
   *
   * Send an interrupt every (N - 1) clock pulses
   */
  systick_set_reload(14999);

  /* SysTick as interrupt */
  systick_interrupt_enable();

  systick_counter_enable();
}

void sys_tick_handler(void) {
  int i;
  system_millis++;

  for (i = 0; i < TIMER_NUM; i++) {
    if (timer_array[i].fp) {
      if ((system_millis - timer_array[i].current) > timer_array[i].cycle) {
        timer_array[i].current = system_millis;
        timer_array[i].fp();
      }
    }
  }
}
