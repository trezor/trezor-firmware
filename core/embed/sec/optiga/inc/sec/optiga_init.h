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

#include <sec/optiga_common.h>

// Security event counter threshold to suspend optiga without postponing
// optiga deinitialization
#define OPTIGA_SEC_SUSPEND_THR 20

/**
 * @brief Initialize optiga driver
 *
 * This function powers up the OPTIGA chip and initializes the communication
 * channel.
 *
 * @return OPTIGA_SUCCESS in case the driver was sucessfully initialized.
 */
optiga_result optiga_init(void);

/**
 * @brief Deinitialize optiga driver
 *
 * Close the communication channel and power down the OPTIGA chip.
 */
void optiga_deinit(void);

/**
 * @brief Close the communication channel to the OPTIGA chip
 *
 * This function should be called when the communication with the OPTIGA chip
 * is no longer needed. It will release any resources associated with the
 * communication channel.
 */
void optiga_close_channel(void);

/**
 * @brief Power down of the OPTIGA chip
 *
 * @note This function should be called after optiga_close_channel().
 */
void optiga_power_down(void);

/**
 * @brief Initializes the optiga driver, establishes a secure channel by
 * providing a shared secret and finally opens the application.
 *
 */
void optiga_init_and_configure(void);

/* *****************************************************************************
 *  KERNEL PART
 * ****************************************************************************/

/**
 * @brief Suspends optiga driver
 *
 * @note This is part of driver is used in KERNEL_MODE since it schedules RTC
 * event to power down the optiga chip when its left powered up due to high
 * SEC counter value.
 */
void optiga_suspend();

/**
 * @brief Resumes optiga driver
 *
 * @note This part of driver is used in KERNEL_MODE since it handles/cancel
 * active RTC power down event when resuming from suspend.
 */
void optiga_resume();
