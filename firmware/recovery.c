/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 * Copyright (C) 2016 Jochen Hoenicke <hoenicke@gmail.com>
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

#include <ctype.h>
#include "recovery.h"
#include "fsm.h"
#include "storage.h"
#include "layout2.h"
#include "protect.h"
#include "types.pb.h"
#include "messages.h"
#include "rng.h"
#include "bip39.h"
#include "oled.h"
#include "usb.h"
#include "types.pb.h"
#include "recovery-table.h"

/* number of words expected in the new seed */
static uint32_t word_count;

/* recovery mode:
 * 0: not recovering
 * 1: recover by scrambled plain text words
 * 2: recover by matrix entry
 */
static int awaiting_word = 0;

/* True if we should check that seed corresponds to bip39.
 */
static bool enforce_wordlist;

/* For scrambled recovery Trezor may ask for faked words if
 * seed is short.  This contains the fake word.
 */
static char fake_word[12];

/* Word position in the seed that we are currently asking for.
 * This is 0 if we ask for a fake word.  Only for scrambled recovery.
 */
static uint32_t word_pos;

/* Scrambled recovery:  How many words has the user already entered.
 * Matrix recovery: How many digits has the user already entered.
 */
static uint32_t word_index;

/* Order in which we ask for the words.  It holds that
 * word_order[word_index] == word_pos.  Only for scrambled recovery.
 */
static char word_order[24];

/* The recovered seed.  This is filled during the recovery process.
 */
static char words[24][12];

/* The "pincode" of the current word.  This is basically the "pin"
 * that the user would have entered for the current word if the words
 * were displayed in alphabetical order.  Note that it is base 9, not
 * base 10.  Only for matrix recovery.
 */
static uint16_t word_pincode;

/* The pinmatrix currently displayed on screen.
 * Only for matrix recovery.
 */
static uint8_t word_matrix[9];

#define MASK_IDX(x) ((x) & 0xfff)
#define TABLE1(x) MASK_IDX(word_table1[x])
#define TABLE2(x) MASK_IDX(word_table2[x])

/* Helper function to format a two digit number.
 * Parameter dest is buffer containing the string. It should already
 * start with "##th".  The number is written in place.
 * Parameter number gives the number that we should format.
 */
static void format_number(char *dest, int number) {
	if (number < 10) {
		dest[0] = ' ';
	} else {
		dest[0] = '0' + number / 10;
	}
	dest[1] = '0' + number % 10;
	if (number == 1 || number == 21) {
		dest[2] = 's'; dest[3] = 't';
	} else if (number == 2 || number == 22) {
		dest[2] = 'n'; dest[3] = 'd';
	} else if (number == 3 || number == 23) {
		dest[2] = 'r'; dest[3] = 'd';
	}
}

/* Send a request for a new word/matrix code to the PC.
 */
static void recovery_request(void) {
	WordRequest resp;
	memset(&resp, 0, sizeof(WordRequest));
	resp.has_type = true;
	resp.type = awaiting_word == 1 ? WordRequestType_WordRequestType_Plain
		: (word_index % 4 == 3) ? WordRequestType_WordRequestType_Matrix6
		: WordRequestType_WordRequestType_Matrix9;
	msg_write(MessageType_MessageType_WordRequest, &resp);
}

/* Called when the last word was entered.
 * Check mnemonic and send success/failure.
 */
static void recovery_done(void) {
	uint32_t i;
	strlcpy(storage.mnemonic, words[0], sizeof(storage.mnemonic));
	for (i = 1; i < word_count; i++) {
		strlcat(storage.mnemonic, " ", sizeof(storage.mnemonic));
		strlcat(storage.mnemonic, words[i], sizeof(storage.mnemonic));
	}
	if (!enforce_wordlist || mnemonic_check(storage.mnemonic)) {
		storage.has_mnemonic = true;
		if (!enforce_wordlist) {
			// not enforcing => mark storage as imported
			storage.has_imported = true;
			storage.imported = true;
		}
		storage_commit();
		fsm_sendSuccess("Device recovered");
	} else {
		storage_reset();
		fsm_sendFailure(FailureType_Failure_SyntaxError, "Invalid mnemonic, are words in correct order?");
	}
	awaiting_word = 0;
	layoutHome();
}

/* Helper function for matrix recovery:
 * Formats a string describing the word range from first to last where
 * prefixlen gives the number of characters in first and last that are
 * significant, i.e. the word before first or the word after last differ
 * exactly at the prefixlen-th character.
 *
 * Invariants:
 *  memcmp("first - 1", first, prefixlen) != 0
 *  memcmp(last, "last + 1", prefixlen) != 0
 *  first[prefixlen-2] == last[prefixlen-2]  except for range WI-Z.
 */
