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

#pragma once

#include <sys/sysevent.h>
#include <sys/system.h>
#include <sys/systick.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

#ifdef USE_IPC
#include <sys/ipc.h>
#endif

#include "bip32.h"
#include "ecdsa.h"
#include "ed25519-donna/ed25519.h"
#include "hmac.h"
#include "secp256k1.h"
#include "sha2.h"
#include "sha3.h"
#include "nist256p1.h"

#ifndef USE_DBG_CONSOLE
    // temporary hack to allow compilation when DBG console is disabled
    ssize_t dbg_console_write(const void* data, size_t data_size);
#endif

typedef struct {
  int (*ed25519_cosi_combine_publickeys)(ed25519_public_key res,
                                         CONST ed25519_public_key* pks,
                                         size_t n);
  int (*ed25519_sign_open)(const unsigned char* m, size_t mlen,
                           const ed25519_public_key pk,
                           const ed25519_signature RS);
  void (*sha3_256)(const unsigned char* data, size_t len,
                   unsigned char* digest);
  void (*keccak_256)(const unsigned char* data, size_t len,
                     unsigned char* digest);
  void (*sha256_Init)(SHA256_CTX* ctx);
  void (*sha256_Update)(SHA256_CTX* ctx, const unsigned char* data, size_t len);
  void (*sha256_Final)(SHA256_CTX* ctx, unsigned char* digest);
  void (*sha512_Init)(SHA512_CTX* ctx);
  void (*sha512_Update)(SHA512_CTX* ctx, const unsigned char* data, size_t len);
  void (*sha512_Final)(SHA512_CTX* ctx, unsigned char* digest);
  void (*hmac_sha256_Init)(HMAC_SHA256_CTX* hctx, const uint8_t* key,
                           const uint32_t keylen);
  ;
  void (*hmac_sha256_Update)(HMAC_SHA256_CTX* hctx, const uint8_t* msg,
                             const uint32_t msglen);
  void (*hmac_sha256_Final)(HMAC_SHA256_CTX* hctx, uint8_t* hmac);
  int (*ecdsa_recover_pub_from_sig)(const ecdsa_curve* curve, uint8_t* pub_key,
                                    const uint8_t* sig, const uint8_t* digest,
                                    int recid);
  int (*ecdsa_verify_digest)(const ecdsa_curve* curve, const uint8_t* pub_key,
                             const uint8_t* sig, const uint8_t* digest);
  const ecdsa_curve* secp256k1;
  const ecdsa_curve* nist256p1;
} trezor_crypto_v1_t;

typedef struct {
  void (*system_exit)(int exitcode);

  void (*system_exit_error)(const char* title, const char* message,
                            const char* footer);

  void (*system_exit_error_ex)(const char* title, size_t title_len,
                               const char* message, size_t message_len,
                               const char* footer, size_t footer_len);

  void (*system_exit_fatal)(const char* message, const char* file, int line);

  void (*system_exit_fatal_ex)(const char* message, size_t message_len,
                               const char* file, size_t file_len, int line);

  ssize_t (*dbg_console_write)(const void* data, size_t size);

  uint32_t (*systick_ms)(void);

  void (*sysevents_poll)(const sysevents_t* awaited, sysevents_t* signalled,
                         uint32_t deadline);

  ssize_t (*syshandle_read)(syshandle_t handle, void* buffer,
                            size_t buffer_size);

  bool (*ipc_register)(systask_id_t remote, void* buffer, size_t size);

  void (*ipc_unregister)(systask_id_t remote);

  bool (*ipc_try_receive)(ipc_message_t* msg);

  void (*ipc_message_free)(ipc_message_t* msg);

  bool (*ipc_send)(systask_id_t remote, uint32_t fn, const void* data,
                   size_t data_size);

  const trezor_crypto_v1_t* trezor_crypto_v1;

} trezor_api_v1_t;
