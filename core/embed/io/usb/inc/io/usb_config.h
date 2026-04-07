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

#include <sys/sysevent.h>

typedef void (*usb_vcp_intr_callback_t)(void);

/**
 * Initialize and configures USB stack and all enabled USB interfaces.
 *
 * @param vcp_intr_callback Optional callback to be called on VCP interrupt.
 */
secbool usb_configure(usb_vcp_intr_callback_t vcp_intr_callback);
