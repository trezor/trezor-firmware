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


#include <sec/tropic_transport.h>
#include <sec/secret.h>
#include "ed25519-donna/ed25519.h"

#define PKEY_INDEX_BYTE PAIRING_KEY_SLOT_INDEX_0

STATIC lt_handle_t lt_handle = {0};

tropic_result tropic_init(void) {
  lt_ret_t ret = lt_init(&lt_handle);
  if (ret != LT_OK) {
    return TROPIC_ERR_INIT;
  }

  return TROPIC_SUCCESS;
}

tropic_result tropic_handshake(const uint8_t *trezor_privkey) {
  lt_ret_t ret = LT_FAIL;

  uint8_t X509_cert[LT_L2_GET_INFO_REQ_CERT_SIZE] = {0};
  ret = lt_get_info_cert(&lt_handle, X509_cert, LT_L2_GET_INFO_REQ_CERT_SIZE);
  if (ret != LT_OK) {
    return TROPIC_ERR_GET_INFO_CERT;
  }

  uint8_t stpub[32] = {0};
  ret = lt_cert_verify_and_parse(X509_cert, 512, stpub);
  if (ret != LT_OK) {
    return TROPIC_ERR_CERT_VERIFY_AND_PARSE;
  }

  uint8_t shipub[SECRET_TROPIC_KEY_LEN] = {};
  curve25519_scalarmult_basepoint(shipub, trezor_privkey);

  ret = lt_session_start(&lt_handle, stpub, PKEY_INDEX_BYTE, trezor_privkey, shipub);
  if (ret != LT_OK) {
    return TROPIC_ERR_SESSION_START;
  }

  return TROPIC_SUCCESS;
}