static void add_choice(char choice[12], int prefixlen, const char *first, const char *last) {
	// assert prefixlen < 4
	int i;
	char *dest = choice;
	for (i = 0; i < prefixlen; i++) {
		*dest++ = toupper((int) first[i]);
	}
	if (first[0] != last[0]) {
		/* special case WI-Z; also used for T-Z, etc. */
		*dest++ = '-';
		*dest++ = toupper((int) last[0]);
	} else if (last[prefixlen-1] == first[prefixlen-1]) {
		/* single prefix */
	} else if (prefixlen < 3) {
		/* AB-AC, etc. */
		*dest++ = '-';
		for (i = 0; i < prefixlen; i++) {
			*dest++ = toupper((int) last[i]);
		}
	} else {
		/* RE[A-M] etc. */
		/* remove last and replace with space */
		dest[-1] = ' ';
		if (first[prefixlen - 1]) {
			/* handle special case: CAN[-D] */
			*dest++ = toupper((int)first[prefixlen - 1]);
		}
		*dest++ = '-';
		*dest++ = toupper((int) last[prefixlen - 1]);
	}
	*dest++ = 0;
}

/* Helper function for matrix recovery:
 * Display the recovery matrix given in choices.  If twoColumn is set
 * use 2x3 layout, otherwise 3x3 layout.  Also generates a random
 * scrambling and stores it in word_matrix.
 */
static void display_choices(bool twoColumn, char choices[9][12], int num)
{
	int i;
	int nColumns = twoColumn ? 2 : 3;
	int displayedChoices = nColumns * 3;
	int row, col;
	for (i = 0; i < displayedChoices; i++) {
		word_matrix[i] = i;
	}
	/* scramble matrix */
	random_permute((char*)word_matrix, displayedChoices);

	if (word_index % 4 == 0) {
		char desc[] = "##th word";
		int nr = (word_index / 4) + 1;
		format_number(desc, nr);
		layoutDialogSwipe(&bmp_icon_info, NULL, NULL, NULL, "Please enter the", (nr < 10 ? desc + 1 : desc), "of your mnemonic", NULL, NULL, NULL);
	} else {
		oledBox(0, 18, 127, 63, false);
	}

	for (row = 0; row < 3; row ++) {
		int y = 55 - row * 11;
		for (col = 0; col < nColumns; col++) {
			int x = twoColumn ? 64 * col + 32 : 42 * col + 22;
			int choice = word_matrix[nColumns*row + col];
			const char *text = choice < num ? choices[choice] : "-";
			oledDrawString(x - oledStringWidth(text)/2, y, text);
		}
	}
	oledRefresh();

	/* avoid picking out of range numbers */
	for (i = 0; i < displayedChoices; i++) {
		if (word_matrix[i] > num)
			word_matrix[i] = 0;
	}
	/* two column layout: middle column = right column */
	if (twoColumn) {
		static const uint8_t twolayout[9] = { 0, 1, 1, 2, 3, 3, 4, 5, 5 };
		for (i = 8; i >= 2; i--) {
			word_matrix[i] = word_matrix[twolayout[i]];
		}
	}
}

/* Helper function for matrix recovery:
 * Generates a new matrix and requests the next pin.
 */
static void next_matrix(void) {
	const char * const *wl = mnemonic_wordlist();
	char word_choices[9][12];
	uint32_t i, idx, first, num;
	bool last = (word_index % 4) == 3;

	switch (word_index % 4) {
	case 3:
		idx = TABLE1(word_pincode / 9) + word_pincode % 9;
		first = word_table2[idx] & 0xfff;
		num  = (word_table2[idx+1] & 0xfff) - first;
		for (i = 0; i < num; i++) {
			strlcpy(word_choices[i], wl[first + i], sizeof(word_choices[i]));
		}
		break;

	case 2:
		idx = TABLE1(word_pincode);
		num = TABLE1(word_pincode + 1) - idx;
		for (i = 0; i < num; i++) {
			add_choice(word_choices[i], (word_table2[idx + i] >> 12),
					   wl[TABLE2(idx + i)],
					   wl[TABLE2(idx + i + 1) - 1]);
		}
		break;

	case 1:
		idx = word_pincode * 9;
		num = 9;
		for (i = 0; i < num; i++) {
			add_choice(word_choices[i], (word_table1[idx + i] >> 12),
					   wl[TABLE2(TABLE1(idx + i))],
					   wl[TABLE2(TABLE1(idx + i + 1)) - 1]);
		}
		break;

	case 0:
		num = 9;
		for (i = 0; i < num; i++) {
			add_choice(word_choices[i], 1,
					   wl[TABLE2(TABLE1(9*i))],
					   wl[TABLE2(TABLE1(9*(i+1)))-1]);
		}
		break;
	}
	display_choices(last, word_choices, num);

	recovery_request();
}

/* Function called when a digit was entered by user.
 * digit: ascii code of the entered digit ('1'-'9') or
 * '\x08' for backspace.
 */
