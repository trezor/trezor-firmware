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

#include "protect.h"
#include "buttons.h"
#include "config.h"
#include "debug.h"
#include "fsm.h"
#include "gettext.h"
#include "input.h"
#include "layout2.h"
#include "memory.h"
#include "memzero.h"
#include "messages.h"
#include "messages.pb.h"
#include "oled.h"
#include "pinmatrix.h"
#include "rng.h"
#include "usb.h"
#include "util.h"

#define MAX_WRONG_PINS 15

#define NUM_PASSPHRASE_LINES 3
#define PASSPHRASE_WIDTH \
  ((MAX_PASSPHRASE_LEN + 1) / NUM_PASSPHRASE_LINES * CHAR_FULL_WIDTH)

#define PIN_WIDTH (MAX_PIN_LEN * CHAR_FULL_WIDTH)

bool protectAbortedByCancel = false;
bool protectAbortedByInitialize = false;

bool protectButton(ButtonRequestType type, bool confirm_only) {
  ButtonRequest resp = {0};
  bool result = false;
  bool acked = false;
#if DEBUG_LINK
  bool debug_decided = false;
#endif

  memzero(&resp, sizeof(ButtonRequest));
  resp.has_code = true;
  resp.code = type;
  usbTiny(1);
  buttonUpdate();  // Clear button state
  msg_write(MessageType_MessageType_ButtonRequest, &resp);

  for (;;) {
    usbPoll();

    // check for ButtonAck
    if (msg_tiny_id == MessageType_MessageType_ButtonAck) {
      msg_tiny_id = 0xFFFF;
      acked = true;
    }

    // button acked - check buttons
    if (acked) {
      usbSleep(5);
      buttonUpdate();
      if (button.YesUp) {
        result = true;
        break;
      }
      if (!confirm_only && button.NoUp) {
        result = false;
        break;
      }
    }

    // check for Cancel / Initialize
    protectAbortedByCancel = (msg_tiny_id == MessageType_MessageType_Cancel);
    protectAbortedByInitialize =
        (msg_tiny_id == MessageType_MessageType_Initialize);
    if (protectAbortedByCancel || protectAbortedByInitialize) {
      msg_tiny_id = 0xFFFF;
      result = false;
      break;
    }

#if DEBUG_LINK
    // check DebugLink
    if (msg_tiny_id == MessageType_MessageType_DebugLinkDecision) {
      msg_tiny_id = 0xFFFF;
      DebugLinkDecision *dld = (DebugLinkDecision *)msg_tiny;
      result = dld->yes_no;
      debug_decided = true;
    }

    if (acked && debug_decided) {
      break;
    }

    if (msg_tiny_id == MessageType_MessageType_DebugLinkGetState) {
      msg_tiny_id = 0xFFFF;
      fsm_msgDebugLinkGetState((DebugLinkGetState *)msg_tiny);
    }
#endif
  }

  usbTiny(0);

  return result;
}

bool requestPinComputer(PinMatrixRequestType type, const char *text,
                        char pin[]) {
  PinMatrixRequest resp = {0};
  memzero(&resp, sizeof(PinMatrixRequest));
  resp.has_type = true;
  resp.type = type;
  usbTiny(1);
  msg_write(MessageType_MessageType_PinMatrixRequest, &resp);
  pinmatrix_start(text);
  for (;;) {
    usbPoll();
    if (msg_tiny_id == MessageType_MessageType_PinMatrixAck) {
      msg_tiny_id = 0xFFFF;
      PinMatrixAck *pma = (PinMatrixAck *)msg_tiny;
      pinmatrix_done(pma->pin);  // convert via pinmatrix
      usbTiny(0);
      strlcpy(pin, pma->pin, sizeof(pma->pin));
      return true;
    }
    // check for Cancel / Initialize
    protectAbortedByCancel = (msg_tiny_id == MessageType_MessageType_Cancel);
    protectAbortedByInitialize =
        (msg_tiny_id == MessageType_MessageType_Initialize);
    if (protectAbortedByCancel || protectAbortedByInitialize) {
      pinmatrix_done(0);
      msg_tiny_id = 0xFFFF;
      usbTiny(0);
      pin[0] = 0;
      return false;
    }
#if DEBUG_LINK
    if (msg_tiny_id == MessageType_MessageType_DebugLinkGetState) {
      msg_tiny_id = 0xFFFF;
      fsm_msgDebugLinkGetState((DebugLinkGetState *)msg_tiny);
    }
#endif
  }
}

