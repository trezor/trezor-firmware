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

#include "optiga_prodtest.h"
#include "aes/aes.h"
#include "ecdsa.h"
#include "memzero.h"
#include "nist256p1.h"
#include "optiga_commands.h"
#include "optiga_transport.h"
#include "prodtest_common.h"
#include "rand.h"
#include "secret.h"
#include "sha2.h"

typedef enum {
  OPTIGA_PAIRING_UNPAIRED = 0,
  OPTIGA_PAIRING_PAIRED,
  OPTIGA_PAIRING_ERR_RNG,
  OPTIGA_PAIRING_ERR_READ,
  OPTIGA_PAIRING_ERR_HANDSHAKE,
} optiga_pairing;

static optiga_pairing optiga_pairing_state = OPTIGA_PAIRING_UNPAIRED;

// Data object access conditions.
static const optiga_metadata_item ACCESS_PAIRED =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_CONF, OID_KEY_PAIRING);
static const optiga_metadata_item KEY_USE_SIGN = {
    (const uint8_t[]){OPTIGA_KEY_USAGE_SIGN}, 1};
static const optiga_metadata_item TYPE_PTFBIND = {
    (const uint8_t[]){OPTIGA_DATA_TYPE_PTFBIND}, 1};

static bool optiga_paired(void) {
  const char *details = "";

  switch (optiga_pairing_state) {
    case OPTIGA_PAIRING_PAIRED:
      return true;
    case OPTIGA_PAIRING_ERR_RNG:
      details = "optiga_get_random error";
      break;
    case OPTIGA_PAIRING_ERR_READ:
      details = "failed to read pairing secret";
      break;
    case OPTIGA_PAIRING_ERR_HANDSHAKE:
      details = "optiga_sec_chan_handshake";
      break;
    default:
      break;
  }

  vcp_println("ERROR Optiga not paired (%s).", details);
  return false;
}

static bool set_metadata(uint16_t oid, const optiga_metadata *metadata) {
  uint8_t serialized[258] = {0};
  size_t size = 0;
  optiga_result ret = optiga_serialize_metadata(metadata, serialized,
                                                sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_serialize_metadata error %d for OID 0x%04x.", ret,
                oid);
    return false;
  }

  optiga_set_data_object(oid, true, serialized, size);

  ret =
      optiga_get_data_object(oid, true, serialized, sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_get_metadata error %d for OID 0x%04x.", ret, oid);
    return false;
  }

  optiga_metadata metadata_stored = {0};
  ret = optiga_parse_metadata(serialized, size, &metadata_stored);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_parse_metadata error %d.", ret);
    return false;
  }

  if (!optiga_compare_metadata(metadata, &metadata_stored)) {
    vcp_println("ERROR optiga_compare_metadata failed.");
    return false;
  }

  return true;
}

void pair_optiga(void) {
  // The pairing key may already be written and locked. The success of the
  // pairing procedure is determined by optiga_sec_chan_handshake(). Therefore
  // it is OK for some of the intermediate operations to fail.

  // Enable writing the pairing secret to OPTIGA.
  optiga_metadata metadata = {0};
  metadata.change = OPTIGA_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;
  metadata.data_type = TYPE_PTFBIND;
  set_metadata(OID_KEY_PAIRING, &metadata);  // Ignore result.

  // Generate pairing secret.
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};
  optiga_result ret = optiga_get_random(secret, sizeof(secret));
  if (OPTIGA_SUCCESS != ret) {
    optiga_pairing_state = OPTIGA_PAIRING_ERR_RNG;
    return;
  }

  // Store pairing secret.
  ret = optiga_set_data_object(OID_KEY_PAIRING, false, secret, sizeof(secret));
  if (OPTIGA_SUCCESS == ret) {
    secret_erase();
    secret_write_header();
    secret_write(secret, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
  }

  // Verify whether the secret was stored correctly in flash and OPTIGA.
  memzero(secret, sizeof(secret));
  if (secret_read(secret, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN) !=
      sectrue) {
    optiga_pairing_state = OPTIGA_PAIRING_ERR_READ;
    return;
  }

  ret = optiga_sec_chan_handshake(secret, sizeof(secret));
  memzero(secret, sizeof(secret));
  if (OPTIGA_SUCCESS != ret) {
    optiga_pairing_state = OPTIGA_PAIRING_ERR_HANDSHAKE;
    return;
  }

  optiga_pairing_state = OPTIGA_PAIRING_PAIRED;
  return;
}

