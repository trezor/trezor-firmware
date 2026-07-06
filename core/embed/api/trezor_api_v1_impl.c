/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "trezor_api_v1.h"

// temporary hack to avoid usage of enum
bool syslog_start_record_(const log_source_t* source, uint32_t level) {
#ifdef USE_DBG_CONSOLE
  return syslog_start_record(source, level);
#else
  return true;
#endif
}

// temporary hack to allow compilation when DBG console is disabled
#ifndef USE_DBG_CONSOLE
ssize_t dbg_console_write(const void* data, size_t data_size) {
  return data_size;
}

ssize_t syslog_write_chunk(const char* text, size_t text_len, bool end_record) {
  return text_len;
}
#endif

const trezor_crypto_v1_t trezor_crypto_v1 = {
    .ed25519_cosi_combine_publickeys = ed25519_cosi_combine_publickeys,
    .ed25519_sign_open = ed25519_sign_open,
    .sha3_256_Init = sha3_256_Init,
    .sha3_512_Init = sha3_512_Init,
    .sha3_Update = sha3_Update,
    .sha3_Final = sha3_Final,
    .keccak_Final = keccak_Final,
    .sha256_Init = sha256_Init,
    .sha256_Update = sha256_Update,
    .sha256_Final = sha256_Final,
    .sha512_Init = sha512_Init,
    .sha512_Update = sha512_Update,
    .sha512_Final = sha512_Final,
    .hmac_sha256_Init = hmac_sha256_Init,
    .hmac_sha256_Update = hmac_sha256_Update,
    .hmac_sha256_Final = hmac_sha256_Final,
    .ecdsa_recover_pub_from_sig = ecdsa_recover_pub_from_sig,
    .ecdsa_verify_digest = ecdsa_verify_digest,
    .secp256k1 = &secp256k1,
    .nist256p1 = &nist256p1,
};

const trezor_api_v1_t trezor_api_v1 = {
    .system_exit = system_exit,
    .system_exit_error = system_exit_error,
    .system_exit_error_ex = system_exit_error_ex,
    .system_exit_fatal = system_exit_fatal,
    .system_exit_fatal_ex = system_exit_fatal_ex,
    .systick_ms = systick_ms,
    .sysevents_poll = sysevents_poll,
    .dbg_console_write = dbg_console_write,
    .syslog_start_record = syslog_start_record_,
    .syslog_write_chunk = syslog_write_chunk,
    .ipc_register = ipc_register,
    .ipc_unregister = ipc_unregister,
    .ipc_try_receive = ipc_try_receive,
    .ipc_message_free = ipc_message_free,
    .ipc_send = ipc_send,
    .app_get_heap = app_get_heap,
    .trezor_crypto_v1 = &trezor_crypto_v1,
};

const void* coreapp_api_get(uint32_t version) {
  if (version == 1) {
    return &trezor_api_v1;
  }
  return NULL;
}
