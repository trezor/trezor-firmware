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

#include <stdint.h>
#include <string.h>

#include "layout2.h"
#include "storage.h"
#include "oled.h"
#include "bitmaps.h"
#include "string.h"
#include "util.h"

void *layoutLast = layoutHome;

void layoutDialogSwipe(LayoutDialogIcon icon, const char *btnNo, const char *btnYes, const char *desc, const char *line1, const char *line2, const char *line3, const char *line4, const char *line5, const char *line6)
{
	layoutLast = layoutDialogSwipe;
	oledSwipeLeft();
	layoutDialog(icon, btnNo, btnYes, desc, line1, line2, line3, line4, line5, line6);
}

void layoutProgressSwipe(const char *desc, int permil, int gearstep)
{
	if (layoutLast == layoutProgressSwipe) {
		oledClear();
	} else {
		layoutLast = layoutProgressSwipe;
		oledSwipeLeft();
	}
	layoutProgress(desc, permil, gearstep);
}

void layoutHome(void)
{
	if (layoutLast == layoutHome) {
		oledClear();
	} else {
		layoutLast = layoutHome;
		oledSwipeLeft();
	}
	const char *label = storage_getLabel();
	if (label && strlen(label) > 0) {
		oledDrawBitmap(44, 4, &bmp_logo48);
		oledDrawStringCenter(OLED_HEIGHT - 8, label);
	} else {
		oledDrawBitmap(40, 0, &bmp_logo64);
	}
	oledRefresh();
}

const char *str_amount(uint64_t amnt, const char *abbr, char *buf, int len)
{
	memset(buf, 0, len);
	uint64_t a = amnt, b = 1;
	int i;
	for (i = 0; i < 8; i++) {
		buf[16 - i] = '0' + (a / b) % 10;
		b *= 10;
	}
	buf[8] = '.';
	for (i = 0; i < 8; i++) {
		buf[7 - i] = '0' + (a / b) % 10;
		b *= 10;
	}
	i = 17;
	while (i > 10 && buf[i - 1] == '0') { // drop trailing zeroes
		i--;
	}
	if (abbr) {
		buf[i] = ' ';
		strlcpy(buf + i + 1, abbr, len - i - 1);
	} else {
		buf[i] = 0;
	}
	const char *r = buf;
	while (*r == '0' && *(r + 1) != '.') r++; // drop leading zeroes
	return r;
}

static char buf_out[32], buf_fee[32];

void layoutConfirmOutput(const CoinType *coin, const TxOutputType *out)
{
	static char first_half[17 + 1];
	strlcpy(first_half, out->address, sizeof(first_half));
	const char *str_out = str_amount(out->amount, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, buf_out, sizeof(buf_out));
	layoutDialogSwipe(DIALOG_ICON_QUESTION,
		"Cancel",
		"Confirm",
		NULL,
		"Confirm sending",
		str_out,
		"to",
		first_half,
		out->address + 17,
		NULL
	);
}

void layoutConfirmTx(const CoinType *coin, uint64_t amount_out, uint64_t amount_fee)
{
	const char *str_out = str_amount(amount_out, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, buf_out, sizeof(buf_out));
	const char *str_fee = str_amount(amount_fee, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, buf_fee, sizeof(buf_fee));
	layoutDialogSwipe(DIALOG_ICON_QUESTION,
		"Cancel",
		"Confirm",
		NULL,
		"Really send",
		str_out,
		"from your wallet?",
		"Fee will be",
		str_fee,
		NULL
	);
}

void layoutFeeOverThreshold(const CoinType *coin, uint64_t fee, uint32_t kb)
{
	(void)kb;
	const char *str_out = str_amount(fee, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, buf_out, sizeof(buf_out));
	layoutDialogSwipe(DIALOG_ICON_QUESTION,
		"Cancel",
		"Confirm",
		NULL,
		"Fee",
		str_out,
		"is unexpectedly high.",
		NULL,
		"Send anyway?",
		NULL
	);
}

void layoutSignMessage(const uint8_t *msg, uint32_t len)
{
	bool ascii = true;
	uint32_t i;
	for (i = 0; i < len; i++) {
		if (msg[i] < 0x20 || msg[i] >= 0x80) {
			ascii = false;
			break;
		}
	}

	char str[4][17];
	memset(str, 0, sizeof(str));
	if (ascii) {
		strlcpy(str[0], (char *)msg, 17);
		if (len > 16) {
			strlcpy(str[1], (char *)msg + 16, 17);
		}
		if (len > 32) {
			strlcpy(str[2], (char *)msg + 32, 17);
		}
		if (len > 48) {
			strlcpy(str[3], (char *)msg + 48, 17);
		}
	} else {
		data2hex(msg, len > 8 ? 8 : len, str[0]);
		if (len > 8) {
			data2hex(msg + 8, len > 16 ? 8 : len - 8, str[1]);
		}
		if (len > 16) {
			data2hex(msg + 16, len > 24 ? 8 : len - 16, str[2]);
		}
		if (len > 24) {
			data2hex(msg + 24, len > 32 ? 8 : len - 24, str[3]);
		}
	}

	layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm", NULL,
		ascii ? "Sign text message?" : "Sign binary message?",
		str[0], str[1], str[2], str[3], NULL);
}