void optiga_lock(void) {
  if (!optiga_paired()) return;

  // Delete trust anchor.
  optiga_result ret =
      optiga_set_data_object(OID_TRUST_ANCHOR, false, (const uint8_t *)"\0", 1);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_set_data error %d for 0x%04x.", ret,
                OID_TRUST_ANCHOR);
    return;
  }

  // Set data object metadata.
  optiga_metadata metadata = {0};

  // Set metadata for device certificate.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;
  if (!set_metadata(OID_CERT_DEV, &metadata)) {
    return;
  }

  // Set metadata for FIDO attestation certificate.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;
  if (!set_metadata(OID_CERT_FIDO, &metadata)) {
    return;
  }

  // Set metadata for device private key.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_NEVER;
  metadata.execute = ACCESS_PAIRED;
  metadata.key_usage = KEY_USE_SIGN;
  if (!set_metadata(OID_KEY_DEV, &metadata)) {
    return;
  }

  // Set metadata for FIDO attestation private key.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_NEVER;
  metadata.execute = ACCESS_PAIRED;
  metadata.key_usage = KEY_USE_SIGN;
  if (!set_metadata(OID_KEY_FIDO, &metadata)) {
    return;
  }

  // Set metadata for pairing key.
  memzero(&metadata, sizeof(metadata));
  metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  metadata.change = OPTIGA_ACCESS_NEVER;
  metadata.read = OPTIGA_ACCESS_NEVER;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;
  metadata.data_type = TYPE_PTFBIND;
  if (!set_metadata(OID_KEY_PAIRING, &metadata)) {
    return;
  }

  vcp_println("OK");
}

optiga_locked_status get_optiga_locked_status(void) {
  if (!optiga_paired()) return OPTIGA_LOCKED_ERROR;

  const uint16_t oids[] = {OID_CERT_DEV, OID_CERT_FIDO, OID_KEY_DEV,
                           OID_KEY_FIDO, OID_KEY_PAIRING};

  optiga_metadata locked_metadata = {0};
  locked_metadata.lcso = OPTIGA_LCS_OPERATIONAL;
  for (size_t i = 0; i < sizeof(oids) / sizeof(oids[0]); ++i) {
    uint8_t metadata_buffer[258] = {0};
    size_t metadata_size = 0;
    optiga_result ret =
        optiga_get_data_object(oids[i], true, metadata_buffer,
                               sizeof(metadata_buffer), &metadata_size);
    if (OPTIGA_SUCCESS != ret) {
      vcp_println("ERROR optiga_get_metadata error %d for OID 0x%04x.", ret,
                  oids[i]);
      return OPTIGA_LOCKED_ERROR;
    }

    optiga_metadata stored_metadata = {0};
    ret =
        optiga_parse_metadata(metadata_buffer, metadata_size, &stored_metadata);
    if (OPTIGA_SUCCESS != ret) {
      vcp_println("ERROR optiga_parse_metadata error %d.", ret);
      return OPTIGA_LOCKED_ERROR;
    }

    if (!optiga_compare_metadata(&locked_metadata, &stored_metadata)) {
      return OPTIGA_LOCKED_FALSE;
    }
  }

  return OPTIGA_LOCKED_TRUE;
}

void check_locked(void) {
  switch (get_optiga_locked_status()) {
    case OPTIGA_LOCKED_TRUE:
      vcp_println("OK YES");
      break;
    case OPTIGA_LOCKED_FALSE:
      vcp_println("OK NO");
      break;
    default:
      // Error reported by get_optiga_locked_status().
      break;
  }
}

void optigaid_read(void) {
  if (!optiga_paired()) return;

  uint8_t optiga_id[27] = {0};
  size_t optiga_id_size = 0;

  optiga_result ret =
      optiga_get_data_object(OPTIGA_OID_COPROC_UID, false, optiga_id,
                             sizeof(optiga_id), &optiga_id_size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_get_data_object error %d for 0x%04x.", ret,
                OPTIGA_OID_COPROC_UID);
    return;
  }

  vcp_print("OK ");
  vcp_println_hex(optiga_id, optiga_id_size);
}

