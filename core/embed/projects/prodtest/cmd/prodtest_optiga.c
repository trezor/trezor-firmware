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

#ifdef USE_OPTIGA

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/optiga_commands.h>
#include <sec/optiga_transport.h>
#include <sec/secret.h>

#include "aes/aes.h"
#include "buffer.h"
#include "der.h"
#include "ecdsa.h"
#include "memzero.h"
#include "nist256p1.h"
#include "rand.h"
#include "sha2.h"

#include "prodtest_optiga.h"

#ifdef USE_STORAGE_HWKEY
#include <sec/secure_aes.h>
#endif

#define OID_CERT_INF (OPTIGA_OID_CERT + 0)
#define OID_CERT_DEV (OPTIGA_OID_CERT + 1)
#define OID_CERT_FIDO (OPTIGA_OID_CERT + 2)
#define OID_KEY_DEV (OPTIGA_OID_ECC_KEY + 0)
#define OID_KEY_FIDO (OPTIGA_OID_ECC_KEY + 2)
#define OID_KEY_PAIRING OPTIGA_OID_PTFBIND_SECRET
#define OID_TRUST_ANCHOR (OPTIGA_OID_CA_CERT + 0)

typedef enum {
  OPTIGA_PAIRING_UNPAIRED = 0,
  OPTIGA_PAIRING_PAIRED,
  OPTIGA_PAIRING_ERR_RNG,
  OPTIGA_PAIRING_ERR_READ_FLASH,
  OPTIGA_PAIRING_ERR_WRITE_FLASH,
  OPTIGA_PAIRING_ERR_WRITE_OPTIGA,
  OPTIGA_PAIRING_ERR_HANDSHAKE1,
  OPTIGA_PAIRING_ERR_HANDSHAKE2,
} optiga_pairing;

static optiga_pairing optiga_pairing_state = OPTIGA_PAIRING_UNPAIRED;

// Data object access conditions.
static const optiga_metadata_item ACCESS_PAIRED =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_CONF, OID_KEY_PAIRING);
static const optiga_metadata_item KEY_USE_SIGN =
    OPTIGA_META_VALUE(OPTIGA_KEY_USAGE_SIGN);
static const optiga_metadata_item TYPE_PTFBIND =
    OPTIGA_META_VALUE(OPTIGA_DATA_TYPE_PTFBIND);

// Identifier of context-specific constructed tag 3, which is used for
// extensions in X.509.
#define DER_X509_EXTENSIONS 0xa3

// Identifier of context-specific primitive tag 0, which is used for
// keyIdentifier in authorityKeyIdentifier.
#define DER_X509_KEY_IDENTIFIER 0x80

// DER-encoded object identifier of the authority key identifier extension
// (id-ce-authorityKeyIdentifier).
const uint8_t OID_AUTHORITY_KEY_IDENTIFIER[] = {0x06, 0x03, 0x55, 0x1d, 0x23};

// forward declaration
static bool check_device_cert_chain(cli_t* cli, const uint8_t* chain,
                                    size_t chain_size);

static bool optiga_paired(cli_t* cli) {
  const char* details = "";

  switch (optiga_pairing_state) {
    case OPTIGA_PAIRING_PAIRED:
      return true;
    case OPTIGA_PAIRING_ERR_RNG:
      details = "optiga_get_random error";
      break;
    case OPTIGA_PAIRING_ERR_READ_FLASH:
      details = "failed to read pairing secret from flash";
      break;
    case OPTIGA_PAIRING_ERR_WRITE_FLASH:
      details = "failed to write pairing secret to flash";
      break;
    case OPTIGA_PAIRING_ERR_WRITE_OPTIGA:
      details = "failed to write pairing secret to Optiga";
      break;
    case OPTIGA_PAIRING_ERR_HANDSHAKE1:
      details = "failed optiga_sec_chan_handshake 1";
      break;
    case OPTIGA_PAIRING_ERR_HANDSHAKE2:
      details = "failed optiga_sec_chan_handshake 2";
      break;
    default:
      break;
  }

  cli_error(cli, CLI_ERROR, "Optiga not paired (%s).", details);
  return false;
}

