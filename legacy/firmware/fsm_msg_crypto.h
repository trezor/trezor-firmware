/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 Pavol Rusnak <stick@satoshilabs.com>
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

static uint8_t cosi_nonce[32] = {0};
static uint8_t cosi_commitment[32] = {0};
static bool cosi_nonce_is_set = false;

void fsm_msgCipherKeyValue(const CipherKeyValue *msg) {
  CHECK_INITIALIZED

  CHECK_PARAM(msg->value.size % 16 == 0,
              _("Value length must be a multiple of 16"));

  CHECK_PIN

  const HDNode *node = fsm_getDerivedNode(SECP256K1_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  bool encrypt = msg->has_encrypt && msg->encrypt;
  bool ask_on_encrypt = msg->has_ask_on_encrypt && msg->ask_on_encrypt;
  bool ask_on_decrypt = msg->has_ask_on_decrypt && msg->ask_on_decrypt;
  if ((encrypt && ask_on_encrypt) || (!encrypt && ask_on_decrypt)) {
    layoutCipherKeyValue(encrypt, msg->key);
    if (!protectButton(ButtonRequestType_ButtonRequest_Other, false)) {
      fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
      layoutHome();
      return;
    }
  }

  uint8_t data[256 + 4];
  strlcpy((char *)data, msg->key, sizeof(data));
  strlcat((char *)data, ask_on_encrypt ? "E1" : "E0", sizeof(data));
  strlcat((char *)data, ask_on_decrypt ? "D1" : "D0", sizeof(data));

  hmac_sha512(node->private_key, 32, data, strlen((char *)data), data);

  if (msg->iv.size == 16) {
    // override iv if provided
    memcpy(data + 32, msg->iv.bytes, 16);
  }

  RESP_INIT(CipheredKeyValue);
  if (encrypt) {
    aes_encrypt_ctx ctx;
    aes_encrypt_key256(data, &ctx);
    aes_cbc_encrypt(msg->value.bytes, resp->value.bytes, msg->value.size,
                    data + 32, &ctx);
  } else {
    aes_decrypt_ctx ctx;
    aes_decrypt_key256(data, &ctx);
    aes_cbc_decrypt(msg->value.bytes, resp->value.bytes, msg->value.size,
                    data + 32, &ctx);
  }
  resp->value.size = msg->value.size;
  msg_write(MessageType_MessageType_CipheredKeyValue, resp);
  layoutHome();
}

void fsm_msgSignIdentity(const SignIdentity *msg) {
  RESP_INIT(SignedIdentity);

  CHECK_INITIALIZED

  CHECK_PIN

  layoutSignIdentity(&(msg->identity),
                     msg->has_challenge_visual ? msg->challenge_visual : 0);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  uint8_t hash[32];
  if (cryptoIdentityFingerprint(&(msg->identity), hash) == 0) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid identity"));
    layoutHome();
    return;
  }

  uint32_t address_n[5];
  address_n[0] = PATH_HARDENED | 13;
  address_n[1] = PATH_HARDENED | hash[0] | (hash[1] << 8) | (hash[2] << 16) |
                 ((uint32_t)hash[3] << 24);
  address_n[2] = PATH_HARDENED | hash[4] | (hash[5] << 8) | (hash[6] << 16) |
                 ((uint32_t)hash[7] << 24);
  address_n[3] = PATH_HARDENED | hash[8] | (hash[9] << 8) | (hash[10] << 16) |
                 ((uint32_t)hash[11] << 24);
  address_n[4] = PATH_HARDENED | hash[12] | (hash[13] << 8) | (hash[14] << 16) |
                 ((uint32_t)hash[15] << 24);

  const char *curve = SECP256K1_NAME;
  if (msg->has_ecdsa_curve_name) {
    curve = msg->ecdsa_curve_name;
  }
  HDNode *node = fsm_getDerivedNode(curve, address_n, 5, NULL);
  if (!node) return;

  bool sign_ssh =
      msg->identity.has_proto && (strcmp(msg->identity.proto, "ssh") == 0);
  bool sign_gpg =
      msg->identity.has_proto && (strcmp(msg->identity.proto, "gpg") == 0);
  bool sign_signify =
      msg->identity.has_proto && (strcmp(msg->identity.proto, "signify") == 0);

  int result = 0;
  layoutProgressSwipe(_("Signing"), 0);
  if (sign_ssh) {  // SSH does not sign visual challenge
    result = sshMessageSign(node, msg->challenge_hidden.bytes,
                            msg->challenge_hidden.size, resp->signature.bytes);
  } else if (sign_gpg) {  // GPG should sign a message digest
    result = gpgMessageSign(node, msg->challenge_hidden.bytes,
                            msg->challenge_hidden.size, resp->signature.bytes);
  } else if (sign_signify) {  // Signify should sign a message digest
    result =
        signifyMessageSign(node, msg->challenge_hidden.bytes,
                           msg->challenge_hidden.size, resp->signature.bytes);
  } else {
    uint8_t digest[64];
    sha256_Raw(msg->challenge_hidden.bytes, msg->challenge_hidden.size, digest);
    sha256_Raw((const uint8_t *)msg->challenge_visual,
               strlen(msg->challenge_visual), digest + 32);
    result = cryptoMessageSign(&(coins[0]), node, InputScriptType_SPENDADDRESS,
                               false, digest, 64, resp->signature.bytes);
  }

  if (result == 0) {
    if (hdnode_fill_public_key(node) != 0) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to derive public key"));
      layoutHome();
      return;
    }

    if (strcmp(curve, SECP256K1_NAME) != 0) {
      resp->has_address = false;
    } else {
      resp->has_address = true;
      // hardcoded Bitcoin address type
      if (hdnode_get_address(node, 0x00, resp->address,
                             sizeof(resp->address)) != 0) {
        fsm_sendFailure(FailureType_Failure_ProcessError,
                        _("Failed to get address"));
        layoutHome();
        return;
      }
    }
    resp->public_key.size = 33;
    memcpy(resp->public_key.bytes, node->public_key, 33);
    if (node->public_key[0] == 1) {
      /* ed25519 public key */
      resp->public_key.bytes[0] = 0;
    }
    resp->signature.size = 65;
    msg_write(MessageType_MessageType_SignedIdentity, resp);
  } else {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Error signing identity"));
  }
  layoutHome();
}