void cert_read(uint16_t oid) {
  if (!optiga_paired()) return;

  static uint8_t cert[2048] = {0};
  size_t cert_size = 0;
  optiga_result ret =
      optiga_get_data_object(oid, false, cert, sizeof(cert), &cert_size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_get_data_object error %d for 0x%04x.", ret, oid);
    return;
  }

  size_t offset = 0;
  if (cert[0] == 0xC0) {
    // TLS identity certificate chain.
    size_t tls_identity_size = (cert[1] << 8) + cert[2];
    size_t cert_chain_size = (cert[3] << 16) + (cert[4] << 8) + cert[5];
    size_t first_cert_size = (cert[6] << 16) + (cert[7] << 8) + cert[8];
    if (tls_identity_size + 3 > cert_size ||
        cert_chain_size + 3 > tls_identity_size ||
        first_cert_size > cert_chain_size) {
      vcp_println("ERROR invalid TLS identity in 0x%04x.", oid);
      return;
    }
    offset = 9;
    cert_size = first_cert_size;
  }

  if (cert_size == 0) {
    vcp_println("ERROR no certificate in 0x%04x.", oid);
    return;
  }

  vcp_print("OK ");
  vcp_println_hex(cert + offset, cert_size);
}

void cert_write(uint16_t oid, char *data) {
  if (!optiga_paired()) return;

  // Enable writing to the certificate slot.
  optiga_metadata metadata = {0};
  metadata.change = OPTIGA_ACCESS_ALWAYS;
  set_metadata(oid, &metadata);  // Ignore result.

  uint8_t data_bytes[1024];

  int len = get_from_hex(data_bytes, sizeof(data_bytes), data);
  if (len < 0) {
    vcp_println("ERROR Hexadecimal decoding error %d.", len);
    return;
  }

  optiga_result ret = optiga_set_data_object(oid, false, data_bytes, len);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_set_data error %d for 0x%04x.", ret, oid);
    return;
  }

  vcp_println("OK");
}

void pubkey_read(uint16_t oid) {
  if (!optiga_paired()) return;

  // Enable key agreement usage.

  optiga_metadata metadata = {0};
  uint8_t key_usage = OPTIGA_KEY_USAGE_KEYAGREE;
  metadata.key_usage.ptr = &key_usage;
  metadata.key_usage.len = 1;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;

  if (!set_metadata(oid, &metadata)) {
    return;
  }

  // Execute ECDH with base point to get the x-coordinate of the public key.
  static const uint8_t BASE_POINT[] = {
      0x03, 0x42, 0x00, 0x04, 0x6b, 0x17, 0xd1, 0xf2, 0xe1, 0x2c, 0x42, 0x47,
      0xf8, 0xbc, 0xe6, 0xe5, 0x63, 0xa4, 0x40, 0xf2, 0x77, 0x03, 0x7d, 0x81,
      0x2d, 0xeb, 0x33, 0xa0, 0xf4, 0xa1, 0x39, 0x45, 0xd8, 0x98, 0xc2, 0x96,
      0x4f, 0xe3, 0x42, 0xe2, 0xfe, 0x1a, 0x7f, 0x9b, 0x8e, 0xe7, 0xeb, 0x4a,
      0x7c, 0x0f, 0x9e, 0x16, 0x2b, 0xce, 0x33, 0x57, 0x6b, 0x31, 0x5e, 0xce,
      0xcb, 0xb6, 0x40, 0x68, 0x37, 0xbf, 0x51, 0xf5};
  uint8_t public_key[32] = {0};
  size_t public_key_size = 0;
  optiga_result ret =
      optiga_calc_ssec(OPTIGA_CURVE_P256, oid, BASE_POINT, sizeof(BASE_POINT),
                       public_key, sizeof(public_key), &public_key_size);
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_calc_ssec error %d.", ret);
    return;
  }

  vcp_print("OK ");
  vcp_println_hex(public_key, public_key_size);
}