static bool set_metadata(cli_t* cli, uint16_t oid,
                         const optiga_metadata* metadata, bool report_error) {
  uint8_t serialized[OPTIGA_MAX_METADATA_SIZE] = {0};
  size_t size = 0;
  optiga_result ret = optiga_serialize_metadata(metadata, serialized,
                                                sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    if (report_error) {
      cli_error(cli, CLI_ERROR,
                "optiga_serialize_metadata error %d for OID 0x%04x.", ret, oid);
    }
    return false;
  }

  optiga_set_data_object(oid, true, serialized, size);

  ret =
      optiga_get_data_object(oid, true, serialized, sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    if (report_error) {
      cli_error(cli, CLI_ERROR, "optiga_get_metadata error %d for OID 0x%04x.",
                ret, oid);
    }
    return false;
  }

  optiga_metadata metadata_stored = {0};
  ret = optiga_parse_metadata(serialized, size, &metadata_stored);
  if (OPTIGA_SUCCESS != ret) {
    if (report_error) {
      cli_error(cli, CLI_ERROR, "optiga_parse_metadata error %d.", ret);
    }
    return false;
  }

  if (!optiga_compare_metadata(metadata, &metadata_stored)) {
    if (report_error) {
      cli_error(cli, CLI_ERROR, "optiga_compare_metadata failed.");
    }
    return false;
  }

  return true;
}

void pair_optiga(cli_t* cli) {
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};

  if (secret_optiga_get(secret) != sectrue) {
    if (secret_optiga_writable() != sectrue) {
      // optiga pairing secret is unwritable, so fail
      optiga_pairing_state = OPTIGA_PAIRING_ERR_WRITE_FLASH;
      return;
    }

    // Generate the pairing secret.
    if (OPTIGA_SUCCESS != optiga_get_random(secret, sizeof(secret))) {
      optiga_pairing_state = OPTIGA_PAIRING_ERR_RNG;
      return;
    }
    random_xor(secret, sizeof(secret));

    // Enable writing the pairing secret to OPTIGA.
    optiga_metadata metadata = {0};
    metadata.change = OPTIGA_META_ACCESS_ALWAYS;
    metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
    metadata.data_type = TYPE_PTFBIND;
    (void)set_metadata(cli, OID_KEY_PAIRING, &metadata,
                       false);  // Ignore result.

    // Store the pairing secret in OPTIGA.
    if (OPTIGA_SUCCESS != optiga_set_data_object(OID_KEY_PAIRING, false, secret,
                                                 sizeof(secret))) {
      optiga_pairing_state = OPTIGA_PAIRING_ERR_WRITE_OPTIGA;
      return;
    }

    // Execute the handshake to verify that the secret was stored correctly in
    // Optiga.
    if (OPTIGA_SUCCESS != optiga_sec_chan_handshake(secret, sizeof(secret))) {
      optiga_pairing_state = OPTIGA_PAIRING_ERR_HANDSHAKE1;
      return;
    }

    // Store the pairing secret in the flash memory.
    if (sectrue != secret_optiga_set(secret)) {
      optiga_pairing_state = OPTIGA_PAIRING_ERR_WRITE_FLASH;
      return;
    }

    // Reload the pairing secret from the flash memory.
    memzero(secret, sizeof(secret));
    if (sectrue != secret_optiga_get(secret)) {
      optiga_pairing_state = OPTIGA_PAIRING_ERR_READ_FLASH;
      return;
    }
  }

  // Execute the handshake to verify that the secret is stored correctly in both
  // Optiga and MCU flash.
  optiga_result ret = optiga_sec_chan_handshake(secret, sizeof(secret));
  memzero(secret, sizeof(secret));
  if (OPTIGA_SUCCESS != ret) {
    optiga_pairing_state = OPTIGA_PAIRING_ERR_HANDSHAKE2;
    return;
  }

  optiga_pairing_state = OPTIGA_PAIRING_PAIRED;
  return;
}

