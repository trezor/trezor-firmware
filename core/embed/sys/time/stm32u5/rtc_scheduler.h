/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

#include <trezor_types.h>

#include <sys/rtc.h>

#define MAX_SCHEDULE_LEN 16

_Static_assert((MAX_SCHEDULE_LEN & (MAX_SCHEDULE_LEN - 1)) == 0,
               "MAX_SCHEDULE_LEN must be a power of 2");

typedef struct {
  uint32_t id;
  uint32_t timestamp;
  rtc_wakeup_callback_t callback;
  void *callback_context;
} rtc_wakeup_event_t;

typedef struct {
  uint8_t head;
  uint8_t tail;
  rtc_wakeup_event_t events[MAX_SCHEDULE_LEN];
} rtc_wakeup_schedule_t;

bool rtc_schedule_push(rtc_wakeup_schedule_t *sch, rtc_wakeup_event_t *event);
bool rtc_schedule_pop(rtc_wakeup_schedule_t *sch, rtc_wakeup_event_t *event);
bool rtc_schedule_remove(rtc_wakeup_schedule_t *sch, uint32_t event_id);
