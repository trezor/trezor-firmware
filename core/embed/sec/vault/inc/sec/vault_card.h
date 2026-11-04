/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stdint.h>

/* Emulator vault whose seed is on an NFC card (TREZOR_VAULT_CARD=1). */

/* Forget all card seed handles and end the tap: on lock and vault wipe. */
void vault_card_wipe(void);

typedef enum {
  VAULT_CARD_WAITING = 0, /* asking for the card, remaining_ms left */
  VAULT_CARD_DONE,        /* the operation the card was tapped for succeeded */
  VAULT_CARD_TIMEOUT,     /* no card came in time */
  VAULT_CARD_CANCELLED,   /* the user cancelled the prompt */
  VAULT_CARD_FAILED,      /* the card was lost, refused, or is another card */
} vault_card_state_t;

/* Card prompt: called repeatedly with VAULT_CARD_WAITING while the vault
 * waits for a tap, then once with the operation's outcome. The outcome is
 * also reported for a card failure without a prompt. Returns true to cancel
 * the wait. */
typedef bool (*vault_card_ui_t)(vault_card_state_t state,
                                uint32_t remaining_ms);
void vault_card_set_ui(vault_card_ui_t ui);