#if PRODUCTION
#define METADATA_SET_LOCKED(metadata) \
  { metadata.lcso = OPTIGA_META_LCS_OPERATIONAL; }
#else
#define METADATA_SET_LOCKED(metadata)
#endif

static void prodtest_optiga_lock(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!optiga_paired(cli)) return;

  // Delete trust anchor.
  optiga_result ret =
      optiga_set_data_object(OID_TRUST_ANCHOR, false, (const uint8_t*)"\0", 1);
  if (OPTIGA_SUCCESS != ret) {
    cli_error(cli, CLI_ERROR, "optiga_set_data error %d for 0x%04x.", ret,
              OID_TRUST_ANCHOR);
    return;
  }

  // Set data object metadata.
  optiga_metadata metadata = {0};

  // Set metadata for device certificate.
  memzero(&metadata, sizeof(metadata));
  METADATA_SET_LOCKED(metadata);
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!set_metadata(cli, OID_CERT_DEV, &metadata, true)) {
    return;
  }

  // Set metadata for FIDO attestation certificate.
  memzero(&metadata, sizeof(metadata));
  METADATA_SET_LOCKED(metadata);
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!set_metadata(cli, OID_CERT_FIDO, &metadata, true)) {
    return;
  }

  // Set metadata for device private key.
  memzero(&metadata, sizeof(metadata));
  METADATA_SET_LOCKED(metadata);
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PAIRED;
  metadata.key_usage = KEY_USE_SIGN;
  if (!set_metadata(cli, OID_KEY_DEV, &metadata, true)) {
    return;
  }

  // Set metadata for FIDO attestation private key.
  memzero(&metadata, sizeof(metadata));
  METADATA_SET_LOCKED(metadata);
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PAIRED;
  metadata.key_usage = KEY_USE_SIGN;
  if (!set_metadata(cli, OID_KEY_FIDO, &metadata, true)) {
    return;
  }

  // Set metadata for pairing key.
  memzero(&metadata, sizeof(metadata));
  METADATA_SET_LOCKED(metadata);
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  metadata.data_type = TYPE_PTFBIND;
  if (!set_metadata(cli, OID_KEY_PAIRING, &metadata, true)) {
    return;
  }

  cli_ok(cli, "");
}

optiga_locked_status get_optiga_locked_status(cli_t* cli) {
  if (!optiga_paired(cli)) return OPTIGA_LOCKED_ERROR;

  const uint16_t oids[] = {OID_CERT_DEV, OID_CERT_FIDO, OID_KEY_DEV,
                           OID_KEY_FIDO, OID_KEY_PAIRING};

  optiga_metadata locked_metadata = {0};
  locked_metadata.lcso = OPTIGA_META_LCS_OPERATIONAL;
  for (size_t i = 0; i < sizeof(oids) / sizeof(oids[0]); ++i) {
    uint8_t metadata_buffer[OPTIGA_MAX_METADATA_SIZE] = {0};
    size_t metadata_size = 0;
    optiga_result ret =
        optiga_get_data_object(oids[i], true, metadata_buffer,
                               sizeof(metadata_buffer), &metadata_size);
    if (OPTIGA_SUCCESS != ret) {
      cli_error(cli, CLI_ERROR, "optiga_get_metadata error %d for OID 0x%04x.",
                ret, oids[i]);
      return OPTIGA_LOCKED_ERROR;
    }

    optiga_metadata stored_metadata = {0};
    ret =
        optiga_parse_metadata(metadata_buffer, metadata_size, &stored_metadata);
    if (OPTIGA_SUCCESS != ret) {
      cli_error(cli, CLI_ERROR, "optiga_parse_metadata error %d.", ret);
      return OPTIGA_LOCKED_ERROR;
    }

    if (!optiga_compare_metadata(&locked_metadata, &stored_metadata)) {
      return OPTIGA_LOCKED_FALSE;
    }
  }

  return OPTIGA_LOCKED_TRUE;
}