secbool protectPinUiCallback(uint32_t wait, uint32_t progress,
                             const char *message) {
  // Convert wait to secstr string.
  char secstrbuf[] = _("________0 seconds");
  char *secstr = secstrbuf + 9;
  uint32_t secs = wait;
  do {
    secstr--;
    *secstr = (secs % 10) + '0';
    secs /= 10;
  } while (secs > 0 && secstr >= secstrbuf);
  if (wait == 1) {
    // Change "seconds" to "second".
    secstrbuf[16] = 0;
  }
  oledClear();
  oledDrawStringCenter(OLED_WIDTH / 2, 0 * 9, message, FONT_STANDARD);
  oledDrawStringCenter(OLED_WIDTH / 2, 2 * 9, _("Please wait"), FONT_STANDARD);
  oledDrawStringCenter(OLED_WIDTH / 2, 3 * 9, secstr, FONT_STANDARD);
  oledDrawStringCenter(OLED_WIDTH / 2, 4 * 9, _("to continue ..."),
                       FONT_STANDARD);
  // progressbar
  oledFrame(0, OLED_HEIGHT - 8, OLED_WIDTH - 1, OLED_HEIGHT - 1);
  oledBox(1, OLED_HEIGHT - 7, OLED_WIDTH - 2, OLED_HEIGHT - 2, 0);
  progress = progress * (OLED_WIDTH - 4) / 1000;
  if (progress > OLED_WIDTH - 4) {
    progress = OLED_WIDTH - 4;
  }
  oledBox(2, OLED_HEIGHT - 6, 1 + progress, OLED_HEIGHT - 3, 1);
  oledRefresh();
  // Check for Cancel / Initialize.
  protectAbortedByCancel = (msg_tiny_id == MessageType_MessageType_Cancel);
  protectAbortedByInitialize =
      (msg_tiny_id == MessageType_MessageType_Initialize);
  if (protectAbortedByCancel || protectAbortedByInitialize) {
    msg_tiny_id = 0xFFFF;
    usbTiny(0);
    fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
    return sectrue;
  }

  return secfalse;
}

void inputPin(char pin[]) {
  const char Characters[] = {
      'a',         'b',         'c',         'd',         'e',
      'f',         'g',         'h',         'i',         CHAR_BCKSPC,
      CHAR_DONE,   'j',         'k',         'l',         'm',
      'n',         'o',         'p',         'q',         'r',
      CHAR_BCKSPC, CHAR_DONE,   's',         't',         'u',
      'v',         'w',         'x',         'y',         'z',
      CHAR_SPACE,  CHAR_BCKSPC, CHAR_DONE,   'A',         'B',
      'C',         'D',         'E',         'F',         'G',
      'H',         'I',         CHAR_BCKSPC, CHAR_DONE,   'J',
      'K',         'L',         'M',         'N',         'O',
      'P',         'Q',         'R',         CHAR_BCKSPC, CHAR_DONE,
      'S',         'T',         'U',         'V',         'W',
      'X',         'Y',         'Z',         CHAR_SPACE,  CHAR_BCKSPC,
      CHAR_DONE,   '1',         '2',         '3',         '4',
      '5',         '6',         '7',         '8',         '9',
      '0',         CHAR_BCKSPC, CHAR_DONE,   '!',         '@',
      '#',         '$',         '\x25',      '^',         '&',
      '*',         '(',         ')',         CHAR_BCKSPC, CHAR_DONE,
      '`',         '-',         '=',         '[',         ']',
      '\\',        ';',         '\'',        ',',         '.',
      '/',         CHAR_BCKSPC, CHAR_DONE,   '~',         '_',
      '+',         '{',         '}',         '|',         ':',
      '"',        '<',         '>',         '?',         CHAR_BCKSPC,
      CHAR_DONE};

  inputText(pin, MAX_PIN_LEN, Characters,
            sizeof(Characters) / sizeof(Characters[0]), CHAR_DONE, PIN_WIDTH,
            true, false);
}