void fsm_msgGetECDHSessionKey(const GetECDHSessionKey *msg) {
  RESP_INIT(ECDHSessionKey);

  CHECK_INITIALIZED

  CHECK_PIN

  layoutDecryptIdentity(&msg->identity);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  uint8_t hash[32];
  if (cryptoIdentityFingerprint(&(msg->identity), hash) == 0) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Invalid identity"));
    layoutHome();
    return;
  }

  uint32_t address_n[5];
  address_n[0] = PATH_HARDENED | 17;
  address_n[1] = PATH_HARDENED | hash[0] | (hash[1] << 8) | (hash[2] << 16) |
                 ((uint32_t)hash[3] << 24);
  address_n[2] = PATH_HARDENED | hash[4] | (hash[5] << 8) | (hash[6] << 16) |
                 ((uint32_t)hash[7] << 24);
  address_n[3] = PATH_HARDENED | hash[8] | (hash[9] << 8) | (hash[10] << 16) |
                 ((uint32_t)hash[11] << 24);
  address_n[4] = PATH_HARDENED | hash[12] | (hash[13] << 8) | (hash[14] << 16) |
                 ((uint32_t)hash[15] << 24);

  const char *curve = SECP256K1_NAME;
  if (msg->has_ecdsa_curve_name) {
    curve = msg->ecdsa_curve_name;
  }

  HDNode *node = fsm_getDerivedNode(curve, address_n, 5, NULL);
  if (!node) return;

  int result_size = 0;
  if (hdnode_get_shared_key(node, msg->peer_public_key.bytes,
                            resp->session_key.bytes, &result_size) == 0) {
    resp->session_key.size = result_size;
    if (hdnode_fill_public_key(node) != 0) {
      fsm_sendFailure(FailureType_Failure_ProcessError,
                      _("Failed to derive public key"));
      layoutHome();
      return;
    }
    memcpy(resp->public_key.bytes, node->public_key, 33);
    resp->public_key.size = 33;
    resp->has_public_key = true;
    msg_write(MessageType_MessageType_ECDHSessionKey, resp);
  } else {
    fsm_sendFailure(FailureType_Failure_ProcessError,
                    _("Error getting ECDH session key"));
  }
  layoutHome();
}

