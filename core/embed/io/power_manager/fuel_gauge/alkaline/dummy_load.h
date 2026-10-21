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

#include <sys/systimer.h>
#include <trezor_types.h>

#define DUMMY_LOAD_MA 150.0f  // Extra current when dummy load is ON [mA].
/**
 * @brief Initialize the dummy load control pin
 *
 * Configures the enable pin as a push-pull output and leaves the load
 * switched off.
 *
 * @param pulse_timer[out] New timer to control CUR_DUMMY pin
 */
ts_t dummy_load_init(systimer_t* pulse_timer);

/**
 * @brief Connect the dummy load to the battery for defined duration.
 *
 * @param pulse_timer Timer created by dummy_load_init()
 * @param on_duration_ms Pulse length in milliseconds; 0 leaves the load on
 *                       until dummy_load_off() is called
 */
void dummy_load_on(systimer_t* pulse_timer, uint32_t on_duration_ms);

/**
 * @brief Disconnect the dummy load from the battery
 */
void dummy_load_off(void);
