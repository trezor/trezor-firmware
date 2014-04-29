/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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

#include "ssp.h"
#include "rng.h"
#include "layout.h"

void *__stack_chk_guard = 0;

void __stack_chk_guard_setup(void)
{
	unsigned char * p;
	p = (unsigned char *) &__stack_chk_guard;
	p[0] = 0;
	p[1] = 0;
	p[2] = '\n';
	p[3] = 0xFF; // random32() & 0xFF;
}

void __attribute__((noreturn)) __stack_chk_fail(void)
{
	layoutDialog(DIALOG_ICON_ERROR, NULL, NULL, NULL, "Stack smashing", "detected.", NULL, "Please unplug", "the device.", NULL);
	for (;;) {} // loop forever
}
