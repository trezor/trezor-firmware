/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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

#include "buttons.h"

#if !HEADLESS
#include <SDL.h>
#endif

uint16_t buttonRead(void) {
	uint16_t state = 0;

#if !HEADLESS
	const uint8_t *scancodes = SDL_GetKeyboardState(NULL);
	if (scancodes[SDL_SCANCODE_LEFT]) {
		state |= BTN_PIN_NO;
	}
	if (scancodes[SDL_SCANCODE_RIGHT]) {
		state |= BTN_PIN_YES;
	}
#endif

	return ~state;
}
