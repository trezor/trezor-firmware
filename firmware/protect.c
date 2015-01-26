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

#include "protect.h"
#include "storage.h"
#include "messages.h"
#include "usb.h"
#include "oled.h"
#include "buttons.h"
#include "pinmatrix.h"
#include "fsm.h"
#include "layout2.h"
#include "util.h"
#include "debug.h"

bool protectAbortedByInitialize = false;

bool protectButton(ButtonRequestType type, bool confirm_only)
{
	ButtonRequest resp;
	bool result = false;
	bool acked = false;
#if DEBUG_LINK
	bool debug_decided = false;
#endif

	memset(&resp, 0, sizeof(ButtonRequest));
	resp.has_code = true;
	resp.code = type;
	usbTiny(1);
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
			delay(100000);
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
		if (msg_tiny_id == MessageType_MessageType_Cancel || msg_tiny_id == MessageType_MessageType_Initialize) {
			if (msg_tiny_id == MessageType_MessageType_Initialize) {
				protectAbortedByInitialize = true;
			}
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
	memset(&resp, 0, sizeof(PinMatrixRequest));
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
		if (msg_tiny_id == MessageType_MessageType_Cancel || msg_tiny_id == MessageType_MessageType_Initialize) {
			pinmatrix_done(0);
			if (msg_tiny_id == MessageType_MessageType_Initialize) {
				protectAbortedByInitialize = true;
			}
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

bool protectPin(bool use_cached)
{
	if (!storage.has_pin || strlen(storage.pin) == 0 || (use_cached && session_isPinCached())) {
		return true;
	}
	uint32_t fails = storage_getPinFails();
	if (fails) {
		if (fails > 2) {
			layoutDialogSwipe(DIALOG_ICON_INFO, NULL, NULL, NULL, "Wrong PIN entered", NULL, "Please wait ...", NULL, NULL, NULL);
		}
		uint32_t wait;
		wait = (fails < 32) ? (1u << fails) : 0xFFFFFFFF;
		while (--wait > 0) {
			delay(10000000);
		}
	}
	storage_increasePinFails();
	bool increase_failed = (fails >= storage_getPinFails());
	const char *pin;
	pin = requestPin(PinMatrixRequestType_PinMatrixRequestType_Current, "Please enter current PIN:");
	if (!pin) {
		fsm_sendFailure(FailureType_Failure_PinCancelled, "PIN Cancelled");
		return false;
	}
	if (storage_isPinCorrect(pin) && !increase_failed) {
		session_cachePin(pin);
		storage_resetPinFails();
		return true;
	} else {
		fsm_sendFailure(FailureType_Failure_PinInvalid, "Invalid PIN");
		return false;
	}
}

bool protectChangePin(void)
{
	const char *pin;
	char pin1[17], pin2[17];
	pin = requestPin(PinMatrixRequestType_PinMatrixRequestType_NewFirst, "Please enter new PIN:");
	if (!pin) {
		return false;
	}
	strlcpy(pin1, pin, sizeof(pin1));
	pin = requestPin(PinMatrixRequestType_PinMatrixRequestType_NewSecond, "Please re-enter new PIN:");
	if (!pin) {
		return false;
	}
	strlcpy(pin2, pin, sizeof(pin2));
	if (strcmp(pin1, pin2) == 0) {
		storage_setPin(pin1);
		return true;
	} else {
		return false;
	}
}

bool protectPassphrase(void)
{
	if (!storage.has_passphrase_protection || !storage.passphrase_protection || session_isPassphraseCached()) {
		return true;
	}

	PassphraseRequest resp;
	memset(&resp, 0, sizeof(PassphraseRequest));
	usbTiny(1);
	msg_write(MessageType_MessageType_PassphraseRequest, &resp);

	layoutDialogSwipe(DIALOG_ICON_INFO, NULL, NULL, NULL, "Please enter your", "passphrase using", "the computer's", "keyboard.", NULL, NULL);

	bool result;
	for (;;) {
		usbPoll();
		if (msg_tiny_id == MessageType_MessageType_PassphraseAck) {
			msg_tiny_id = 0xFFFF;
			PassphraseAck *ppa = (PassphraseAck *)msg_tiny;
			session_cachePassphrase(ppa->passphrase);
			result = true;
			break;
		}
		if (msg_tiny_id == MessageType_MessageType_Cancel || msg_tiny_id == MessageType_MessageType_Initialize) {
			if (msg_tiny_id == MessageType_MessageType_Initialize) {
				protectAbortedByInitialize = true;
			}
			msg_tiny_id = 0xFFFF;
			result = false;
			break;
		}
	}
	usbTiny(0);
	layoutHome();
	return result;
}