static void recovery_digit(const char digit) {
	if (digit == 8) {
		/* backspace: undo */
		if ((word_index % 4) == 0) {
			/* undo complete word */
			if (word_index > 0)
				word_index -= 4;
		} else {
			word_index--;
			word_pincode /= 9;
		}
		next_matrix();
		return;
	}

	if (digit < '1' || digit > '9') {
		recovery_request();
		return;
	}

	int choice = word_matrix[digit - '1'];
	if ((word_index % 4) == 3) {
		/* received final word */
		int y = 54 - ((digit - '1')/3)*11;
		int x = 64 * (((digit - '1') % 3) > 0);
		oledInvert(x, y, x + 63, y + 9);
		oledRefresh();
		usbSleep(250);

		int idx = TABLE2(TABLE1(word_pincode / 9) + (word_pincode % 9)) + choice;
		uint32_t widx = word_index / 4;

		word_pincode = 0;
		strlcpy(words[widx], mnemonic_wordlist()[idx], sizeof(words[widx]));
		if (widx + 1 == word_count) {
			recovery_done();
			return;
		}
		/* next word */
	} else {
		word_pincode = word_pincode * 9 + choice;
	}
	word_index++;
	next_matrix();
}

/* Helper function for scrambled recovery:
 * Ask the user for the next word.
 */
void next_word(void) {
	word_pos = word_order[word_index];
	if (word_pos == 0) {
		const char * const *wl = mnemonic_wordlist();
		strlcpy(fake_word, wl[random_uniform(2048)], sizeof(fake_word));
		layoutDialogSwipe(&bmp_icon_info, NULL, NULL, NULL, "Please enter the word", NULL, fake_word, NULL, "on your computer", NULL);
	} else {
		fake_word[0] = 0;
		char desc[] = "##th word";
		format_number(desc, word_pos);
		layoutDialogSwipe(&bmp_icon_info, NULL, NULL, NULL, "Please enter the", NULL, (word_pos < 10 ? desc + 1 : desc), NULL, "of your mnemonic", NULL);
	}
	recovery_request();
}

void recovery_init(uint32_t _word_count, bool passphrase_protection, bool pin_protection, const char *language, const char *label, bool _enforce_wordlist, uint32_t type, uint32_t u2f_counter)
{
	if (_word_count != 12 && _word_count != 18 && _word_count != 24) return;

	word_count = _word_count;
	enforce_wordlist = _enforce_wordlist;

	if (pin_protection && !protectChangePin()) {
		fsm_sendFailure(FailureType_Failure_ActionCancelled, "PIN change failed");
		layoutHome();
		return;
	}

	storage.has_passphrase_protection = true;
	storage.passphrase_protection = passphrase_protection;
	storage_setLanguage(language);
	storage_setLabel(label);
	storage_setU2FCounter(u2f_counter);

	if ((type & RecoveryDeviceType_RecoveryDeviceType_Matrix) != 0) {
		awaiting_word = 2;
		word_index = 0;
		next_matrix();
	} else {
		uint32_t i;
		for (i = 0; i < word_count; i++) {
			word_order[i] = i + 1;
		}
		for (i = word_count; i < 24; i++) {
			word_order[i] = 0;
		}
		random_permute(word_order, 24);
		awaiting_word = 1;
		word_index = 0;
		next_word();
	}
}

static void recovery_scrambledword(const char *word)
{
	if (word_pos == 0) { // fake word
		if (strcmp(word, fake_word) != 0) {
			storage_reset();
			fsm_sendFailure(FailureType_Failure_SyntaxError, "Wrong word retyped");
			layoutHome();
			return;
		}
	} else { // real word
		if (enforce_wordlist) { // check if word is valid
			const char * const *wl = mnemonic_wordlist();
			bool found = false;
			while (*wl) {
				if (strcmp(word, *wl) == 0) {
					found = true;
					break;
				}
				wl++;
			}
			if (!found) {
				storage_reset();
				fsm_sendFailure(FailureType_Failure_SyntaxError, "Word not found in a wordlist");
				layoutHome();
				return;
			}
		}
		strlcpy(words[word_pos - 1], word, sizeof(words[word_pos - 1]));
	}

	if (word_index + 1 == 24) { // last one
		recovery_done();
	} else {
		word_index++;
		next_word();
	}
}

/* Function called when a word was entered by user. Used
 * for scrambled recovery.
 */
void recovery_word(const char *word)
{
	switch (awaiting_word) {
	case 2:
		recovery_digit(word[0]);
		break;
	case 1:
		recovery_scrambledword(word);
		break;
	default:
		fsm_sendFailure(FailureType_Failure_UnexpectedMessage, "Not in Recovery mode");
		break;
	}
}

/* Abort recovery.
 */
void recovery_abort(void)
{
	if (awaiting_word) {
		layoutHome();
		awaiting_word = 0;
	}
}

#if DEBUG_LINK

const char *recovery_get_fake_word(void)
{
	return fake_word;
}

uint32_t recovery_get_word_pos(void)
{
	return word_pos;
}

#endif
