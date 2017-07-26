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
#include "bignum.h"
#include "gettext.h"

#define BITCOIN_DIVISIBILITY (8)

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
	const char *label = storage_isInitialized() ? storage_getLabel() : _("Go to trezor.io/start");
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
	if (storage_needsBackup()) {
		oledBox(0, 0, 127, 8, false);
		oledDrawStringCenter(0, "NEEDS BACKUP!");
	}
	oledRefresh();

	// Reset lock screen timeout
	system_millis_lock_start = system_millis;
}

void layoutConfirmOutput(const CoinType *coin, const TxOutputType *out)
{
	char str_out[32];
	bn_format_uint64(out->amount, NULL, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, BITCOIN_DIVISIBILITY, 0, false, str_out, sizeof(str_out));
	static char first_half[17 + 1];
	strlcpy(first_half, out->address, sizeof(first_half));
	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Confirm"),
		NULL,
		_("Confirm sending"),
		str_out,
		_("to"),
		first_half,
		out->address + 17,
		NULL
	);
}

void layoutConfirmTx(const CoinType *coin, uint64_t amount_out, uint64_t amount_fee)
{
	char str_out[32], str_fee[32];
	bn_format_uint64(amount_out, NULL, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, BITCOIN_DIVISIBILITY, 0, false, str_out, sizeof(str_out));
	bn_format_uint64(amount_fee, NULL, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, BITCOIN_DIVISIBILITY, 0, false, str_fee, sizeof(str_fee));
	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Confirm"),
		NULL,
		_("Really send"),
		str_out,
		_("from your wallet?"),
		_("Fee included:"),
		str_fee,
		NULL
	);
}