static void prodtest_optiga_lock_check(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  switch (get_optiga_locked_status(cli)) {
    case OPTIGA_LOCKED_TRUE:
      cli_ok(cli, "YES");
      break;
    case OPTIGA_LOCKED_FALSE:
      cli_ok(cli, "NO");
      break;
    default:
      // Error reported by get_optiga_locked_status().
      break;
  }
}

static void prodtest_optiga_id_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!optiga_paired(cli)) return;

  uint8_t optiga_id[27] = {0};
  size_t optiga_id_size = 0;

  optiga_result ret =
      optiga_get_data_object(OPTIGA_OID_COPROC_UID, false, optiga_id,
                             sizeof(optiga_id), &optiga_id_size);
  if (OPTIGA_SUCCESS != ret) {
    cli_error(cli, CLI_ERROR, "optiga_get_data_object error %d for 0x%04x.",
              ret, OPTIGA_OID_COPROC_UID);
    return;
  }

  cli_ok_hexdata(cli, optiga_id, optiga_id_size);
}

static void cert_read(cli_t* cli, uint16_t oid) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!optiga_paired(cli)) return;

  static uint8_t cert[OPTIGA_MAX_CERT_SIZE] = {0};
  size_t cert_size = 0;
  optiga_result ret =
      optiga_get_data_object(oid, false, cert, sizeof(cert), &cert_size);
  if (OPTIGA_SUCCESS != ret) {
    cli_error(cli, CLI_ERROR, "optiga_get_data_object error %d for 0x%04x.",
              ret, oid);
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
      cli_error(cli, CLI_ERROR, "invalid TLS identity in 0x%04x.", oid);
      return;
    }
    offset = 9;
    cert_size = first_cert_size;
  }

  if (cert_size == 0) {
    cli_error(cli, CLI_ERROR, "no certificate in 0x%04x.", oid);
    return;
  }

  cli_ok_hexdata(cli, cert + offset, cert_size);
}