static bool fsm_checkCosiPath(uint32_t address_n_count,
                              const uint32_t *address_n) {
  // The path should typically match "m / 10018' / [0-9]'", but we allow
  // any path from the SLIP-18 domain "m / 10018' / *".
  if (address_n_count >= 1 && address_n[0] == PATH_HARDENED + 10018) {
    return true;
  }

  if (config_getSafetyCheckLevel() == SafetyCheckLevel_Strict) {
    fsm_sendFailure(FailureType_Failure_DataError, _("Forbidden key path"));
    return false;
  }

  return fsm_layoutPathWarning();
}

void fsm_msgCosiCommit(const CosiCommit *msg) {
  RESP_INIT(CosiCommitment);

  CHECK_INITIALIZED

  CHECK_PIN

  if (!fsm_checkCosiPath(msg->address_n_count, msg->address_n)) {
    layoutHome();
    return;
  }

  const HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  if (!cosi_nonce_is_set) {
    ed25519_cosi_commit(cosi_nonce, cosi_commitment);
    cosi_nonce_is_set = true;
  }

  resp->commitment.size = 32;
  resp->pubkey.size = 32;

  memcpy(resp->commitment.bytes, cosi_commitment, sizeof(cosi_commitment));
  ed25519_publickey(node->private_key, resp->pubkey.bytes);

  msg_write(MessageType_MessageType_CosiCommitment, resp);
  layoutHome();
}

void fsm_msgCosiSign(const CosiSign *msg) {
  RESP_INIT(CosiSignature);

  CHECK_INITIALIZED

  CHECK_PARAM(msg->global_commitment.size == 32,
              _("Invalid global commitment"));
  CHECK_PARAM(msg->global_pubkey.size == 32, _("Invalid global pubkey"));

  if (!cosi_nonce_is_set) {
    fsm_sendFailure(FailureType_Failure_ProcessError, _("CoSi nonce not set"));
    layoutHome();
    return;
  }

  if (!fsm_checkCosiPath(msg->address_n_count, msg->address_n)) {
    layoutHome();
    return;
  }

  CHECK_PIN

  layoutCosiSign(msg->address_n, msg->address_n_count, msg->data.bytes,
                 msg->data.size);
  if (!protectButton(ButtonRequestType_ButtonRequest_ProtectCall, false)) {
    fsm_sendFailure(FailureType_Failure_ActionCancelled, NULL);
    layoutHome();
    return;
  }

  const HDNode *node = fsm_getDerivedNode(ED25519_NAME, msg->address_n,
                                          msg->address_n_count, NULL);
  if (!node) return;

  resp->signature.size = 32;
  cosi_nonce_is_set = false;

  if (ed25519_cosi_sign(msg->data.bytes, msg->data.size, node->private_key,
                        cosi_nonce, msg->global_commitment.bytes,
                        msg->global_pubkey.bytes, resp->signature.bytes) == 0) {
    msg_write(MessageType_MessageType_CosiSignature, resp);
  } else {
    fsm_sendFailure(FailureType_Failure_FirmwareError, NULL);
  }
  fsm_clearCosiNonce();
  layoutHome();
}

void fsm_clearCosiNonce(void) {
  cosi_nonce_is_set = false;
  memzero(cosi_nonce, sizeof(cosi_nonce));
}
