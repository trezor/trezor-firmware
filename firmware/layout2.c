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
#include "secp256k1.h"
#include "nem2.h"
#include "gettext.h"

#define BITCOIN_DIVISIBILITY (8)

static const char *slip44_extras(uint32_t coin_type)
{
	if ((coin_type & 0x80000000) == 0) {
		return 0;
	}
	switch (coin_type & 0x7fffffff) {
		case    40: return "EXP";  // Expanse
		case    43: return "NEM";  // NEM
		case    60: return "ETH";  // Ethereum Mainnet
		case    61: return "ETC";  // Ethereum Classic Mainnet
		case   108: return "UBQ";  // UBIQ
		case   137: return "RSK";  // Rootstock Mainnet
		case 37310: return "tRSK"; // Rootstock Testnet
	}
	return 0;
}

#define BIP32_MAX_LAST_ELEMENT 1000000

static const char *address_n_str(const uint32_t *address_n, size_t address_n_count)
{
	if (address_n_count > 8) {
		return _("Unknown long path");
	}
	if (address_n_count == 0) {
		return _("Path: m");
	}

	// known BIP44/49 path
	static char path[100];
	if (address_n_count == 5 &&
		(address_n[0] == (0x80000000 + 44) || address_n[0] == (0x80000000 + 49) || address_n[0] == (0x80000000 + 84)) &&
		(address_n[1] & 0x80000000) &&
		(address_n[2] & 0x80000000) &&
		(address_n[3] <= 1) &&
		(address_n[4] <= BIP32_MAX_LAST_ELEMENT)) {
			bool native_segwit = (address_n[0] == (0x80000000 + 84));
			bool p2sh_segwit = (address_n[0] == (0x80000000 + 49));
			bool legacy = false;
			const CoinInfo *coin = coinBySlip44(address_n[1]);
			const char *abbr = 0;
			if (native_segwit) {
				if (coin && coin->has_segwit && coin->bech32_prefix) {
					abbr = coin->coin_shortcut + 1;
				}
			} else
			if (p2sh_segwit) {
				if (coin && coin->has_segwit && coin->has_address_type_p2sh) {
					abbr = coin->coin_shortcut + 1;
				}
			} else {
				if (coin) {
					if (coin->has_segwit && coin->has_address_type_p2sh) {
						legacy = true;
					}
					abbr = coin->coin_shortcut + 1;
				} else {
					abbr = slip44_extras(address_n[1]);
				}
			}
			uint32_t accnum = (address_n[2] & 0x7fffffff) + 1;
			if (abbr && accnum < 100) {
				memset(path, 0, sizeof(path));
				strlcpy(path, abbr, sizeof(path));
				// TODO: how to name accounts?
				// currently we have "legacy account", "account" and "segwit account"
				// for BIP44/P2PKH, BIP49/P2SH-P2WPKH and BIP84/P2WPKH respectivelly
				if (legacy) {
					strlcat(path, " legacy", sizeof(path));
				}
				if (native_segwit) {
					strlcat(path, " segwit", sizeof(path));
				}
				strlcat(path, " account #", sizeof(path));
				char acc[3];
				memset(acc, 0, sizeof(acc));
				if (accnum < 10) {
					acc[0] = '0' + accnum;
				} else {
					acc[0] = '0' + (accnum / 10);
					acc[1] = '0' + (accnum % 10);
				}
				strlcat(path, acc, sizeof(path));
				return path;
			}
	}

	//                  "Path: m"    /   i   '
	static char address_str[7 + 8 * (1 + 9 + 1) + 1];
	char *c = address_str + sizeof(address_str) - 1;

	*c = 0; c--;

	for (int n = (int)address_n_count - 1; n >= 0; n--) {
		uint32_t i = address_n[n];
		if (i & 0x80000000) {
			*c = '\''; c--;
		}
		i = i & 0x7fffffff;
		do {
			*c = '0' + (i % 10); c--;
			i /= 10;
		} while (i > 0);
		*c = '/'; c--;
	}
	*c = 'm'; c--;
	*c = ' '; c--;
	*c = ':'; c--;
	*c = 'h'; c--;
	*c = 't'; c--;
	*c = 'a'; c--;
	*c = 'P';

	return c;
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
	if (len > rowlen * 4) {
		str[3][rowlen - 1] = '.';
		str[3][rowlen - 2] = '.';
		str[3][rowlen - 3] = '.';
	}
	static const char *ret[4] = { str[0], str[1], str[2], str[3] };
	return ret;
}

