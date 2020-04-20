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

#ifndef __TIMER_H__
#define __TIMER_H__

#include <stdint.h>
#include "supervise.h"

#define autoPowerOffMsDefault (90 * 1000U)

#define sys_time1s 1000
#define timer1s 1000

#define default_time timer1s * 5
#define default_oper_time timer1s * 60
#define default_resp_time timer1s * 60

typedef enum _TimerOut {
  timer_out_cmd = 0,
  timer_out_countdown,
  timer_out_oper,
  timer_out_null,
} TimerOut;

typedef void (*timer_func)(void);

void register_timer(char *name, uint32_t cyc, timer_func fp);
void unregister_timer(char *name);

void delay_ms(uint32_t uiDelay_Ms);
void delay_us(uint32_t uiDelay_us);

void timer_init(void);

void timer_out_set(TimerOut type, uint32_t val);
uint32_t timer_out_get(TimerOut type);

#if EMULATOR
uint32_t timer_ms(void);
#else
#define timer_ms svc_timer_ms
#endif

#endif
