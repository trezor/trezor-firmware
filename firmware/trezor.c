/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "common.h"
#include "trezor.h"
#include "oled.h"
#include "bitmaps.h"
#include "util.h"
#include "usb.h"
#include "setup.h"
#include "config.h"
#include "layout.h"
#include "layout2.h"
#include "rng.h"
#include "timer.h"
#include "buttons.h"
#include "gettext.h"
#include "bl_check.h"
#include "memzero.h"
#include <libopencm3/stm32/desig.h>

/* Screen timeout */
uint32_t system_millis_lock_start;

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

		layoutDialog(&bmp_icon_question, _("Cancel"), _("Lock Device"), NULL, _("Do you really want to"), _("lock your TREZOR?"), NULL, NULL, NULL, NULL);

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

	// if homescreen is shown for too long
	if (layoutLast == layoutHome) {
		if ((timer_ms() - system_millis_lock_start) >= config_getAutoLockDelayMs()) {
			// lock the screen
			session_clear(true);
			layoutScreensaver();
		}
	}
}

int main(void)
{
#if EMULATOR
    memzero(HW_ENTROPY_DATA, HW_ENTROPY_LEN);
    HW_ENTROPY_DATA[0] = 1;
#else
    desig_get_unique_id((uint32_t*)HW_ENTROPY_DATA);
#endif

#ifndef APPVER
	setup();
	__stack_chk_guard = random32(); // this supports compiler provided unpredictable stack protection checks
	oledInit();
#else
	check_bootloader();
	setupApp();
	__stack_chk_guard = random32(); // this supports compiler provided unpredictable stack protection checks
#endif

	if (!is_mode_unprivileged()) {

		timer_init();

#ifdef APPVER
		// enable MPU (Memory Protection Unit)
		mpu_config();
#endif
	}

#if DEBUG_LINK
	oledSetDebugLink(1);
	config_wipe();
#endif

	oledDrawBitmap(40, 0, &bmp_logo64);
	oledRefresh();

	config_init();
	layoutHome();
	usbInit();
	for (;;) {
		usbPoll();
		check_lock_screen();
	}

	return 0;
}