void *layoutLast = layoutHome;

void layoutDialogSwipe(const BITMAP *icon, const char *btnNo, const char *btnYes, const char *desc, const char *line1, const char *line2, const char *line3, const char *line4, const char *line5, const char *line6)
{
	layoutLast = layoutDialogSwipe;
	layoutSwipe();
	layoutDialog(icon, btnNo, btnYes, desc, line1, line2, line3, line4, line5, line6);
}

void layoutProgressSwipe(const char *desc, int permil)
{
	if (layoutLast == layoutProgressSwipe) {
		oledClear();
	} else {
		layoutLast = layoutProgressSwipe;
		layoutSwipe();
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
		layoutSwipe();
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
			oledDrawStringCenter(OLED_HEIGHT - 8, label, FONT_STANDARD);
		} else {
			oledDrawBitmap(40, 0, &bmp_logo64);
		}
	}
	if (storage_unfinishedBackup()) {
		oledBox(0, 0, 127, 8, false);
		oledDrawStringCenter(0, "BACKUP FAILED!", FONT_STANDARD);
	} else
	if (storage_needsBackup()) {
		oledBox(0, 0, 127, 8, false);
		oledDrawStringCenter(0, "NEEDS BACKUP!", FONT_STANDARD);
	}
	oledRefresh();

	// Reset lock screen timeout
	system_millis_lock_start = timer_ms();
}

void layoutConfirmOutput(const CoinInfo *coin, const TxOutputType *out)
{
	char str_out[32 + 3];
	bn_format_uint64(out->amount, NULL, coin->coin_shortcut, BITCOIN_DIVISIBILITY, 0, false, str_out, sizeof(str_out) - 3);
	strlcat(str_out, " to", sizeof(str_out));
	const char *addr = out->address;
	if (coin->cashaddr_prefix) {
		/* If this is a cashaddr address, remove the prefix from the
		 * string presented to the user
		 */
		int prefix_len = strlen(coin->cashaddr_prefix);
		if (strncmp(addr, coin->cashaddr_prefix, prefix_len) == 0
			&& addr[prefix_len] == ':') {
			addr += prefix_len + 1;
		}
	}
	int addrlen = strlen(addr);
	int numlines = addrlen <= 42 ? 2 : 3;
	int linelen = (addrlen - 1) / numlines + 1;
	if (linelen > 21) {
		linelen = 21;
	}
	const char **str = split_message((const uint8_t *)addr, addrlen, linelen);
	layoutLast = layoutDialogSwipe;
	layoutSwipe();
	oledClear();
	oledDrawBitmap(0, 0, &bmp_icon_question);
	oledDrawString(20, 0 * 9, _("Confirm sending"), FONT_STANDARD);
	oledDrawString(20, 1 * 9, str_out, FONT_STANDARD);
	int left = linelen > 18 ? 0 : 20;
	oledDrawString(left, 2 * 9, str[0], FONT_FIXED);
	oledDrawString(left, 3 * 9, str[1], FONT_FIXED);
	oledDrawString(left, 4 * 9, str[2], FONT_FIXED);
	oledDrawString(left, 5 * 9, str[3], FONT_FIXED);
	if (!str[3][0]) {
		if (out->address_n_count > 0) {
			oledDrawString(0, 5*9, address_n_str(out->address_n, out->address_n_count), FONT_STANDARD);
		} else {
			oledHLine(OLED_HEIGHT - 13);
		}
	}
	layoutButtonNo(_("Cancel"));
	layoutButtonYes(_("Confirm"));
	oledRefresh();
}

void layoutConfirmOpReturn(const uint8_t *data, uint32_t size)
{
	bool ascii_only = true;
	for (uint32_t i = 0; i < size; i++) {
		if (data[i] < ' ' || data[i] > '~') {
			ascii_only = false;
			break;
		}
	}
	const char **str;
	if (!ascii_only) {
		char hex[65];
		memset(hex, 0, sizeof(hex));
		data2hex(data, (size > 32) ? 32 : size, hex);
		str = split_message((const uint8_t *)hex, size * 2, 16);
	} else {
		str = split_message(data, size, 20);
	}
	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Confirm"),
		NULL,
		_("Confirm OP_RETURN:"),
		str[0],
		str[1],
		str[2],
		str[3],
		NULL
	);
}