void keyfido_write(char *data) {
  if (!optiga_paired()) return;

  const size_t EPH_PUB_KEY_SIZE = 33;
  const size_t PAYLOAD_SIZE = 32;
  const size_t CIPHERTEXT_OFFSET = EPH_PUB_KEY_SIZE;
  const size_t EXPECTED_SIZE = EPH_PUB_KEY_SIZE + PAYLOAD_SIZE;

  // Enable key agreement usage for device key.

  optiga_metadata metadata = {0};
  uint8_t key_usage = OPTIGA_KEY_USAGE_KEYAGREE;
  metadata.key_usage.ptr = &key_usage;
  metadata.key_usage.len = 1;
  metadata.execute = OPTIGA_ACCESS_ALWAYS;

  if (!set_metadata(OID_KEY_DEV, &metadata)) {
    return;
  }

  // Read encrypted FIDO attestation private key.

  uint8_t data_bytes[EXPECTED_SIZE];
  int len = get_from_hex(data_bytes, sizeof(data_bytes), data);
  if (len < 0) {
    vcp_println("ERROR Hexadecimal decoding error %d.", len);
    return;
  }

  if (len != EXPECTED_SIZE) {
    vcp_println("ERROR Unexpected input length.");
    return;
  }

  // Expand sender's ephemeral public key.
  uint8_t public_key[3 + 65] = {0x03, 0x42, 0x00};
  if (ecdsa_uncompress_pubkey(&nist256p1, data_bytes, &public_key[3]) != 1) {
    vcp_println("ERROR Failed to decode public key.");
    return;
  }

  // Execute ECDH with device private key.
  uint8_t secret[32] = {0};
  size_t secret_size = 0;
  optiga_result ret = optiga_calc_ssec(OPTIGA_CURVE_P256, OID_KEY_DEV,
                                       public_key, sizeof(public_key), secret,
                                       sizeof(secret), &secret_size);
  if (OPTIGA_SUCCESS != ret) {
    memzero(secret, sizeof(secret));
    vcp_println("ERROR optiga_calc_ssec error %d.", ret);
    return;
  }

  // Hash the shared secret. Use the result as the decryption key.
  sha256_Raw(secret, secret_size, secret);
  aes_decrypt_ctx ctx = {0};
  AES_RETURN aes_ret = aes_decrypt_key256(secret, &ctx);
  if (EXIT_SUCCESS != aes_ret) {
    vcp_println("ERROR aes_decrypt_key256 error.");
    memzero(&ctx, sizeof(ctx));
    memzero(secret, sizeof(secret));
    return;
  }

  // Decrypt the FIDO attestation key.
  uint8_t fido_key[PAYLOAD_SIZE];

  // The IV is intentionally all-zero, which is not a problem, because the
  // encryption key is unique for each ciphertext.
  uint8_t iv[AES_BLOCK_SIZE] = {0};
  aes_ret = aes_cbc_decrypt(&data_bytes[CIPHERTEXT_OFFSET], fido_key,
                            sizeof(fido_key), iv, &ctx);
  memzero(&ctx, sizeof(ctx));
  memzero(secret, sizeof(secret));
  if (EXIT_SUCCESS != aes_ret) {
    memzero(fido_key, sizeof(fido_key));
    vcp_println("ERROR aes_cbc_decrypt error.");
    return;
  }

  // Write trust anchor certificate to OID 0xE0E8
  ret = optiga_set_trust_anchor();
  if (OPTIGA_SUCCESS != ret) {
    memzero(fido_key, sizeof(fido_key));
    vcp_println("ERROR optiga_set_trust_anchor error %d.", ret);
    return;
  }

  // Set change access condition for the FIDO key to Int(0xE0E8), so that we
  // can write the FIDO key using the trust anchor in OID 0xE0E8.
  memzero(&metadata, sizeof(metadata));
  metadata.change.ptr = (const uint8_t *)"\x21\xe0\xe8";
  metadata.change.len = 3;
  if (!set_metadata(OID_KEY_FIDO, &metadata)) {
    return;
  }

  // Store the FIDO attestation key.
  ret = optiga_set_priv_key(OID_KEY_FIDO, fido_key);
  memzero(fido_key, sizeof(fido_key));
  if (OPTIGA_SUCCESS != ret) {
    vcp_println("ERROR optiga_set_priv_key error %d.", ret);
    return;
  }

  vcp_println("OK");
}
