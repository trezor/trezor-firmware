/*
 * This file is part of the Trezor project, https://trezor.io/
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
#include "bip39.h"
#include "config.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "memzero.h"
#include "messages.h"
#include "messages.pb.h"
#include "oled.h"
#include "protect.h"
#include "rng.h"
#include "sha2.h"
#include "util.h"

static uint32_t strength;
static uint8_t int_entropy[32];
static bool awaiting_entropy = false;
static bool skip_backup = false;
static bool no_backup = false;

void reset_init(bool display_random, uint32_t _strength,
                bool passphrase_protection, bool pin_protection,
                const char *language, const char *label, uint32_t u2f_counter,
                bool _skip_backup, bool _no_backup) {
  if (_strength != 128 && _strength != 192 && _strength != 256) return;

  strength = _strength;
  skip_backup = _skip_backup;
  no_backup = _no_backup;

  if (display_random && (skip_backup || no_backup)) {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    "Can't show internal entropy when backup is skipped");
    layoutHome();
    return;
  }

  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Do you really want to"), _("create a new wallet?"), NULL,
                    _("By continuing you"), _("agree to trezor.io/tos"), NULL);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  random_buffer(int_entropy, 32);

  if (display_random) {
    for (int start = 0; start < 2; start++) {
      char ent_str[4][17] = {0};
      char desc[] = "Internal entropy _/2:";
      data2hex(int_entropy + start * 16, 4, ent_str[0]);
      data2hex(int_entropy + start * 16 + 4, 4, ent_str[1]);
      data2hex(int_entropy + start * 16 + 8, 4, ent_str[2]);
      data2hex(int_entropy + start * 16 + 12, 4, ent_str[3]);
      layoutLast = layoutDialogSwipe;
      layoutSwipe();
      desc[17] = '1' + start;
      oledDrawStringCenter(OLED_WIDTH / 2, 0, desc, FONT_STANDARD);
      oledDrawStringCenter(OLED_WIDTH / 2, 2 + 1 * 9, ent_str[0], FONT_FIXED);
      oledDrawStringCenter(OLED_WIDTH / 2, 2 + 2 * 9, ent_str[1], FONT_FIXED);
      oledDrawStringCenter(OLED_WIDTH / 2, 2 + 3 * 9, ent_str[2], FONT_FIXED);
      oledDrawStringCenter(OLED_WIDTH / 2, 2 + 4 * 9, ent_str[3], FONT_FIXED);
      oledHLine(OLED_HEIGHT - 13);
      layoutButtonNo(_("Cancel"));
      layoutButtonYes(_("Continue"));
      // 40 is the maximum pixels used for a row
      oledSCA(2 + 1 * 9, 2 + 1 * 9 + 6, 40);
      oledSCA(2 + 2 * 9, 2 + 2 * 9 + 6, 40);
      oledSCA(2 + 3 * 9, 2 + 3 * 9 + 6, 40);
      oledSCA(2 + 4 * 9, 2 + 4 * 9 + 6, 40);
      oledRefresh();
      if (!protectButton(ButtonRequestType_ButtonRequest_ResetDevice, false)) {
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        layoutHome();
        return;
      }
    }
  }

  if (pin_protection && !protectChangePin(false)) {
    layoutHome();
    return;
  }

  config_setPassphraseProtection(passphrase_protection);
  config_setLanguage(language);
  config_setLabel(label);
  config_setU2FCounter(u2f_counter);

  EntropyRequest resp = {0};
  memzero(&resp, sizeof(EntropyRequest));
  msg_write(MessageType_MessageType_EntropyRequest, &resp);
  awaiting_entropy = true;
}

void reset_entropy(const uint8_t *ext_entropy, uint32_t len) {
  if (!awaiting_entropy) {
    fsm_sendFailure(FailureType_Failure_UnexpectedMessage,
                    _("Not in Reset mode"));
    return;
  }
  awaiting_entropy = false;

  SHA256_CTX ctx = {0};
  sha256_Init(&ctx);
  sha256_Update(&ctx, int_entropy, 32);
  sha256_Update(&ctx, ext_entropy, len);
  sha256_Final(&ctx, int_entropy);
  const char *mnemonic = mnemonic_from_data(int_entropy, strength / 8);
  memzero(int_entropy, 32);

  if (skip_backup || no_backup) {
    if (no_backup) {
      config_setNoBackup();
    } else {
      config_setNeedsBackup(true);
    }
    if (config_setMnemonic(mnemonic)) {
      fsm_sendSuccess(_("Device successfully initialized"));
    } else {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to store mnemonic"));
    }
    layoutHome();
  } else {
    reset_backup(false, mnemonic);
  }
  mnemonic_clear();
}

static char current_word[10];

// separated == true if called as a separate workflow via BackupMessage
void reset_backup(bool separated, const char *mnemonic) {
  if (separated) {
    bool needs_backup = false;
    config_getNeedsBackup(&needs_backup);
    if (!needs_backup) {
      fsm_sendFailure(FailureType_Failure_UnexpectedMessage,
                      _("Seed already backed up"));
      return;
    }

    config_setUnfinishedBackup(true);
    config_setNeedsBackup(false);
  }

  for (int pass = 0; pass < 2; pass++) {
    int i = 0, word_pos = 1;
    while (mnemonic[i] != 0) {
      // copy current_word
      int j = 0;
      while (mnemonic[i] != ' ' && mnemonic[i] != 0 &&
             j + 1 < (int)sizeof(current_word)) {
        current_word[j] = mnemonic[i];
        i++;
        j++;
      }
      current_word[j] = 0;
      if (mnemonic[i] != 0) {
        i++;
      }
      layoutResetWord(current_word, pass, word_pos, mnemonic[i] == 0);
      if (!protectButton(ButtonRequestType_ButtonRequest_ConfirmWord, true)) {
        if (!separated) {
          session_clear(true);
        }
        layoutHome();
        fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
        return;
      }
      word_pos++;
    }
  }

  config_setUnfinishedBackup(false);

  if (separated) {
    fsm_sendSuccess(_("Seed successfully backed up"));
  } else {
    config_setNeedsBackup(false);
    if (config_setMnemonic(mnemonic)) {
      fsm_sendSuccess(_("Device successfully initialized"));
    } else {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to store mnemonic"));
    }
  }
  layoutHome();
}

#if DEBUG_LINK

uint32_t reset_get_int_entropy(uint8_t *entropy) {
  memcpy(entropy, int_entropy, 32);
  return 32;
}

const char *reset_get_word(void) { return current_word; }

#endif
