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

#include <string.h>

#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/cm3/scb.h>

#include "bootloader.h"
#include "buttons.h"
#include "setup.h"
#include "usb.h"
#include "oled.h"
#include "util.h"
#include "signatures.h"
#include "layout.h"
#include "serialno.h"
#include "rng.h"

#ifdef APPVER
#error Bootloader cannot be used in app mode
#endif

void layoutFirmwareHash(uint8_t *hash)
{
	char str[4][17];
	int i;
	for (i = 0; i < 4; i++) {
		data2hex(hash + i * 8, 8, str[i]);
	}
	layoutDialog(&bmp_icon_question, "Abort", "Continue", "Compare fingerprints", str[0], str[1], str[2], str[3], NULL, NULL);
}

void show_halt(void)
{
	layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Unofficial firmware", "aborted.", NULL, "Unplug your TREZOR", "and see our support", "page at mytrezor.com");
	system_halt();
}

void show_unofficial_warning(uint8_t *hash)
{
	layoutDialog(&bmp_icon_warning, "Abort", "I'll take the risk", NULL, "WARNING!", NULL, "Unofficial firmware", "detected.", NULL, NULL);

	do {
		delay(100000);
		buttonUpdate();
	} while (!button.YesUp && !button.NoUp);

	if (button.NoUp) {
		show_halt(); // no button was pressed -> halt
	}

	layoutFirmwareHash(hash);

	do {
		delay(100000);
		buttonUpdate();
	} while (!button.YesUp && !button.NoUp);

	if (button.NoUp) {
		show_halt(); // no button was pressed -> halt
	}

	// everything is OK, user pressed 2x Continue -> continue program
}

void load_app(void)
{
	// jump to app
	SCB_VTOR = FLASH_APP_START; // & 0xFFFF;
	__asm__ volatile("msr msp, %0"::"g" (*(volatile uint32_t *)FLASH_APP_START));
	(*(void (**)())(FLASH_APP_START + 4))();
}

int firmware_present;

void bootloader_loop(void)
{
	oledClear();
	oledDrawBitmap(0, 0, &bmp_logo64);
	if (firmware_present) {
		oledDrawString(52, 0, "TREZOR");
		static char serial[25];
		fill_serialno_fixed(serial);
		oledDrawString(52, 20, "Serial No.");
		oledDrawString(52, 40, serial + 12); // second part of serial
		serial[12] = 0;
		oledDrawString(52, 30, serial);      // first part of serial
		oledDrawStringRight(OLED_WIDTH - 1, OLED_HEIGHT - 8, "Loader " VERSTR(VERSION_MAJOR) "." VERSTR(VERSION_MINOR) "." VERSTR(VERSION_PATCH));
	} else {
		oledDrawString(52, 10, "Welcome!");
		oledDrawString(52, 30, "Please visit");
		oledDrawString(52, 50, "trezor.io/start");
	}
	oledRefresh();

	usbInit();
	usbLoop();
}

int check_firmware_sanity(void)
{
	if (memcmp((void *)FLASH_META_MAGIC, "TRZR", 4)) { // magic does not match
		return 0;
	}
	if (*((uint32_t *)FLASH_META_CODELEN) < 4096) { // firmware reports smaller size than 4kB
		return 0;
	}
	if (*((uint32_t *)FLASH_META_CODELEN) > FLASH_TOTAL_SIZE - (FLASH_APP_START - FLASH_ORIGIN)) { // firmware reports bigger size than flash size
		return 0;
	}
	return 1;
}

uint32_t __stack_chk_guard;

void __attribute__((noreturn)) __stack_chk_fail(void)
{
	layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Stack smashing", "detected.", NULL, "Please unplug", "the device.", NULL);
	for (;;) {} // loop forever
}

int main(void)
{
	__stack_chk_guard = random32();
	setup();
	memory_protect();
	oledInit();

	firmware_present = check_firmware_sanity();

	// at least one button is unpressed
	uint16_t state = gpio_port_read(BTN_PORT);
	int unpressed = ((state & BTN_PIN_YES) == BTN_PIN_YES || (state & BTN_PIN_NO) == BTN_PIN_NO);

	if (firmware_present && unpressed) {

		oledClear();
		oledDrawBitmap(40, 0, &bmp_logo64_empty);
		oledRefresh();

		uint8_t hash[32];
		if (!signatures_ok(hash)) {
			show_unofficial_warning(hash);
		}

		delay(100000);

		load_app();
	}

	bootloader_loop();

	return 0;
}
