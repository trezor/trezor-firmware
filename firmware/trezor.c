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

#include "trezor.h"
#include "oled.h"
#include "bitmaps.h"
#include "util.h"
#include "usb.h"
#include "setup.h"
#include "storage.h"
#include "layout.h"
#include "layout2.h"
#include "rng.h"
#include "timer.h"
#include "buttons.h"

uint32_t __stack_chk_guard;

void __attribute__((noreturn)) __stack_chk_fail(void)
{
	layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Stack smashing", "detected.", NULL, "Please unplug", "the device.", NULL);
	for (;;) {} // loop forever
}

void check_lock_screen(void)
{
	buttonUpdate();

	// wake from screensaver on any button
	if (layoutLast == layoutScreensaver && (button.NoUp || button.YesUp)) {
		layoutHome();
		return;
	}

	// button held for long enough (2 seconds)
	if (layoutLast == layoutHome && button.NoDown >= 285000 * 2) {

		layoutDialog(&bmp_icon_question, "Cancel", "Lock Device", NULL, "Do you really want to", "lock your TREZOR?", NULL, NULL, NULL, NULL);

		// wait until NoButton is released
		usbTiny(1);
		do {
			usbSleep(5);
			buttonUpdate();
		} while (!button.NoUp);

		// wait for confirmation/cancellation of the dialog
		do {
			usbSleep(5);
			buttonUpdate();
		} while (!button.YesUp && !button.NoUp);
		usbTiny(0);

		if (button.YesUp) {
			// lock the screen
			session_clear(true);
			layoutScreensaver();
		} else {
			// resume homescreen
			layoutHome();
		}
	}

	// if homescreen is shown for longer than 10 minutes, lock too
	if (layoutLast == layoutHome) {
		if ((system_millis - system_millis_lock_start) >= 600000) {
			// lock the screen
			session_clear(true);
			layoutScreensaver();
		}
	}
}

int main(void)
{
	__stack_chk_guard = random32();
#ifndef APPVER
	setup();
	oledInit();
#else
	setupApp();
#endif

	timer_init();

#if DEBUG_LOG
	oledSetDebug(1);
#endif

#if DEBUG_LINK
	storage_reset(); // wipe storage if debug link
	storage_reset_uuid();
	storage_commit();
	storage_clearPinArea(); // reset PIN failures if debug link
#endif

	oledDrawBitmap(40, 0, &bmp_logo64);
	oledRefresh();

	storage_init();
	layoutHome();
	usbInit();
	for (;;) {
		usbPoll();
		check_lock_screen();
	}

	return 0;
}