bool confirmPin(char pin[]) {
  layoutCheckInput(pin, PIN_WIDTH, true, true, "Confirm PIN:", NULL, NULL);

  buttonUpdate();

  for (;;) {
    usbSleep(5);
    buttonUpdate();
    if (button.YesUp) return true;
    if (button.NoUp) return false;
  }
}

void requestPinDevice(const char *line1, const char *line2, const char *line3,
                      char pin[]) {
  buttonUpdate();

  layoutDialog(NULL, NULL, _("Next"), NULL, line1, line2, line3, NULL, NULL,
               NULL);
  buttonWaitForYesUp();
  layoutSwipe();

  for (;;) {
    inputPin(pin);
    layoutSwipe();

    if (confirmPin(pin)) break;

    oledSwipeRight();
  }

  for (int i = 0; i < MAX_PIN_LEN + 1 && pin[i]; ++i)
    if (pin[i] == CHAR_SPACE) pin[i] = ' ';
}

bool protectPin(bool use_cached) {
  if (use_cached && session_isUnlocked()) {
    return true;
  }

  static CONFIDENTIAL char pin[MAX_PIN_LEN + 1];

  if (config_hasPin()) {
    memzero(pin, sizeof(pin));

    if (!session_isUseOnDeviceTextInputCached()) {
      requestOnDeviceTextInput();
    }

    if (session_isUseOnDeviceTextInput()) {
      requestPinDevice("Please enter current PIN", "on the next screen.", NULL,
                       pin);
    } else {
      requestPinComputer(PinMatrixRequestType_PinMatrixRequestType_Current,
                         _("Please enter current PIN:"), pin);
      if (!pin[0]) {
        memzero(pin, sizeof(pin));
        fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
        return false;
      }
    }
  }

  bool ret = config_unlock(pin);
  memzero(pin, sizeof(pin));
  if (!ret) {
    fsm_sendFailure(FailureType_Failure_PinInvalid, NULL);
  }
  return ret;
}

bool protectChangePin(bool removal) {
  static CONFIDENTIAL char old_pin[MAX_PIN_LEN + 1] = "";
  static CONFIDENTIAL char new_pin[MAX_PIN_LEN + 1] = "";
  static CONFIDENTIAL char pin[MAX_PIN_LEN + 1];

  if (!session_isUseOnDeviceTextInputCached()) {
    requestOnDeviceTextInput();
  }

  if (config_hasPin()) {
    if (session_isUseOnDeviceTextInput()) {
      memzero(pin, sizeof(pin));
      requestPinDevice("Please enter current PIN", "on the next screen.", NULL,
                       pin);
    } else {
      requestPinComputer(PinMatrixRequestType_PinMatrixRequestType_Current,
                         _("Please enter current PIN:"), pin);
      if (!pin[0]) {
        fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
        return false;
      }
    }

    // If removing, defer the check to config_changePin().
    if (!removal) {
      usbTiny(1);
      bool ret = config_unlock(pin);
      usbTiny(0);
      if (ret == false) {
        fsm_sendFailure(FailureType_Failure_PinInvalid, NULL);
        return false;
      }
    }

    strlcpy(old_pin, pin, sizeof(old_pin));
  } else {
    memzero(old_pin, sizeof(old_pin));
  }

  if (!removal) {
    if (session_isUseOnDeviceTextInput()) {
      memzero(pin, sizeof(pin));
      requestPinDevice("Please enter new PIN", "on the next screen.", NULL,
                       pin);
    } else {
      requestPinComputer(PinMatrixRequestType_PinMatrixRequestType_NewFirst,
                         _("Please enter new PIN:"), pin);
      if (!pin[0]) {
        memzero(old_pin, sizeof(old_pin));
        fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
        return false;
      }
    }
    strlcpy(new_pin, pin, sizeof(new_pin));

    if (session_isUseOnDeviceTextInput()) {
      memzero(pin, sizeof(pin));
      requestPinDevice("Please re-enter new PIN", "on the next screen.", NULL,
                       pin);
    } else {
      requestPinComputer(PinMatrixRequestType_PinMatrixRequestType_NewSecond,
                         _("Please re-enter new PIN:"), pin);
      if (!pin[0]) {
        memzero(old_pin, sizeof(old_pin));
        memzero(new_pin, sizeof(new_pin));
        fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
        return false;
      }
    }

    if (strncmp(new_pin, pin, sizeof(new_pin)) != 0) {
      memzero(old_pin, sizeof(old_pin));
      memzero(new_pin, sizeof(new_pin));
      fsm_sendFailure(FailureType_Failure_PinMismatch, NULL);
      return false;
    }
  } else {
    memzero(new_pin, sizeof(new_pin));
  }

  bool ret = config_changePin(old_pin, new_pin);
  memzero(old_pin, sizeof(old_pin));
  memzero(new_pin, sizeof(new_pin));
  memzero(pin, sizeof(pin));
  if (ret == false) {
    fsm_sendFailure(FailureType_Failure_PinInvalid, NULL);
  }
  return ret;
}

