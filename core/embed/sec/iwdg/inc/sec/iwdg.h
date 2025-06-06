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

#define IWDG_MAX_TIME (60 * 60 * 4)  // 4 hours

/**
 * @brief Start the Independent Watchdog, to enforce reset after specified time
 * elapsed.
 *
 * The IWDG is clocked from LSI, which is expected to be set to 250 Hz.
 * The IWDG prescaler is set to 1024, which means that the watchdog
 * will tick every 4.096 s. The time is floored to the nearest multiple of 4.096
 * s.
 *
 * @param time_s Watchdog timeout in seconds. Time is ceiled to IWDG_MAX_TIME.
 */
void iwdg_start(uint32_t time_s);
