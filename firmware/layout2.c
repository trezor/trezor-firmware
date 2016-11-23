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
#include <ctype.h>

#include "layout2.h"
#include "storage.h"
#include "oled.h"
#include "bitmaps.h"
#include "string.h"
#include "util.h"
#include "qr_encode.h"
#include "timer.h"

void *layoutLast = layoutHome;

void layoutDialogSwipe(const BITMAP *icon, const char *btnNo, const char *btnYes, const char *desc, const char *line1, const char *line2, const char *line3, const char *line4, const char *line5, const char *line6)
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

void layoutScreensaver(void)
{
	layoutLast = layoutScreensaver;
	oledClear();
	oledRefresh();
}

void layoutHome(void)
{
	if (layoutLast == layoutHome || layoutLast == layoutScreensaver) {
		oledClear();
	} else {
		oledSwipeLeft();
	}
	layoutLast = layoutHome;
	const char *label = storage_isInitialized() ? storage_getLabel() : "Go to mytrezor.com";
	const uint8_t *homescreen = storage_getHomescreen();
	if (homescreen) {
		BITMAP b;
		b.width = 128;
		b.height = 64;
		b.data = homescreen;
		oledDrawBitmap(0, 0, &b);
	} else {
		if (label && strlen(label) > 0) {
			oledDrawBitmap(44, 4, &bmp_logo48);
			oledDrawStringCenter(OLED_HEIGHT - 8, label);
		} else {
			oledDrawBitmap(40, 0, &bmp_logo64);
		}
	}
	oledRefresh();

	// Reset lock screen timeout
	system_millis_lock_start = system_millis;
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
	layoutDialogSwipe(&bmp_icon_question,
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
	layoutDialogSwipe(&bmp_icon_question,
		"Cancel",
		"Confirm",
		NULL,
		"Really send",
		str_out,
		"from your wallet?",
		"Fee included:",
		str_fee,
		NULL
	);
}

void layoutFeeOverThreshold(const CoinType *coin, uint64_t fee, uint32_t kb)
{
	(void)kb;
	const char *str_out = str_amount(fee, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, buf_out, sizeof(buf_out));
	layoutDialogSwipe(&bmp_icon_question,
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
	layoutDialogSwipe(&bmp_icon_question, "Cancel", "Confirm",
		"Sign message?",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutVerifyAddress(const char *address)
{
	const char **str = split_message((const uint8_t *)address, strlen(address), 17);
	layoutDialogSwipe(&bmp_icon_info, "Cancel", "Confirm",
		"Confirm address?",
		"Message signed by:",
		NULL, str[0], str[1], str[2], NULL);
}

void layoutVerifyMessage(const uint8_t *msg, uint32_t len)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(&bmp_icon_info, "Cancel", "Confirm",
		"Verified message",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutCipherKeyValue(bool encrypt, const char *key)
{
	const char **str = split_message((const uint8_t *)key, strlen(key), 16);
	layoutDialogSwipe(&bmp_icon_question, "Cancel", "Confirm",
		encrypt ? "Encode value of this key?" : "Decode value of this key?",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutEncryptMessage(const uint8_t *msg, uint32_t len, bool signing)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(&bmp_icon_question, "Cancel", "Confirm",
		signing ? "Encrypt+Sign message?" : "Encrypt message?",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutDecryptMessage(const uint8_t *msg, uint32_t len, const char *address)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(&bmp_icon_info, NULL, "OK",
		address ? "Decrypted signed message" : "Decrypted message",
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutAddress(const char *address, const char *desc)
{
	oledSwipeLeft();
	layoutLast = layoutAddress;

	static unsigned char bitdata[QR_MAX_BITDATA];
	int a, i, j;
	int side = qr_encode(QR_LEVEL_M, 0, address, 0, bitdata);

	if (side > 0 && side <= 29) {
		oledInvert(0, 0, (side + 2) * 2, (side + 2) * 2);
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

	uint32_t addrlen = strlen(address);
	uint32_t rowlen = addrlen / 4;
	if (addrlen % 4) {
		rowlen++;
	}
	const char **str = split_message((const uint8_t *)address, addrlen, rowlen);

	if (desc) {
		oledDrawString(68, 0 * 9, desc);
	}
	oledDrawString(68, 1 * 9 + 4, str[0]);
	oledDrawString(68, 2 * 9 + 4, str[1]);
	oledDrawString(68, 3 * 9 + 4, str[2]);
	oledDrawString(68, 4 * 9 + 4, str[3]);

	static const char *btnYes = "Continue";
	oledDrawString(OLED_WIDTH - fontCharWidth('\x06') - 1, OLED_HEIGHT - 8, "\x06");
	oledDrawString(OLED_WIDTH - oledStringWidth(btnYes) - fontCharWidth('\x06') - 3, OLED_HEIGHT - 8, btnYes);
	oledInvert(OLED_WIDTH - oledStringWidth(btnYes) - fontCharWidth('\x06') - 4, OLED_HEIGHT - 9, OLED_WIDTH - 1, OLED_HEIGHT - 1);

	oledRefresh();
}

void layoutPublicKey(const uint8_t *pubkey)
{
	char hex[32*2+1], desc[16];
	strlcpy(desc, "Public Key: 00", sizeof(desc));
	data2hex(pubkey, 1, desc + 12);
	data2hex(pubkey + 1, 32, hex);
	const char **str = split_message((const uint8_t *)hex, 32*2, 16);
	layoutDialogSwipe(&bmp_icon_question, NULL, "Continue", NULL,
		desc, str[0], str[1], str[2], str[3], NULL);
}

void layoutSignIdentity(const IdentityType *identity, const char *challenge)
{
	char row_proto[8 + 11 + 1];
	char row_hostport[64 + 6 + 1];
	char row_user[64 + 8 + 1];

	if (identity->has_proto && identity->proto[0]) {
		if (strcmp(identity->proto, "https") == 0) {
			strlcpy(row_proto, "Web sign in to:", sizeof(row_proto));
		} else if (strcmp(identity->proto, "gpg") == 0) {
			strlcpy(row_proto, "GPG sign for:", sizeof(row_proto));
		} else {
			strlcpy(row_proto, identity->proto, sizeof(row_proto));
			char *p = row_proto;
			while (*p) { *p = toupper((int)*p); p++; }
			strlcat(row_proto, " login to:", sizeof(row_proto));
		}
	} else {
		strlcpy(row_proto, "Login to:", sizeof(row_proto));
	}

	if (identity->has_host && identity->host[0]) {
		strlcpy(row_hostport, identity->host, sizeof(row_hostport));
		if (identity->has_port && identity->port[0]) {
			strlcat(row_hostport, ":", sizeof(row_hostport));
			strlcat(row_hostport, identity->port, sizeof(row_hostport));
		}
	} else {
		row_hostport[0] = 0;
	}

	if (identity->has_user && identity->user[0]) {
		strlcpy(row_user, "user: ", sizeof(row_user));
		strlcat(row_user, identity->user, sizeof(row_user));
	} else {
		row_user[0] = 0;
	}

	layoutDialogSwipe(&bmp_icon_question, "Cancel", "Confirm",
		"Do you want to sign in?",
		row_proto[0] ? row_proto : NULL,
		row_hostport[0] ? row_hostport : NULL,
		row_user[0] ? row_user : NULL,
		challenge,
		NULL,
		NULL);
}

void layoutDecryptIdentity(const IdentityType *identity)
{
	char row_proto[8 + 11 + 1];
	char row_hostport[64 + 6 + 1];
	char row_user[64 + 8 + 1];

	if (identity->has_proto && identity->proto[0]) {
		strlcpy(row_proto, identity->proto, sizeof(row_proto));
		char *p = row_proto;
		while (*p) { *p = toupper((int)*p); p++; }
		strlcat(row_proto, " decrypt for:", sizeof(row_proto));
	} else {
		strlcpy(row_proto, "Decrypt for:", sizeof(row_proto));
	}

	if (identity->has_host && identity->host[0]) {
		strlcpy(row_hostport, identity->host, sizeof(row_hostport));
		if (identity->has_port && identity->port[0]) {
			strlcat(row_hostport, ":", sizeof(row_hostport));
			strlcat(row_hostport, identity->port, sizeof(row_hostport));
		}
	} else {
		row_hostport[0] = 0;
	}

	if (identity->has_user && identity->user[0]) {
		strlcpy(row_user, "user: ", sizeof(row_user));
		strlcat(row_user, identity->user, sizeof(row_user));
	} else {
		row_user[0] = 0;
	}

	layoutDialogSwipe(&bmp_icon_question, "Cancel", "Confirm",
		"Do you want to decrypt?",
		row_proto[0] ? row_proto : NULL,
		row_hostport[0] ? row_hostport : NULL,
		row_user[0] ? row_user : NULL,
		NULL,
		NULL,
		NULL);
}

void layoutU2FDialog(const char *verb, const char *appname, const BITMAP *appicon) {
	if (!appicon) {
		appicon = &bmp_icon_question;
	}
	layoutDialog(appicon, NULL, verb, NULL, verb, "U2F security key?", NULL, appname, NULL, NULL);
}