static void cert_write(cli_t* cli, uint16_t oid) {
  if (!optiga_paired(cli)) return;

  // Enable writing to the certificate slot.
  optiga_metadata metadata = {0};
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  set_metadata(cli, oid, &metadata, false);  // Ignore result.

  size_t len = 0;
  uint8_t data_bytes[OPTIGA_MAX_CERT_SIZE];

  if (!cli_arg_hex(cli, "hex-data", data_bytes, sizeof(data_bytes), &len)) {
    if (len == sizeof(data_bytes)) {
      cli_error(cli, CLI_ERROR, "Certificate too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  optiga_result ret = optiga_set_data_object(oid, false, data_bytes, len);
  if (OPTIGA_SUCCESS != ret) {
    cli_error(cli, CLI_ERROR, "optiga_set_data error %d for 0x%04x.", ret, oid);
    return;
  }

  // Verify that the certificate was written correctly.
  static uint8_t cert[OPTIGA_MAX_CERT_SIZE] = {0};
  size_t cert_size = 0;
  ret = optiga_get_data_object(oid, false, cert, sizeof(cert), &cert_size);
  if (OPTIGA_SUCCESS != ret || cert_size != len ||
      memcmp(data_bytes, cert, len) != 0) {
    cli_error(cli, CLI_ERROR, "optiga_get_data_object error %d for 0x%04x.",
              ret, oid);
    return;
  }

  if (oid == OID_CERT_DEV && !check_device_cert_chain(cli, cert, cert_size)) {
    // Error returned by check_device_cert_chain().
    return;
  }

  cli_ok(cli, "");
}

static void pubkey_read(cli_t* cli, uint16_t oid) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!optiga_paired(cli)) return;

  // Enable key agreement usage.

  optiga_metadata metadata = {0};
  metadata.key_usage = OPTIGA_META_KEY_USE_KEYAGREE;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;

  if (!set_metadata(cli, oid, &metadata, true)) {
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
    cli_error(cli, CLI_ERROR, "optiga_calc_ssec error %d.", ret);
    return;
  }

  cli_ok_hexdata(cli, public_key, public_key_size);
}

static void prodtest_optiga_keyfido_write(cli_t* cli) {
  if (!optiga_paired(cli)) return;

  const size_t EPH_PUB_KEY_SIZE = 33;
  const size_t PAYLOAD_SIZE = 32;
  const size_t CIPHERTEXT_OFFSET = EPH_PUB_KEY_SIZE;
  const size_t EXPECTED_SIZE = EPH_PUB_KEY_SIZE + PAYLOAD_SIZE;

  // Enable key agreement usage for device key.

  optiga_metadata metadata = {0};
  metadata.key_usage = OPTIGA_META_KEY_USE_KEYAGREE;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;

  if (!set_metadata(cli, OID_KEY_DEV, &metadata, true)) {
    return;
  }

  // Read encrypted FIDO attestation private key.

  uint8_t data_bytes[EXPECTED_SIZE];
  size_t len = 0;

  if (!cli_arg_hex(cli, "hex-data", data_bytes, sizeof(data_bytes), &len)) {
    if (len == sizeof(data_bytes)) {
      cli_error(cli, CLI_ERROR, "Key too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (len != EXPECTED_SIZE) {
    cli_error(cli, CLI_ERROR, "Unexpected input length.");
    return;
  }

  // Expand sender's ephemeral public key.
  uint8_t public_key[3 + 65] = {0x03, 0x42, 0x00};
  if (ecdsa_uncompress_pubkey(&nist256p1, data_bytes, &public_key[3]) != 1) {
    cli_error(cli, CLI_ERROR, "Failed to decode public key.");
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
    cli_error(cli, CLI_ERROR, "optiga_calc_ssec error %d.", ret);
    return;
  }

  // Hash the shared secret. Use the result as the decryption key.
  sha256_Raw(secret, secret_size, secret);
  aes_decrypt_ctx ctx = {0};
  AES_RETURN aes_ret = aes_decrypt_key256(secret, &ctx);
  if (EXIT_SUCCESS != aes_ret) {
    cli_error(cli, CLI_ERROR, "aes_decrypt_key256 error.");
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
    cli_error(cli, CLI_ERROR, "aes_cbc_decrypt error.");
    return;
  }

  // Set the data type of OID 0xE0E8 to trust anchor, so that we can use it to
  // write the FIDO key.
  memzero(&metadata, sizeof(metadata));
  metadata.data_type = OPTIGA_META_VALUE(OPTIGA_DATA_TYPE_TA);
  if (!set_metadata(cli, OID_TRUST_ANCHOR, &metadata, true)) {
    return;
  }

  // Write trust anchor certificate to OID 0xE0E8
  ret = optiga_set_trust_anchor();
  if (OPTIGA_SUCCESS != ret) {
    memzero(fido_key, sizeof(fido_key));
    cli_error(cli, CLI_ERROR, "optiga_set_trust_anchor error %d.", ret);
    return;
  }

  // Set change access condition for the FIDO key to Int(0xE0E8), so that we
  // can write the FIDO key using the trust anchor in OID 0xE0E8.
  memzero(&metadata, sizeof(metadata));
  metadata.change =
      OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_INT, OID_TRUST_ANCHOR);
  metadata.version = OPTIGA_META_VERSION_DEFAULT;
  if (!set_metadata(cli, OID_KEY_FIDO, &metadata, true)) {
    return;
  }

  // Store the FIDO attestation key.
  ret = optiga_set_priv_key(OID_KEY_FIDO, fido_key);
  memzero(fido_key, sizeof(fido_key));
  if (OPTIGA_SUCCESS != ret) {
    cli_error(cli, CLI_ERROR, "optiga_set_priv_key error %d.", ret);
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_optiga_counter_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!optiga_paired(cli)) return;

  uint8_t sec = 0;
  size_t size = 0;

  optiga_result ret =
      optiga_get_data_object(OPTIGA_OID_SEC, false, &sec, sizeof(sec), &size);
  if (OPTIGA_SUCCESS != ret || sizeof(sec) != size) {
    cli_error(cli, CLI_ERROR, "optiga_get_data_object error %d for 0x%04x.",
              ret, OPTIGA_OID_SEC);
    return;
  }

  cli_ok_hexdata(cli, &sec, sizeof(sec));
}

// clang-format off
static const uint8_t ECDSA_WITH_SHA256[] = {
  0x30, 0x0a, // a sequence of 10 bytes
    0x06, 0x08, // an OID of 8 bytes
      0x2a, 0x86, 0x48, 0xce, 0x3d, 0x04, 0x03, 0x02,
};
// clang-format on

static bool get_cert_extensions(DER_ITEM* tbs_cert, DER_ITEM* extensions) {
  // Find the certificate extensions in the tbsCertificate.
  DER_ITEM cert_item = {0};
  while (der_read_item(&tbs_cert->buf, &cert_item)) {
    if (cert_item.id == DER_X509_EXTENSIONS) {
      // Open the extensions sequence.
      return der_read_item(&cert_item.buf, extensions) &&
             extensions->id == DER_SEQUENCE;
    }
  }
  return false;
}

static bool get_extension_value(const uint8_t* extension_oid,
                                size_t extension_oid_size, DER_ITEM* extensions,
                                DER_ITEM* extension_value) {
  // Find the extension with the given OID.
  DER_ITEM extension = {0};
  while (der_read_item(&extensions->buf, &extension)) {
    DER_ITEM extension_id = {0};
    if (der_read_item(&extension.buf, &extension_id) &&
        extension_id.buf.size == extension_oid_size &&
        memcmp(extension_id.buf.data, extension_oid, extension_oid_size) == 0) {
      // Find the extension's extnValue, skipping the optional critical flag.
      while (der_read_item(&extension.buf, extension_value)) {
        if (extension_value->id == DER_OCTET_STRING) {
          return true;
        }
      }
      memzero(extension_value, sizeof(DER_ITEM));
      return false;
    }
  }
  return false;
}

static bool get_authority_key_digest(cli_t* cli, DER_ITEM* tbs_cert,
                                     const uint8_t** authority_key_digest) {
  DER_ITEM extensions = {0};
  if (!get_cert_extensions(tbs_cert, &extensions)) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, extensions not found.");
    return false;
  }

  // Find the authority key identifier extension's extnValue.
  DER_ITEM extension_value = {0};
  if (!get_extension_value(OID_AUTHORITY_KEY_IDENTIFIER,
                           sizeof(OID_AUTHORITY_KEY_IDENTIFIER), &extensions,
                           &extension_value)) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, authority key identifier extension "
              "not found.");
    return false;
  }

  // Open the AuthorityKeyIdentifier sequence.
  DER_ITEM auth_key_id = {0};
  if (!der_read_item(&extension_value.buf, &auth_key_id) ||
      auth_key_id.id != DER_SEQUENCE) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, failed to open authority key "
              "identifier extnValue.");
    return false;
  }

  // Find the keyIdentifier field.
  DER_ITEM key_id = {0};
  if (!der_read_item(&auth_key_id.buf, &key_id) ||
      key_id.id != DER_X509_KEY_IDENTIFIER) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, failed to find keyIdentifier field.");
    return false;
  }

  // Return the pointer to the keyIdentifier data.
  if (buffer_remaining(&key_id.buf) != SHA1_DIGEST_LENGTH ||
      !buffer_ptr(&key_id.buf, authority_key_digest)) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, invalid length of keyIdentifier.");
    return false;
  }

  return true;
}

