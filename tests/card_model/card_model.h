/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stddef.h>
#include <stdint.h>

/* Reference model of the Trezor card: one APDU in, one response out. It holds
 * the mnemonic (the card's NVM) and, until the next reset, the seed selected
 * on this tap (its RAM). No I/O: the TCP server, native tests and an Android
 * HCE service all wrap this same function. */

/* Program the card. Returns 0 if the mnemonic is not valid BIP-39. */
int card_model_init(const char *mnemonic);

/* Power cycle: the tap ended, RAM is gone. */
void card_model_reset(void);

/* Process one command APDU. Returns the response length, SW1 SW2 included;
 * response must hold CARD_RESPONSE_MAX bytes. */
size_t card_model_process(const uint8_t *command, size_t length,
                          uint8_t *response);
