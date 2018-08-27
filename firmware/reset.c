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

#include "reset.h"
#include "storage.h"
#include "rng.h"
#include "sha2.h"
#include "messages.h"
#include "fsm.h"
#include "layout2.h"
#include "protect.h"
#include "bip39.h"
#include "util.h"
#include "gettext.h"
#include "messages.pb.h"

static uint32_t strength;
static uint8_t  int_entropy[32];
static bool     awaiting_entropy = false;
static bool     skip_backup = false;

void reset_init(bool display_random, uint32_t _strength, bool passphrase_protection, bool pin_protection, const char *language, const char *label, uint32_t u2f_counter, bool _skip_backup)
{
	if (_strength != 128 && _strength != 192 && _strength != 256) return;

	strength = _strength;
	skip_backup = _skip_backup;

	random_buffer(int_entropy, 32);

	char ent_str[4][17];
	data2hex(int_entropy     , 8, ent_str[0]);
	data2hex(int_entropy +  8, 8, ent_str[1]);
	data2hex(int_entropy + 16, 8, ent_str[2]);
	data2hex(int_entropy + 24, 8, ent_str[3]);

	if (display_random) {
		layoutDialogSwipe(&bmp_icon_info, _("Cancel"), _("Continue"), NULL, _("Internal entropy:"), ent_str[0], ent_str[1], ent_str[2], ent_str[3], NULL);
		if (!protectButton(ButtonRequestType_ButtonRequest_ResetDevice, false)) {
			fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
			layoutHome();
			return;
		}
	}

	if (pin_protection && !protectChangePin()) {
		fsm_sendFailure(FailureType_Failure_PinMismatch, NULL);
		layoutHome();
		return;
	}

	storage_setPassphraseProtection(passphrase_protection);
	storage_setLanguage(language);
	storage_setLabel(label);
	storage_setU2FCounter(u2f_counter);
	storage_update();

	EntropyRequest resp;
	memset(&resp, 0, sizeof(EntropyRequest));
	msg_write(MessageType_MessageType_EntropyRequest, &resp);
	awaiting_entropy = true;
}

void reset_entropy(const uint8_t *ext_entropy, uint32_t len)
{
	if (!awaiting_entropy) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, _("Not in Reset mode"));
		return;
	}
	SHA256_CTX ctx;
	sha256_Init(&ctx);
	sha256_Update(&ctx, int_entropy, 32);
	sha256_Update(&ctx, ext_entropy, len);
	sha256_Final(&ctx, int_entropy);
	storage_setNeedsBackup(true);
	storage_setMnemonic(mnemonic_from_data(int_entropy, strength / 8));
	memset(int_entropy, 0, 32);
	awaiting_entropy = false;

	if (skip_backup) {
		storage_update();
		fsm_sendSuccess(_("Device successfully initialized"));
		layoutHome();
	} else {
		reset_backup(false);
	}

}

static char current_word[10];

// separated == true if called as a separate workflow via BackupMessage
void reset_backup(bool separated)
{
	if (!storage_needsBackup()) {
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, _("Seed already backed up"));
		return;
	}

	storage_setUnfinishedBackup(true);
	storage_setNeedsBackup(false);

	if (separated) {
		storage_update();
	}

	const char *mnemonic = storage_getMnemonic();

	for (int pass = 0; pass < 2; pass++) {
		int i = 0, word_pos = 1;
		while (mnemonic[i] != 0) {
			// copy current_word
			int j = 0;
			while (mnemonic[i] != ' ' && mnemonic[i] != 0 && j + 1 < (int)sizeof(current_word)) {
				current_word[j] = mnemonic[i];
				i++; j++;
			}
			current_word[j] = 0;
			if (mnemonic[i] != 0) {
				i++;
			}
			layoutResetWord(current_word, pass, word_pos, mnemonic[i] == 0);
			if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmWord, true)) {
				if (!separated) {
					storage_clear_update();
					session_clear(true);
				}
				layoutHome();
				fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
				return;
			}
			word_pos++;
		}
	}

	storage_setUnfinishedBackup(false);

	if (separated) {
		fsm_sendSuccess(_("Seed successfully backed up"));
	} else {
		storage_update();
		fsm_sendSuccess(_("Device successfully initialized"));
	}
	layoutHome();
}

#if DEBUG_LINK

uint32_t reset_get_int_entropy(uint8_t *entropy) {
	memcpy(entropy, int_entropy, 32);
	return 32;
}

const char *reset_get_word(void) {
	return current_word;
}

#endif
