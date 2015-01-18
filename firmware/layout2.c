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
#include "qr_encode.h"

void *layoutLast = layoutHome;

void layoutDialogSwipe(LayoutDialogIcon icon, const char *btnNo, const char *btnYes, const char *desc, const char *line1, const char *line2, const char *line3, const char *line4, const char *line5, const char *line6)
{
	layoutLast = layoutDialogSwipe;
	oledSwipeLeft();
	layoutDialog(icon, btnNo, btnYes, desc, line1, line2, line3, line4, line5, line6);
}

void layoutProgressSwipe(const char *desc, int permil)
{
	if (layoutLast == layoutProgressSwipe) {
		oledClear();
	} else {
		layoutLast = layoutProgressSwipe;
		oledSwipeLeft();
	}
	layoutProgress(desc, permil);
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

// split longer string into 4 rows, rowlen chars each
const char **split_message(const uint8_t *msg, uint32_t len, uint32_t rowlen)
{
	static char str[4][32 + 1];
	if (rowlen > 32) {
		rowlen = 32;
	}
	memset(str, 0, sizeof(str));
	strlcpy(str[0], (char *)msg, rowlen + 1);
	if (len > rowlen) {
		strlcpy(str[1], (char *)msg + rowlen, rowlen + 1);
	}
	if (len > rowlen * 2) {
		strlcpy(str[2], (char *)msg + rowlen * 2, rowlen + 1);
	}
	if (len > rowlen * 3) {
		strlcpy(str[3], (char *)msg + rowlen * 3, rowlen + 1);
	}
	static const char *ret[4] = { str[0], str[1], str[2], str[3] };
	return ret;
}

void layoutSignMessage(const uint8_t *msg, uint32_t len)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm",
		"Sign message?",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutVerifyMessage(const uint8_t *msg, uint32_t len)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(DIALOG_ICON_INFO, NULL, "OK",
		"Verified message",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutCipherKeyValue(bool encrypt, const char *key)
{
	const char **str = split_message((const uint8_t *)key, strlen(key), 16);
	layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm",
		encrypt ? "Encode value of this key?" : "Decode value of this key?",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutEncryptMessage(const uint8_t *msg, uint32_t len, bool signing)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(DIALOG_ICON_QUESTION, "Cancel", "Confirm",
		signing ? "Encrypt+Sign message?" : "Encrypt message?",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutDecryptMessage(const uint8_t *msg, uint32_t len, const char *address)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(DIALOG_ICON_INFO, NULL, "OK",
		address ? "Decrypted signed message" : "Decrypted message",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutAddress(const char *address)
{
	oledSwipeLeft();
	layoutLast = layoutAddress;

	static unsigned char bitdata[QR_MAX_BITDATA];
	int a, i, j;
	int side = qr_encode(QR_LEVEL_M, 0, address, 0, bitdata);

	if (side > 0 && side <= 29) {
		oledInvert(0, 0, (side + 2) * 2, (side + 2) * 2);
		//not 100% sure why this is transponed
		for (i = 0; i < side; i++) {
			for (j = 0; j< side; j++) {
				a = j * side + i;
				if (bitdata[a / 8] & (1 << (7 - a % 8))) {
					oledClearPixel(2 + i * 2, 2 + j * 2);
					oledClearPixel(3 + i * 2, 2 + j * 2);
					oledClearPixel(2 + i * 2, 3 + j * 2);
					oledClearPixel(3 + i * 2, 3 + j * 2);
				}
			}
		}
	}

	const char **str = split_message((const uint8_t *)address, strlen(address), 9);

	oledDrawString(68, 0 * 9, str[0]);
	oledDrawString(68, 1 * 9, str[1]);
	oledDrawString(68, 2 * 9, str[2]);
	oledDrawString(68, 3 * 9, str[3]);

	static const char *btnYes = "Continue";
	oledDrawString(OLED_WIDTH - fontCharWidth('}') - 1, OLED_HEIGHT - 8, "}");
	oledDrawString(OLED_WIDTH - fontStringWidth(btnYes) - fontCharWidth('}') - 3, OLED_HEIGHT - 8, btnYes);
	oledInvert(OLED_WIDTH - fontStringWidth(btnYes) - fontCharWidth('}') - 4, OLED_HEIGHT - 9, OLED_WIDTH - 1, OLED_HEIGHT - 1);

	oledRefresh();
}
