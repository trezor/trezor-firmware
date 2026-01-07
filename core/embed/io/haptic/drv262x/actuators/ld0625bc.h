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

/* Actuator type: ACTUATOR_LRA or ACTUATOR_ERM */
#define ACTUATOR_LRA

/* Actuator control mode: ACTUATOR_CLOSED_LOOP or ACTUATOR_OPEN_LOOP */
#define ACTUATOR_CLOSED_LOOP

/* Actuator resonant frequency */
#define ACTUATOR_FREQUENCY_HZ (260)
#define ACTUATOR_VOLTAGE (0.7)

#define ACTUATOR_LRA_PERIOD ((int)((1000000 / ACTUATOR_FREQUENCY) / 24.615))

// V = (20.58 * 10^(-3) * RATED_VOLTAGE) / sqrt (1 - (4 * tSAMPLE_TIME + 300 *
// 10^(-6)) * fLRA) where tSAMPLE_TIME = 300us, by default
#define ACTUATOR_RATED_VOLTAGE (27)

// V = 21.32 * 10^(-3) * OD_CLAMP * sqrt(1 - fLRA * 800 * 10^(-6))
#define ACTUATOR_OD_CLAMP (150)

#define ACTUATOR_FB_BRK_FACTOR 3
#define ACTUATOR_LOOP_GAIN 1
#define ACTUATOR_BEMF_GAIN 2

// DRIVE_TIME ~= (0.5 * (1000/ACTUATOR_FREQUENCY_HZ) - 0.5) / 0.1
#define ACTUATOR_DRIVE_TIME 16
#define ACTUATOR_IDISS_TIME 1
#define ACTUATOR_BLANK_TIME 1
#define ACTUATOR_SAMPLE_TIME 3
#define ACTUATOR_ZC_DET_TIME 0
