/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <trezor_types.h>

/* RFC 3394 wrap (encrypt) or unwrap of a 32-byte key under the BHK. value
 * holds the 8-byte integrity block followed by the key; on wrap the first 8
 * bytes are ignored. Unwrap fails on an integrity mismatch and then zeroes
 * value. Runs in the secure world: directly in a secure-mode kernel, through
 * an smcall when secmon owns SAES. The BHK must not be used for anything else,
 * as this exposes a wrap/unwrap oracle under it to the caller. */
secbool vault_kek_wrap(bool encrypt, uint8_t value[40]);
