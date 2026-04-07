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

/**
 * @brief Switches the CPU to STOP2 low-power mode.
 *
 * This function blocks until an interrupt wakes the CPU.
 * Upon wake-up, it restores the system clock so the CPU can run at full speed.
 */
void suspend_cpu(void);

/**
 * @brief Suspends secure peripherals.
 *
 * This function is called before the device enters a low-power state.
 * It suspends secure peripherals to reduce power consumption.
 */
void suspend_secure_drivers(void);

/**
 * @brief Resumes secure peripherals.
 *
 * This function is called when the device exits a low-power state.
 * It resumes secure peripherals that were suspended before entering
 * the low-power state.
 */
void resume_secure_drivers(void);
