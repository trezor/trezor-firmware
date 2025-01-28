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

#define ACTUATOR_LRA
#define ACTUATOR_CLOSED_LOOP

#define ACTUATOR_FREQUENCY (260)
#define ACTUATOR_VOLTAGE (0.7)

#define ACTUATOR_LRA_PERIOD ((int)((1000000 / ACTUATOR_FREQUENCY) / 24.615))

// open-loop mode
// V = 21.32 * 10^(-3) * OD_CLAMP * sqrt(1 - fLRA * 800 * 10^(-6))
#define ACTUATOR_OD_CLAMP (37)

// closed-loop mode
// V = (20.58 * 10^(-3) * RATED_VOLTAGE) / sqrt (1 - (4 * tSAMPLE_TIME + 300 *
// 10^(-6)) * fLRA) where tSAMPLE_TIME = 300us, by default
#define ACTUATOR_RATED_VOLTAGE (27)