void layoutConfirmTx(const CoinInfo *coin, uint64_t amount_out, uint64_t amount_fee)
{
	char str_out[32], str_fee[32];
	bn_format_uint64(amount_out, NULL, coin->coin_shortcut, BITCOIN_DIVISIBILITY, 0, false, str_out, sizeof(str_out));
	bn_format_uint64(amount_fee, NULL, coin->coin_shortcut, BITCOIN_DIVISIBILITY, 0, false, str_fee, sizeof(str_fee));
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

void layoutFeeOverThreshold(const CoinInfo *coin, uint64_t fee)
{
	char str_fee[32];
	bn_format_uint64(fee, NULL, coin->coin_shortcut, BITCOIN_DIVISIBILITY, 0, false, str_fee, sizeof(str_fee));
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
		encrypt ? _("Encrypt value of this key?") : _("Decrypt value of this key?"),
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

void layoutResetWord(const char *word, int pass, int word_pos, bool last)
{
	layoutLast = layoutResetWord;
	layoutSwipe();

	const char *btnYes;
	if (last) {
		if (pass == 1) {
			btnYes = _("Finish");
		} else {
			btnYes = _("Again");
		}
	} else {
		btnYes = _("Next");
	}

	const char *action;
	if (pass == 1) {
		action = _("Please check the seed");
	} else {
		action = _("Write down the seed");
	}

	char index_str[] = "##th word is:";
	if (word_pos < 10) {
		index_str[0] = ' ';
	} else {
		index_str[0] = '0' + word_pos / 10;
	}
	index_str[1] = '0' + word_pos % 10;
	if (word_pos == 1 || word_pos == 21) {
		index_str[2] = 's'; index_str[3] = 't';
	} else
	if (word_pos == 2 || word_pos == 22) {
		index_str[2] = 'n'; index_str[3] = 'd';
	} else
	if (word_pos == 3 || word_pos == 23) {
		index_str[2] = 'r'; index_str[3] = 'd';
	}

	int left = 0;
	oledClear();
	oledDrawBitmap(0, 0, &bmp_icon_info);
	left = bmp_icon_info.width + 4;

	oledDrawString(left, 0 * 9, action, FONT_STANDARD);
	oledDrawString(left, 2 * 9, word_pos < 10 ? index_str + 1 : index_str, FONT_STANDARD);
	oledDrawString(left, 3 * 9, word, FONT_STANDARD | FONT_DOUBLE);
	oledHLine(OLED_HEIGHT - 13);
	layoutButtonYes(btnYes);
	oledRefresh();
}

void layoutAddress(const char *address, const char *desc, bool qrcode, bool ignorecase, const uint32_t *address_n, size_t address_n_count)
{
	if (layoutLast != layoutAddress) {
		layoutSwipe();
	} else {
		oledClear();
	}
	layoutLast = layoutAddress;

	uint32_t addrlen = strlen(address);
	if (qrcode) {
		static unsigned char bitdata[QR_MAX_BITDATA];
		char address_upcase[addrlen + 1];
		if (ignorecase) {
			for (uint32_t i = 0; i < addrlen + 1; i++) {
				address_upcase[i] = address[i] >= 'a' && address[i] <= 'z' ?
					address[i] + 'A' - 'a' : address[i];
			}
		}
		int side = qr_encode(addrlen <= (ignorecase ? 60 : 40) ? QR_LEVEL_M : QR_LEVEL_L, 0,
							 ignorecase ? address_upcase : address, 0, bitdata);

		oledInvert(0, 0, 63, 63);
		if (side > 0 && side <= 29) {
			int offset = 32 - side;
			for (int i = 0; i < side; i++) {
				for (int j = 0; j< side; j++) {
					int a = j * side + i;
					if (bitdata[a / 8] & (1 << (7 - a % 8))) {
						oledBox(offset + i * 2, offset + j * 2,
								offset + 1 + i * 2, offset + 1 + j * 2, false);
					}
				}
			}
		} else if (side > 0 && side <= 60) {
			int offset = 32 - (side / 2); 
			for (int i = 0; i < side; i++) {
				for (int j = 0; j< side; j++) {
					int a = j * side + i;
					if (bitdata[a / 8] & (1 << (7 - a % 8))) {
						oledClearPixel(offset + i, offset + j);
					}
				}
			}
		}
	} else {
		uint32_t rowlen = (addrlen - 1) / (addrlen <= 42 ? 2 : addrlen <= 63 ? 3 : 4) + 1;
		const char **str = split_message((const uint8_t *)address, addrlen, rowlen);
		if (desc) {
			oledDrawString(0, 0 * 9, desc, FONT_STANDARD);
		}
		for (int i = 0; i < 4; i++) {
			oledDrawString(0, (i + 1) * 9 + 4, str[i], FONT_FIXED);
		}
		oledDrawString(0, 42, address_n_str(address_n, address_n_count), FONT_STANDARD);
	}

	if (!qrcode) {
		layoutButtonNo(_("QR Code"));
	}

	layoutButtonYes(_("Continue"));
	oledRefresh();
}

void layoutPublicKey(const uint8_t *pubkey)
{
	char hex[32 * 2 + 1], desc[16];
	strlcpy(desc, "Public Key: 00", sizeof(desc));
	if (pubkey[0] == 1) {
		/* ed25519 public key */
		// pass - leave 00
	} else {
		data2hex(pubkey, 1, desc + 12);
	}
	data2hex(pubkey + 1, 32, hex);
	const char **str = split_message((const uint8_t *)hex, 32 * 2, 16);
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

void layoutNEMDialog(const BITMAP *icon, const char *btnNo, const char *btnYes, const char *desc, const char *line1, const char *address) {
	static char first_third[NEM_ADDRESS_SIZE / 3 + 1];
	strlcpy(first_third, address, sizeof(first_third));

	static char second_third[NEM_ADDRESS_SIZE / 3 + 1];
	strlcpy(second_third, &address[NEM_ADDRESS_SIZE / 3], sizeof(second_third));

	const char *third_third = &address[NEM_ADDRESS_SIZE * 2 / 3];

	layoutDialogSwipe(icon,
		btnNo,
		btnYes,
		desc,
		line1,
		first_third,
		second_third,
		third_third,
		NULL,
		NULL);
}

void layoutNEMTransferXEM(const char *desc, uint64_t quantity, const bignum256 *multiplier, uint64_t fee) {
	char str_out[32], str_fee[32];

	nem_mosaicFormatAmount(NEM_MOSAIC_DEFINITION_XEM, quantity, multiplier, str_out, sizeof(str_out));
	nem_mosaicFormatAmount(NEM_MOSAIC_DEFINITION_XEM, fee, NULL, str_fee, sizeof(str_fee));

	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Next"),
		desc,
		_("Confirm transfer of"),
		str_out,
		_("and network fee of"),
		str_fee,
		NULL,
		NULL);
}

void layoutNEMNetworkFee(const char *desc, bool confirm, const char *fee1_desc, uint64_t fee1, const char *fee2_desc, uint64_t fee2) {
	char str_fee1[32], str_fee2[32];

	nem_mosaicFormatAmount(NEM_MOSAIC_DEFINITION_XEM, fee1, NULL, str_fee1, sizeof(str_fee1));

	if (fee2_desc) {
		nem_mosaicFormatAmount(NEM_MOSAIC_DEFINITION_XEM, fee2, NULL, str_fee2, sizeof(str_fee2));
	}

	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		confirm ? _("Confirm") : _("Next"),
		desc,
		fee1_desc,
		str_fee1,
		fee2_desc,
		fee2_desc ? str_fee2 : NULL,
		NULL,
		NULL);
}

void layoutNEMTransferMosaic(const NEMMosaicDefinition *definition, uint64_t quantity, const bignum256 *multiplier, uint8_t network) {
	char str_out[32], str_levy[32];

	nem_mosaicFormatAmount(definition, quantity, multiplier, str_out, sizeof(str_out));

	if (definition->has_levy) {
		nem_mosaicFormatLevy(definition, quantity, multiplier, network, str_levy, sizeof(str_levy));
	}

	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("Next"),
		definition->has_name ? definition->name : _("Mosaic"),
		_("Confirm transfer of"),
		str_out,
		definition->has_levy ? _("and levy of") : NULL,
		definition->has_levy ? str_levy : NULL,
		NULL,
		NULL);
}