bool protectPassphraseComputer(void) {
  PassphraseRequest resp = {0};
  memzero(&resp, sizeof(PassphraseRequest));
  usbTiny(1);
  msg_write(MessageType_MessageType_PassphraseRequest, &resp);

  layoutDialogSwipe(&bmp_icon_info, NULL, NULL, NULL, _("Please enter your"),
                    _("passphrase using"), _("the computer's"), _("keyboard."),
                    NULL, NULL);

  bool result;
  for (;;) {
    usbPoll();
    // TODO: correctly process PassphraseAck with state field set (mismatch =>
    // Failure)
    if (msg_tiny_id == MessageType_MessageType_PassphraseAck) {
      msg_tiny_id = 0xFFFF;
      PassphraseAck *ppa = (PassphraseAck *)msg_tiny;
      session_cachePassphrase(ppa->has_passphrase ? ppa->passphrase : "");
      result = true;
      break;
    }
    // check for Cancel / Initialize
    protectAbortedByCancel = (msg_tiny_id == MessageType_MessageType_Cancel);
    protectAbortedByInitialize =
        (msg_tiny_id == MessageType_MessageType_Initialize);
    if (protectAbortedByCancel || protectAbortedByInitialize) {
      msg_tiny_id = 0xFFFF;
      result = false;
      break;
    }
  }
  usbTiny(0);
  layoutHome();
  return result;
}

void inputPassphrase(char *passphrase) {
  const char Characters[] = {
      'a',         'b',         'c',         'd',         'e',
      'f',         'g',         'h',         'i',         CHAR_BCKSPC,
      CHAR_DONE,   'j',         'k',         'l',         'm',
      'n',         'o',         'p',         'q',         'r',
      CHAR_BCKSPC, CHAR_DONE,   's',         't',         'u',
      'v',         'w',         'x',         'y',         'z',
      CHAR_SPACE,  CHAR_BCKSPC, CHAR_DONE,   'A',         'B',
      'C',         'D',         'E',         'F',         'G',
      'H',         'I',         CHAR_BCKSPC, CHAR_DONE,   'J',
      'K',         'L',         'M',         'N',         'O',
      'P',         'Q',         'R',         CHAR_BCKSPC, CHAR_DONE,
      'S',         'T',         'U',         'V',         'W',
      'X',         'Y',         'Z',         CHAR_SPACE,  CHAR_BCKSPC,
      CHAR_DONE,   '1',         '2',         '3',         '4',
      '5',         '6',         '7',         '8',         '9',
      '0',         CHAR_BCKSPC, CHAR_DONE,   '!',         '@',
      '#',         '$',         '\x25',      '^',         '&',
      '*',         '(',         ')',         CHAR_BCKSPC, CHAR_DONE,
      '`',         '-',         '=',         '[',         ']',
      '\\',        ';',         '\'',        ',',         '.',
      '/',         CHAR_BCKSPC, CHAR_DONE,   '~',         '_',
      '+',         '{',         '}',         '|',         ':',
      '"',         '<',         '>',         '?',         CHAR_BCKSPC,
      CHAR_DONE};

  inputText(passphrase, MAX_PASSPHRASE_LEN, Characters,
            sizeof(Characters) / sizeof(Characters[0]), CHAR_DONE,
            PASSPHRASE_WIDTH, true, true);
}

