/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* One APDU exchange with the card. The response includes SW1 SW2. Fails when
 * no card is present or the tap ended; the next call starts a new tap.
 * Implementations: TCP to the card model (emulator, CI), Android IsoDep over
 * JNI, or the card model linked in-process. */
bool card_transceive(const uint8_t *command, size_t command_length,
                     uint8_t *response, size_t *response_length);

/* End the current tap. The card loses its selected seed. */
void card_disconnect(void);

/* Provided by the vault: called about every 50 ms while the transport waits
 * for the card, with the time waited for this response. Returns false to give
 * up, on timeout or when the user cancels. */
bool card_waiting(uint32_t waited_ms);
