/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once

/* APDU protocol between the vault card backend and a Trezor card: ISO 7816-4
 * short APDUs (CLA INS P1 P2 Lc data), responses end with SW1 SW2.
 *
 * The card is stateless between taps except for the mnemonic in NVM. Each tap
 * selects the seed with the session passphrase; every later command carries
 * the 4-byte seed tag the selection returned, so a command never runs against
 * another card or another passphrase. Commands are idempotent and safe to
 * retry after a lost tap. */

#define CARD_CLA 0x80

/* data: passphrase (UTF-8, at most 200 bytes); response: tag[4]. */
#define CARD_INS_SELECT_SEED 0x10
/* data: node; response: depth u8, child u32 BE, chain[32], public[33]. */
#define CARD_INS_GET_PUBLIC 0x20
/* P1: VAULT_CANONICAL_*; data: node, digest[32];
 * response: recovery u8, signature[64]. */
#define CARD_INS_SIGN 0x30

#define CARD_SW_OK 0x9000
#define CARD_SW_WRONG_LENGTH 0x6700
#define CARD_SW_NO_SEED 0x6985 /* no seed selected, or another tag */
#define CARD_SW_WRONG_DATA 0x6A80
#define CARD_SW_INS 0x6D00
#define CARD_SW_CLA 0x6E00
#define CARD_SW_FAILED 0x6F00

/* Node encoding: tag[4], curve u8, depth u8, depth * index u32 BE. Curve ids
 * follow the vault curve table; the card implements the first three. */
#define CARD_CURVE_SECP256K1 0
#define CARD_CURVE_NIST256P1 1
#define CARD_CURVE_ED25519 2
#define CARD_CURVE_COUNT 3
#define CARD_TAG_SIZE 4
#define CARD_MAX_DEPTH 20
#define CARD_NODE_MAX (CARD_TAG_SIZE + 2 + 4 * CARD_MAX_DEPTH)
#define CARD_PUBLIC_SIZE (1 + 4 + 32 + 33)
#define CARD_SIGN_SIZE 65
#define CARD_PASSPHRASE_MAX 200

#define CARD_COMMAND_MAX (5 + 255)
#define CARD_RESPONSE_MAX (256 + 2)
