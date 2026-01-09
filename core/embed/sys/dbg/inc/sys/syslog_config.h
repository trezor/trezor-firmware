
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

#ifdef TREZOR_EMULATOR
#define SYSLOG_DEFAULT_LOG_LEVEL LOG_LEVEL_INF
#endif

// Maximum default log level for all modules if not overriden in
// by defining SYSLOG_<module_name>_MAX_LOG_LEVEL during compilation
#ifndef SYSLOG_DEFAULT_LOG_LEVEL
#define SYSLOG_DEFAULT_LOG_LEVEL LOG_LEVEL_OFF
#endif

// Maximum default log level for specific modules
// (can be overriden by defining SYSLOG_<module_name>_MAX_LOG_LEVEL)

#ifndef SYSLOG_emulator_MAX_LOG_LEVEL
#define SYSLOG_emulator_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

#ifndef SYSLOG_coreapp_main_MAX_LOG_LEVEL
#define SYSLOG_coreapp_main_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

#ifndef SYSLOG_bootutils_MAX_LOG_LEVEL
#define SYSLOG_bootutils_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

#ifndef SYSLOG_suspend_MAX_LOG_LEVEL
#define SYSLOG_suspend_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

#ifndef SYSLOG_touch_driver_MAX_LOG_LEVEL
#define SYSLOG_touch_driver_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

#ifndef SYSLOG_display_driver_MAX_LOG_LEVEL
#define SYSLOG_display_driver_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

#ifndef SYSLOG_haptic_driver_MAX_LOG_LEVEL
#define SYSLOG_haptic_driver_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

#ifndef SYSLOG_ble_driver_MAX_LOG_LEVEL
#define SYSLOG_ble_driver_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

// Optiga command log is relatively quiet
#ifndef SYSLOG_optiga_MAX_LOG_LEVEL
#define SYSLOG_optiga_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

// Optiga transport log can be spammy
#ifndef SYSLOG_optiga_transport_MAX_LOG_LEVEL
#define SYSLOG_optiga_transport_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif

// Add more module-specific max log level definitions here...