static bool check_device_cert_chain(cli_t* cli, const uint8_t* chain,
                                    size_t chain_size) {
  // Checks the integrity of the device certificate chain to ensure that the
  // certificate data was not corrupted in transport and that the device
  // certificate belongs to this device. THIS IS NOT A FULL VERIFICATION OF THE
  // CERTIFICATE CHAIN.

  // Enable signing with the device private key.
  optiga_metadata metadata = {0};
  metadata.key_usage = KEY_USE_SIGN;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!set_metadata(cli, OID_KEY_DEV, &metadata, true)) {
    return false;
  }

  // Generate a P-256 signature using the device private key.
  uint8_t digest[SHA256_DIGEST_LENGTH] = {1};
  uint8_t der_sig[72] = {DER_SEQUENCE};
  size_t der_sig_size = 0;
  if (optiga_calc_sign(OID_KEY_DEV, digest, sizeof(digest), &der_sig[2],
                       sizeof(der_sig) - 2, &der_sig_size) != OPTIGA_SUCCESS) {
    cli_error(cli, CLI_ERROR, "check_device_cert_chain, optiga_calc_sign.");
    return false;
  }
  der_sig[1] = der_sig_size;

  uint8_t sig[64] = {0};
  if (ecdsa_sig_from_der(der_sig, der_sig_size + 2, sig) != 0) {
    cli_error(cli, CLI_ERROR, "check_device_cert_chain, ecdsa_sig_from_der.");
    return false;
  }

  // This will be populated with a pointer to the key identifier data of the
  // AuthorityKeyIdentifier extension from the last certificate in the chain.
  const uint8_t* authority_key_digest = NULL;

  BUFFER_READER chain_reader = {0};
  buffer_reader_init(&chain_reader, chain, chain_size);
  int cert_count = 0;
  while (buffer_remaining(&chain_reader) > 0) {
    // Read the next certificate in the chain.
    cert_count += 1;
    DER_ITEM cert = {0};
    if (!der_read_item(&chain_reader, &cert) || cert.id != DER_SEQUENCE) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 1, cert %d.",
                cert_count);
      return false;
    }

    // Read the tbsCertificate.
    DER_ITEM tbs_cert = {0};
    if (!der_read_item(&cert.buf, &tbs_cert)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 2, cert %d.",
                cert_count);
      return false;
    }

    // Read the Subject Public Key Info.
    DER_ITEM pub_key_info = {0};
    for (int i = 0; i < 7; ++i) {
      if (!der_read_item(&tbs_cert.buf, &pub_key_info)) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, der_read_item 3, cert %d.",
                  cert_count);
        return false;
      }
    }

    // Read the public key.
    DER_ITEM pub_key = {0};
    uint8_t unused_bits = 0;
    const uint8_t* pub_key_bytes = NULL;
    for (int i = 0; i < 2; ++i) {
      if (!der_read_item(&pub_key_info.buf, &pub_key)) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, der_read_item 4, cert %d.",
                  cert_count);
        return false;
      }
    }

    if (!buffer_get(&pub_key.buf, &unused_bits) ||
        buffer_remaining(&pub_key.buf) != 65 ||
        !buffer_ptr(&pub_key.buf, &pub_key_bytes)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, reading public key, cert %d.",
                cert_count);
      return false;
    }

    // Verify the previous signature.
    if (ecdsa_verify_digest(&nist256p1, pub_key_bytes, sig, digest) != 0) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, ecdsa_verify_digest, cert %d.",
                cert_count);
      return false;
    }

    // Get the authority key identifier from the last certificate.
    if (buffer_remaining(&chain_reader) == 0 &&
        !get_authority_key_digest(cli, &tbs_cert, &authority_key_digest)) {
      // Error returned by get_authority_key_digest().
      return false;
    }

    // Prepare the hash of tbsCertificate for the next signature verification.
    sha256_Raw(tbs_cert.buf.data, tbs_cert.buf.size, digest);

    // Read the signatureAlgorithm and ensure it matches ECDSA_WITH_SHA256.
    DER_ITEM sig_alg = {0};
    if (!der_read_item(&cert.buf, &sig_alg) ||
        sig_alg.buf.size != sizeof(ECDSA_WITH_SHA256) ||
        memcmp(ECDSA_WITH_SHA256, sig_alg.buf.data,
               sizeof(ECDSA_WITH_SHA256)) != 0) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, checking signatureAlgorithm, cert "
                "%d.",
                cert_count);
      return false;
    }

    // Read the signatureValue.
    DER_ITEM sig_val = {0};
    if (!der_read_item(&cert.buf, &sig_val) || sig_val.id != DER_BIT_STRING ||
        !buffer_get(&sig_val.buf, &unused_bits) || unused_bits != 0) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, reading signatureValue, cert %d.",
                cert_count);
      return false;
    }

    // Extract the signature for the next signature verification.
    const uint8_t* sig_bytes = NULL;
    if (!buffer_ptr(&sig_val.buf, &sig_bytes) ||
        ecdsa_sig_from_der(sig_bytes, buffer_remaining(&sig_val.buf), sig) !=
            0) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, ecdsa_sig_from_der, cert %d.",
                cert_count);
      return false;
    }
  }

  // Verify that the signature of the last certificate in the chain matches its
  // own AuthorityKeyIdentifier to verify the integrity of the certificate data.
  uint8_t pub_key[65] = {0};
  uint8_t pub_key_digest[SHA1_DIGEST_LENGTH] = {0};
  for (int recid = 0; recid < 4; ++recid) {
    if (ecdsa_recover_pub_from_sig(&nist256p1, pub_key, sig, digest, recid) ==
        0) {
      sha1_Raw(pub_key, sizeof(pub_key), pub_key_digest);
      if (memcmp(authority_key_digest, pub_key_digest,
                 sizeof(pub_key_digest)) == 0) {
        return true;
      }
    }
  }

  cli_error(cli, CLI_ERROR,
            "check_device_cert_chain, ecdsa_verify_digest root.");
  return false;
}