void layoutNEMTransferUnknownMosaic(const char *namespace, const char *mosaic, uint64_t quantity, const bignum256 *multiplier) {
	char mosaic_name[32];
	nem_mosaicFormatName(namespace, mosaic, mosaic_name, sizeof(mosaic_name));

	char str_out[32];
	nem_mosaicFormatAmount(NULL, quantity, multiplier, str_out, sizeof(str_out));

	char *decimal = strchr(str_out, '.');
	if (decimal != NULL) {
		*decimal = '\0';
	}

	layoutDialogSwipe(&bmp_icon_question,
		_("Cancel"),
		_("I take the risk"),
		_("Unknown Mosaic"),
		_("Confirm transfer of"),
		str_out,
		_("raw units of"),
		mosaic_name,
		NULL,
		NULL);
}

void layoutNEMTransferPayload(const uint8_t *payload, size_t length, bool encrypted) {
	if (length >= 1 && payload[0] == 0xFE) {
		char encoded[(length - 1) * 2 + 1];
		data2hex(&payload[1], length - 1, encoded);

		const char **str = split_message((uint8_t *) encoded, sizeof(encoded) - 1, 16);
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Next"),
			encrypted ? _("Encrypted hex data") : _("Unencrypted hex data"),
			str[0], str[1], str[2], str[3], NULL, NULL);
	} else {
		const char **str = split_message(payload, length, 16);
		layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Next"),
			encrypted ? _("Encrypted message") : _("Unencrypted message"),
			str[0], str[1], str[2], str[3], NULL, NULL);
	}
}