bool confirmPassphrase(const char *passphrase, bool enable_edit,
                       bool enable_done) {
  layoutCheckInput(passphrase, PASSPHRASE_WIDTH, enable_edit, enable_done,
                   "Confirm passphrase:", "Passphrases mismatched:",
                   "Passphrase confirmed:");

  buttonUpdate();

  for (;;) {
    usbSleep(5);
    buttonUpdate();
    if (enable_done && button.YesUp) return true;
    if (enable_edit && button.NoUp) return false;
  }
}

bool protectPassphraseDevice(void) {
  static CONFIDENTIAL char passphrase[MAX_PASSPHRASE_LEN + 1];

  memzero(passphrase, sizeof(passphrase));
  buttonUpdate();

  layoutDialog(NULL, NULL, _("Next"), NULL, _("You are about to enter"),
               _("the passphrase."), _("Select how many times"),
               _("you'd like to do it."), NULL, NULL);
  buttonWaitForYesUp();
  layoutSwipe();

  layoutDialog(NULL, _("Twice"), _("Once"), NULL,
               _("If you are creating a new"), _("wallet, it is advised"),
               _("that you select Twice."), NULL, NULL, NULL);
  for (;;) {
    usbSleep(5);
    buttonUpdate();
    if (button.YesUp || button.NoUp) break;
  }
  layoutSwipe();

  bool twice = button.NoUp;

  layoutDialog(NULL, NULL, _("Next"), NULL, _("Enter the passphrase"),
               _("on the next screen."), _("- Single button: scroll."),
               _("- Hold: auto-scroll."), _("- Both buttons: confirm."), NULL);
  buttonWaitForYesUp();
  layoutSwipe();

  for (;;) {
    inputPassphrase(passphrase);

    if (confirmPassphrase(passphrase, true, true)) break;

    oledSwipeRight();
  }

  if (twice) {
    static CONFIDENTIAL char passphrase2[MAX_PASSPHRASE_LEN + 1];

    memzero(passphrase2, sizeof(passphrase2));

    layoutSwipe();
    layoutDialog(NULL, NULL, _("Next"), NULL, _("Re-enter the passphrase."),
                 NULL, NULL, NULL, NULL, NULL);
    buttonWaitForYesUp();
    layoutSwipe();

    for (;;) {
      inputPassphrase(passphrase2);

      if (strcmp(passphrase, passphrase2) == 0) break;

      confirmPassphrase(passphrase2, true, false);
      oledSwipeRight();
    }

    memzero(passphrase2, sizeof(passphrase2));
  }

  confirmPassphrase(passphrase, false, true);

  for (int i = 0; i < MAX_PASSPHRASE_LEN + 1 && passphrase[i]; ++i)
    if (passphrase[i] == CHAR_SPACE) passphrase[i] = ' ';

  session_cachePassphrase(passphrase);
  memzero(passphrase, sizeof(passphrase));

  layoutHome();

  return true;
}

bool protectPassphrase(void) {
  bool passphrase_protection = false;
  config_getPassphraseProtection(&passphrase_protection);
  if (!passphrase_protection || session_isPassphraseCached()) {
    return true;
  }

  bool result;
  if (!session_isUseOnDeviceTextInputCached()) {
    requestOnDeviceTextInput();
  }
  if (session_isUseOnDeviceTextInput())
    result = protectPassphraseDevice();
  else
    result = protectPassphraseComputer();
  return result;
}