void layoutFeeOverThreshold(const CoinType *coin, uint64_t fee)
{
	char str_fee[32];
	bn_format_uint64(fee, NULL, coin->has_coin_shortcut ? coin->coin_shortcut : NULL, BITCOIN_DIVISIBILITY, 0, false, str_fee, sizeof(str_fee));
	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Confirm"),
		NULL,
		_("Fee"),
		str_fee,
		_("is unexpectedly high."),
		NULL,
		_("Send anyway?"),
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
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		_("Sign message?"),
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutVerifyAddress(const char *address)
{
	const char **str = split_message((const uint8_t *)address, strlen(address), 17);
	layoutDialogSwipe(&bmp_icon_info, _("Cancel"), _("Confirm"),
		_("Confirm address?"),
		_("Message signed by:"),
		str[0], str[1], str[2], NULL, NULL);
}

void layoutVerifyMessage(const uint8_t *msg, uint32_t len)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(&bmp_icon_info, _("Cancel"), _("Confirm"),
		_("Verified message"),
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutCipherKeyValue(bool encrypt, const char *key)
{
	const char **str = split_message((const uint8_t *)key, strlen(key), 16);
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		encrypt ? _("Encode value of this key?") : _("Decode value of this key?"),
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutEncryptMessage(const uint8_t *msg, uint32_t len, bool signing)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		signing ? _("Encrypt+Sign message?") : _("Encrypt message?"),
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutDecryptMessage(const uint8_t *msg, uint32_t len, const char *address)
{
	const char **str = split_message(msg, len, 16);
	layoutDialogSwipe(&bmp_icon_info, NULL, _("OK"),
		address ? _("Decrypted signed message") : _("Decrypted message"),
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutAddress(const char *address, const char *desc, bool qrcode)
{
	if (layoutLast != layoutAddress) {
		oledSwipeLeft();
	} else {
		oledClear();
	}
	layoutLast = layoutAddress;

	if (qrcode) {
		static unsigned char bitdata[QR_MAX_BITDATA];
		int side = qr_encode(QR_LEVEL_M, 0, address, 0, bitdata);

		if (side > 0 && side <= 29) {
			oledInvert(0, 0, (side + 2) * 2, (side + 2) * 2);
			for (int i = 0; i < side; i++) {
				for (int j = 0; j< side; j++) {
					int a = j * side + i;
					if (bitdata[a / 8] & (1 << (7 - a % 8))) {
						oledClearPixel(2 + i * 2, 2 + j * 2);
						oledClearPixel(3 + i * 2, 2 + j * 2);
						oledClearPixel(2 + i * 2, 3 + j * 2);
						oledClearPixel(3 + i * 2, 3 + j * 2);
					}
				}
			}
		} else if (side > 0 && side <= 60) {
			oledInvert(0, 0, (side + 3), (side + 3));
			for (int i = 0; i < side; i++) {
				for (int j = 0; j< side; j++) {
					int a = j * side + i;
					if (bitdata[a / 8] & (1 << (7 - a % 8))) {
						oledClearPixel(2 + i, 2 + j);
					}
				}
			}
		}
	} else {
		uint32_t addrlen = strlen(address);
		uint32_t rowlen = addrlen / 2;
		if (addrlen % 2) {
			rowlen++;
		}
		const char **str = split_message((const uint8_t *)address, addrlen, rowlen);
		if (desc) {
			oledDrawString(0, 0 * 9, desc);
		}
		for (int i = 0; i < 4; i++) {
			oledDrawString(0, (i + 1) * 9 + 4, str[i]);
		}
	}

	if (!qrcode) {
		static const char *btnNo = _("QR Code");
		oledDrawString(2, OLED_HEIGHT - 8, btnNo);
		oledInvert(0, OLED_HEIGHT - 9, oledStringWidth(btnNo) + 3, OLED_HEIGHT - 1);
	}

	static const char *btnYes = _("Continue");
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
	layoutDialogSwipe(&bmp_icon_question, NULL, _("Continue"), NULL,
		desc, str[0], str[1], str[2], str[3], NULL);
}

void layoutSignIdentity(const IdentityType *identity, const char *challenge)
{
	char row_proto[8 + 11 + 1];
	char row_hostport[64 + 6 + 1];
	char row_user[64 + 8 + 1];

	bool is_gpg = (strcmp(identity->proto, "gpg") == 0);

	if (identity->has_proto && identity->proto[0]) {
		if (strcmp(identity->proto, "https") == 0) {
			strlcpy(row_proto, _("Web sign in to:"), sizeof(row_proto));
		} else if (is_gpg) {
			strlcpy(row_proto, _("GPG sign for:"), sizeof(row_proto));
		} else {
			strlcpy(row_proto, identity->proto, sizeof(row_proto));
			char *p = row_proto;
			while (*p) { *p = toupper((int)*p); p++; }
			strlcat(row_proto, _(" login to:"), sizeof(row_proto));
		}
	} else {
		strlcpy(row_proto, _("Login to:"), sizeof(row_proto));
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
		strlcpy(row_user, _("user: "), sizeof(row_user));
		strlcat(row_user, identity->user, sizeof(row_user));
	} else {
		row_user[0] = 0;
	}

	if (is_gpg) {
		// Split "First Last <first@last.com>" into 2 lines:
		// "First Last"
		// "first@last.com"
		char *email_start = strchr(row_hostport, '<');
		if (email_start) {
			strlcpy(row_user, email_start + 1, sizeof(row_user));
			*email_start = 0;
			char *email_end = strchr(row_user, '>');
			if (email_end) {
				*email_end = 0;
			}
		}
	}

	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		_("Do you want to sign in?"),
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
		strlcat(row_proto, _(" decrypt for:"), sizeof(row_proto));
	} else {
		strlcpy(row_proto, _("Decrypt for:"), sizeof(row_proto));
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
		strlcpy(row_user, _("user: "), sizeof(row_user));
		strlcat(row_user, identity->user, sizeof(row_user));
	} else {
		row_user[0] = 0;
	}

	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"),
		_("Do you want to decrypt?"),
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
	layoutDialog(appicon, NULL, verb, NULL, verb, _("U2F security key?"), NULL, appname, NULL, NULL);
}
