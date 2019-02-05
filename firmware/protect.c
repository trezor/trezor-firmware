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

#include "protect.h"
#include "config.h"
#include "memory.h"
#include "messages.h"
#include "usb.h"
#include "oled.h"
#include "buttons.h"
#include "pinmatrix.h"
#include "fsm.h"
#include "layout2.h"
#include "util.h"
#include "debug.h"
#include "gettext.h"
#include "memzero.h"
#include "messages.pb.h"

#define MAX_WRONG_PINS 15

bool protectAbortedByCancel = false;
bool protectAbortedByInitialize = false;

bool protectButton(ButtonRequestType type, bool confirm_only)
{
	ButtonRequest resp;
	bool result = false;
	bool acked = false;
#if DEBUG_LINK
	bool debug_decided = false;
#endif

	memzero(&resp, sizeof(ButtonRequest));
	resp.has_code = true;
	resp.code = type;
	usbTiny(1);
	buttonUpdate(); // Clear button state
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
		protectAbortedByInitialize = (msg_tiny_id == MessageType_MessageType_Initialize);
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

const char *requestPin(PinMatrixRequestType type, const char *text)
{
	PinMatrixRequest resp;
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
			pinmatrix_done(pma->pin); // convert via pinmatrix
			usbTiny(0);
			return pma->pin;
		}
		// check for Cancel / Initialize
		protectAbortedByCancel = (msg_tiny_id == MessageType_MessageType_Cancel);
		protectAbortedByInitialize = (msg_tiny_id == MessageType_MessageType_Initialize);
		if (protectAbortedByCancel || protectAbortedByInitialize) {
			pinmatrix_done(0);
			msg_tiny_id = 0xFFFF;
			usbTiny(0);
			return 0;
		}
#if DEBUG_LINK
		if (msg_tiny_id == MessageType_MessageType_DebugLinkGetState) {
			msg_tiny_id = 0xFFFF;
			fsm_msgDebugLinkGetState((DebugLinkGetState *)msg_tiny);
		}
#endif
	}
}

void protectPinUiCallback(uint32_t wait, uint32_t progress)
{
    (void) progress;

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
    layoutDialog(&bmp_icon_info, NULL, NULL, NULL, _("Wrong PIN entered"), NULL, _("Please wait"), secstr, _("to continue ..."), NULL);

    /* TODO
    if (msg_tiny_id == MessageType_MessageType_Initialize) {
        protectAbortedByCancel = false;
        protectAbortedByInitialize = true;
        msg_tiny_id = 0xFFFF;
        usbTiny(0);
        fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
        return false;
    }
    */
}

bool protectPin(bool use_cached)
{
	if (use_cached && session_isPinCached()) {
		return true;
	}

    // TODO If maximum number of PIN attempts:
    // error_shutdown("Too many wrong PIN", "attempts. Storage has", "been wiped.", NULL, "Please unplug", "the device.");

	const char *pin = "";
	if (config_hasPin()) {
        pin = requestPin(PinMatrixRequestType_PinMatrixRequestType_Current, _("Please enter current PIN:"));
        if (!pin) {
            fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
            return false;
        }
	}

    usbTiny(1);
	bool ret = config_containsPin(pin);
    usbTiny(0);
	if (!ret) {
		fsm_sendFailure(FailureType_Failure_PinInvalid, NULL);
	}
    return ret;
}

bool protectChangePin(bool removal)
{
    static CONFIDENTIAL char old_pin[MAX_PIN_LEN + 1] = "";
    static CONFIDENTIAL char new_pin[MAX_PIN_LEN + 1] = "";
    const char* pin = NULL;

    if (config_hasPin()) {
        pin = requestPin(PinMatrixRequestType_PinMatrixRequestType_Current, _("Please enter current PIN:"));
        if (pin == NULL) {
            fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
            return false;
        }
        strlcpy(old_pin, pin, sizeof(old_pin));
    }

    if (!removal) {
        pin = requestPin(PinMatrixRequestType_PinMatrixRequestType_NewFirst, _("Please enter new PIN:"));
        if (pin == NULL) {
            memzero(old_pin, sizeof(old_pin));
            fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
            return false;
        }
        strlcpy(new_pin, pin, sizeof(new_pin));

        pin = requestPin(PinMatrixRequestType_PinMatrixRequestType_NewSecond, _("Please re-enter new PIN:"));
        if (pin == NULL) {
            memzero(old_pin, sizeof(old_pin));
            memzero(new_pin, sizeof(new_pin));
            fsm_sendFailure(FailureType_Failure_PinCancelled, NULL);
            return false;
        }

        if (strncmp(new_pin, pin, sizeof(new_pin)) != 0) {
            memzero(old_pin, sizeof(old_pin));
            memzero(new_pin, sizeof(new_pin));
            fsm_sendFailure(FailureType_Failure_PinMismatch, NULL);
            return false;
        }
    }

    usbTiny(1);
    bool ret = config_changePin(old_pin, new_pin);
    usbTiny(0);
    memzero(old_pin, sizeof(old_pin));
    memzero(new_pin, sizeof(new_pin));
    if (ret == false) {
        fsm_sendFailure(FailureType_Failure_PinInvalid, NULL);
    }
    return ret;
}

bool protectPassphrase(void)
{
	if (!config_hasPassphraseProtection() || session_isPassphraseCached()) {
		return true;
	}

	PassphraseRequest resp;
	memzero(&resp, sizeof(PassphraseRequest));
	usbTiny(1);
	msg_write(MessageType_MessageType_PassphraseRequest, &resp);

	layoutDialogSwipe(&bmp_icon_info, NULL, NULL, NULL, _("Please enter your"), _("passphrase using"), _("the computer's"), _("keyboard."), NULL, NULL);

	bool result;
	for (;;) {
		usbPoll();
		// TODO: correctly process PassphraseAck with state field set (mismatch => Failure)
		if (msg_tiny_id == MessageType_MessageType_PassphraseAck) {
			msg_tiny_id = 0xFFFF;
			PassphraseAck *ppa = (PassphraseAck *)msg_tiny;
			session_cachePassphrase(ppa->has_passphrase ? ppa->passphrase : "");
			result = true;
			break;
		}
		// check for Cancel / Initialize
		protectAbortedByCancel = (msg_tiny_id == MessageType_MessageType_Cancel);
		protectAbortedByInitialize = (msg_tiny_id == MessageType_MessageType_Initialize);
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