static void prodtest_optiga_certinf_read(cli_t* cli) {
  cert_read(cli, OID_CERT_INF);
}

static void prodtest_optiga_certdev_read(cli_t* cli) {
  cert_read(cli, OID_CERT_DEV);
}

static void prodtest_optiga_certdev_write(cli_t* cli) {
  cert_write(cli, OID_CERT_DEV);
}

static void prodtest_optiga_certfido_read(cli_t* cli) {
  cert_read(cli, OID_CERT_FIDO);
}

static void prodtest_optiga_certfido_write(cli_t* cli) {
  cert_write(cli, OID_CERT_FIDO);
}

static void prodtest_optiga_keyfido_read(cli_t* cli) {
  pubkey_read(cli, OID_KEY_FIDO);
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "optiga-id-read",
  .func = prodtest_optiga_id_read,
  .info = "Retrieve the unique ID of the Optiga chip",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "optiga-certinf-read",
  .func = prodtest_optiga_certinf_read,
  .info = "Read the X.509 certificate issued by Infineon",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "optiga-certdev-read",
  .func = prodtest_optiga_certdev_read,
  .info = "Read the device's X.509 certificate",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "optiga-certdev-write",
  .func = prodtest_optiga_certdev_write,
  .info = "Write the device's X.509 certificate",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "optiga-certfido-read",
  .func = prodtest_optiga_certfido_read,
  .info = "Read the X.509 certificate for the FIDO key",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "optiga-certfido-write",
  .func = prodtest_optiga_certfido_write,
  .info = "Write the X.509 certificate for the FIDO key",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "optiga-keyfido-read",
  .func = prodtest_optiga_keyfido_read,
  .info = "Read the x-coordinate of the FIDO public key.",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "optiga-keyfido-write",
  .func = prodtest_optiga_keyfido_write,
  .info = "Write the FIDO private key",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "optiga-lock",
  .func = prodtest_optiga_lock,
  .info = "Lock Optiga's data objects containing provisioning data",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "optiga-lock-check",
  .func = prodtest_optiga_lock_check,
  .info = "Check whether Optiga's data objects are locked",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "optiga-counter-read",
  .func = prodtest_optiga_counter_read,
  .info = "Read the Optiga security event counter",
  .args = ""
);

#endif  // USE_OPTIGA