void layoutNEMMosaicDescription(const char *description) {
	const char **str = split_message((uint8_t *) description, strlen(description), 16);
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Next"),
		_("Mosaic Description"),
		str[0], str[1], str[2], str[3], NULL, NULL);
}

void layoutNEMLevy(const NEMMosaicDefinition *definition, uint8_t network) {
	const NEMMosaicDefinition *mosaic;
	if (nem_mosaicMatches(definition, definition->levy_namespace, definition->levy_mosaic, network)) {
		mosaic = definition;
	} else {
		mosaic = nem_mosaicByName(definition->levy_namespace, definition->levy_mosaic, network);
	}

	char mosaic_name[32];
	if (mosaic == NULL) {
		nem_mosaicFormatName(definition->levy_namespace, definition->levy_mosaic, mosaic_name, sizeof(mosaic_name));
	}

	char str_out[32];

	switch (definition->levy) {
	case NEMMosaicLevy_MosaicLevy_Percentile:
		bn_format_uint64(definition->fee, NULL, NULL, 0, 0, false, str_out, sizeof(str_out));

		layoutDialogSwipe(&bmp_icon_question,
			_("Cancel"),
			_("Next"),
			_("Percentile Levy"),
			_("Raw levy value is"),
			str_out,
			_("in"),
			mosaic ? (mosaic == definition ? _("the same mosaic") : mosaic->name) : mosaic_name,
			NULL,
			NULL);
		break;

	case NEMMosaicLevy_MosaicLevy_Absolute:
	default:
		nem_mosaicFormatAmount(mosaic, definition->fee, NULL, str_out, sizeof(str_out));
		layoutDialogSwipe(&bmp_icon_question,
			_("Cancel"),
			_("Next"),
			_("Absolute Levy"),
			_("Levy is"),
			str_out,
			mosaic ? (mosaic == definition ? _("in the same mosaic") : NULL) : _("in raw units of"),
			mosaic ? NULL : mosaic_name,
			NULL,
			NULL);
		break;
	}
}

static inline bool is_slip18(const uint32_t *address_n, size_t address_n_count)
{
	return address_n_count == 2 && address_n[0] == (0x80000000 + 10018) && (address_n[1] & 0x80000000) && (address_n[1] & 0x7FFFFFFF) <= 9;
}

void layoutCosiCommitSign(const uint32_t *address_n, size_t address_n_count, const uint8_t *data, uint32_t len, bool final_sign)
{
	char *desc = final_sign ? _("CoSi sign message?") : _("CoSi commit message?");
	char desc_buf[32];
	if (is_slip18(address_n, address_n_count)) {
		if (final_sign) {
			strlcpy(desc_buf, _("CoSi sign index #?"), sizeof(desc_buf));
			desc_buf[16] = '0' + (address_n[1] & 0x7FFFFFFF);
		} else {
			strlcpy(desc_buf, _("CoSi commit index #?"), sizeof(desc_buf));
			desc_buf[18] = '0' + (address_n[1] & 0x7FFFFFFF);
		}
		desc = desc_buf;
	}
	char str[4][17];
	if (len == 32) {
		data2hex(data     , 8, str[0]);
		data2hex(data +  8, 8, str[1]);
		data2hex(data + 16, 8, str[2]);
		data2hex(data + 24, 8, str[3]);
	} else {
		strlcpy(str[0], "Data", sizeof(str[0]));
		strlcpy(str[1], "of", sizeof(str[1]));
		strlcpy(str[2], "unsupported", sizeof(str[2]));
		strlcpy(str[3], "length", sizeof(str[3]));
	}
	layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), desc,
		str[0], str[1], str[2], str[3], NULL, NULL);
}
