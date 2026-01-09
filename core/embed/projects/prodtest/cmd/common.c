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

#include <sec/unit_properties.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include "common.h"

#include "buffer.h"
#include "der.h"
#include "ecdsa.h"
#include "ed25519-donna/ed25519.h"
#include "hsm_keys.h"
#include "memzero.h"
#include "nist256p1.h"
#include "sha2.h"
#include "string.h"

#include <../vendor/mldsa-native/mldsa/sign.h>

// HSM root certification authority public keys.
const uint8_t ROOT_KEYS_P256[][ECDSA_PUBLIC_KEY_SIZE] = {
#if PRODUCTION
#ifdef DEV_AUTH_ROOT_PROD_P256
    DEV_AUTH_ROOT_PROD_P256,
#endif
#ifdef DEV_AUTH_ROOT_PROD_BACKUP_P256
    DEV_AUTH_ROOT_PROD_BACKUP_P256,
#endif
#else
#ifdef DEV_AUTH_ROOT_DEBUG_P256
    DEV_AUTH_ROOT_DEBUG_P256,
#endif
#ifdef DEV_AUTH_ROOT_STAGING_P256
    DEV_AUTH_ROOT_STAGING_P256,
#endif
#endif
};

const ed25519_public_key ROOT_KEYS_ED25519[] = {
#if PRODUCTION
#ifdef DEV_AUTH_ROOT_PROD_ED25519
    DEV_AUTH_ROOT_PROD_ED25519,
#endif
#ifdef DEV_AUTH_ROOT_PROD_BACKUP_ED25519
    DEV_AUTH_ROOT_PROD_BACKUP_ED25519,
#endif
#else
#ifdef DEV_AUTH_ROOT_DEBUG_ED25519
    DEV_AUTH_ROOT_DEBUG_ED25519,
#endif
#ifdef DEV_AUTH_ROOT_STAGING_ED25519
    DEV_AUTH_ROOT_STAGING_ED25519,
#endif
#endif
};

const uint8_t ROOT_KEYS_MLDSA44[][CRYPTO_PUBLICKEYBYTES] = {
#if PRODUCTION
#ifdef DEV_AUTH_ROOT_PROD_MLDSA44
    DEV_AUTH_ROOT_PROD_MLDSA44,
#endif
#ifdef DEV_AUTH_ROOT_PROD_BACKUP_MLDSA44
    DEV_AUTH_ROOT_PROD_BACKUP_MLDSA44,
#endif
#else
#ifdef DEV_AUTH_ROOT_DEBUG_MLDSA44
    DEV_AUTH_ROOT_DEBUG_MLDSA44,
#endif
#ifdef DEV_AUTH_ROOT_STAGING_MLDSA44
    DEV_AUTH_ROOT_STAGING_MLDSA44,
#endif
#endif
};

// Identifier of context-specific constructed tag 3, which is used for
// extensions in X.509.
#define DER_X509_EXTENSIONS 0xa3

// Identifier of context-specific primitive tag 0, which is used for
// keyIdentifier in authorityKeyIdentifier.
#define DER_X509_KEY_IDENTIFIER 0x80

// DER-encoded object identifier of the authority key identifier extension
// (id-ce-authorityKeyIdentifier).
const uint8_t OID_AUTHORITY_KEY_IDENTIFIER[] = {0x06, 0x03, 0x55, 0x1d, 0x23};

// clang-format off
static const uint8_t ECDSA_P256_WITH_SHA256[] = {
  0x30, 0x13, // a sequence of 19 bytes
    0x06, 0x07, // an OID of 7 bytes
      0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01, // corresponds to ecPublicKey in X.509
    0x06, 0x08, // an OID of 8 bytes
      0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07, // corresponds to prime256v1 in X.509
};

static const uint8_t EDDSA_25519[] = {
  0x30, 0x05, // a sequence of 5 bytes
    0x06, 0x03, // an OID of 3 bytes
      0x2b, 0x65, 0x70, // corresponds to EdDSA 25519 in X.509
};

static const uint8_t MLDSA44[] = {
  0x30, 0x0b, // a sequence of 11 bytes
    0x06, 0x09, // an OID of 9 bytes
      0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x03, 0x11, // corresponds to id-ml-dsa-44 in X.509
};

static const uint8_t OID_COMMON_NAME[] = {
  0x06, 0x03, // an OID of 3 bytes
    0x55, 0x04, 0x03, // corresponds to commonName in X.509
};

#if !(defined TREZOR_MODEL_T3B1 || defined TREZOR_MODEL_T3T1)
static const uint8_t OID_SERIAL_NUMBER[] = {
  0x06, 0x03, // an OID of 3 bytes
    0x55, 0x04, 0x05, // corresponds to serialNumber in X.509
};
#endif

static const uint8_t SUBJECT_COMMON_NAME[] = {
#ifdef TREZOR_MODEL_T2B1
  'T', '2', 'B', '1', ' ', 'T', 'r', 'e', 'z', 'o', 'r', ' ', 'S', 'a', 'f', 'e', ' ', '3',
#endif
#ifdef TREZOR_MODEL_T3B1
  'T', '3', 'B', '1', ' ', 'T', 'r', 'e', 'z', 'o', 'r', ' ', 'S', 'a', 'f', 'e', ' ', '3',
#endif
#ifdef TREZOR_MODEL_T3T1
  'T', '3', 'T', '1', ' ', 'T', 'r', 'e', 'z', 'o', 'r', ' ', 'S', 'a', 'f', 'e', ' ', '5',
#endif
#ifdef TREZOR_MODEL_T3W1
  'T', '3', 'W', '1', ' ', 'T', 'r', 'e', 'z', 'o', 'r', ' ', 'S', 'a', 'f', 'e', ' ', '7',
#endif
};
// clang-format on

typedef enum {
  ALG_ID_ECDSA_P256_WITH_SHA256,
  ALG_ID_EDDSA_25519,
  ALG_ID_MLDSA44
} alg_id_t;

static bool get_algorithm(DER_ITEM* alg, alg_id_t* alg_id) {
  if (alg->buf.size == sizeof(ECDSA_P256_WITH_SHA256) &&
      memcmp(alg->buf.data, ECDSA_P256_WITH_SHA256,
             sizeof(ECDSA_P256_WITH_SHA256)) == 0) {
    *alg_id = ALG_ID_ECDSA_P256_WITH_SHA256;
    return true;
  }

  if (alg->buf.size == sizeof(EDDSA_25519) &&
      memcmp(alg->buf.data, EDDSA_25519, sizeof(EDDSA_25519)) == 0) {
    *alg_id = ALG_ID_EDDSA_25519;
    return true;
  }

  if (alg->buf.size == sizeof(MLDSA44) &&
      memcmp(alg->buf.data, MLDSA44, sizeof(MLDSA44)) == 0) {
    *alg_id = ALG_ID_MLDSA44;
    return true;
  }

  return false;
}

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

static bool get_name_attribute(DER_ITEM* name, const uint8_t* type,
                               size_t type_size, const uint8_t** value,
                               size_t* value_size) {
  if (name->id != DER_SEQUENCE) {
    return false;
  }

  DER_ITEM relative_distinguished_name = {0};
  while (der_read_item(&name->buf, &relative_distinguished_name)) {
    if (relative_distinguished_name.id != DER_SET) {
      return false;
    }

    DER_ITEM attribute = {0};
    if (!der_read_item(&relative_distinguished_name.buf, &attribute) ||
        attribute.id != DER_SEQUENCE) {
      return false;
    }

    DER_ITEM attribute_type = {0};
    if (!der_read_item(&attribute.buf, &attribute_type)) {
      return false;
    }

    if (attribute_type.buf.size != type_size ||
        memcmp(attribute_type.buf.data, type, type_size) != 0) {
      continue;
    }

    DER_ITEM attribute_value = {0};
    if (!der_read_item(&attribute.buf, &attribute_value) ||
        (attribute_value.id != DER_UTF8_STRING &&
         attribute_value.id != DER_PRINTABLE_STRING)) {
      return false;
    }

    if (!buffer_ptr(&attribute_value.buf, value)) {
      return false;
    }
    *value_size = buffer_remaining(&attribute_value.buf);
    return true;
  }

  // Attribute not found.
  return false;
}

static bool verify_signature(alg_id_t alg_id, const uint8_t* pub_key,
                             size_t pub_key_size, const uint8_t* sig,
                             size_t sig_size, const uint8_t* msg,
                             size_t msg_size) {
  if (alg_id == ALG_ID_ECDSA_P256_WITH_SHA256) {
    if (pub_key_size != 65) {
      return false;
    }

    uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
    sha256_Raw(msg, msg_size, digest);

    uint8_t decoded_sig[64] = {0};
    if (ecdsa_sig_from_der(sig, sig_size, decoded_sig) != 0) {
      return false;
    }

    if (ecdsa_verify_digest(&nist256p1, pub_key, decoded_sig, digest) != 0) {
      return false;
    }

    return true;
  }

  if (alg_id == ALG_ID_EDDSA_25519) {
    if (pub_key_size != 32 || sig_size != 64) {
      return false;
    }

    if (ed25519_sign_open(msg, msg_size, pub_key, sig) != 0) {
      return false;
    }

    return true;
  }

  if (alg_id == ALG_ID_MLDSA44) {
    if (pub_key_size != CRYPTO_PUBLICKEYBYTES) {
      return false;
    }

    if (crypto_sign_verify(sig, sig_size, msg, msg_size, (const uint8_t*)"", 0,
                           pub_key) != 0) {
      return false;
    }

    return true;
  }

  return false;
}

static bool get_root_public_key(
    alg_id_t alg_id, const uint8_t authority_key_digest[SHA1_DIGEST_LENGTH],
    const uint8_t** pub_key, size_t* pub_key_size) {
  const uint8_t* root_keys = NULL;
  int root_key_count = 0;
  size_t root_key_size = 0;
  switch (alg_id) {
    case ALG_ID_ECDSA_P256_WITH_SHA256:
      root_keys = (const uint8_t*)ROOT_KEYS_P256;
      root_key_count = sizeof(ROOT_KEYS_P256) / sizeof(ROOT_KEYS_P256[0]);
      root_key_size = sizeof(ROOT_KEYS_P256[0]);
      break;
    case ALG_ID_EDDSA_25519:
      root_keys = (const uint8_t*)ROOT_KEYS_ED25519;
      root_key_count = sizeof(ROOT_KEYS_ED25519) / sizeof(ROOT_KEYS_ED25519[0]);
      root_key_size = sizeof(ROOT_KEYS_ED25519[0]);
      break;
    case ALG_ID_MLDSA44:
      root_keys = (const uint8_t*)ROOT_KEYS_MLDSA44;
      root_key_count = sizeof(ROOT_KEYS_MLDSA44) / sizeof(ROOT_KEYS_MLDSA44[0]);
      root_key_size = sizeof(ROOT_KEYS_MLDSA44[0]);
      break;
    default:
      return false;
  }

  for (int i = 0; i < root_key_count; ++i) {
    uint8_t pub_key_digest[SHA1_DIGEST_LENGTH] = {0};
    const uint8_t* root_key = root_keys + i * root_key_size;
    sha1_Raw(root_key, root_key_size, pub_key_digest);
    if (memcmp(authority_key_digest, pub_key_digest, sizeof(pub_key_digest)) ==
        0) {
      *pub_key = root_key;
      *pub_key_size = root_key_size;
      return true;
    }
  }

  return false;
}

bool check_cert_chain(cli_t* cli, const uint8_t* chain, size_t chain_size,
                      const uint8_t* sig, size_t sig_size,
                      const uint8_t challenge[CHALLENGE_SIZE]) {
  // Checks the integrity of the device certificate chain to ensure that the
  // certificate data was not corrupted in transport and that the device
  // certificate belongs to this device.
  // The certificate chain should contain two certificates:
  //   * the end-entity certificate (device certificate)
  //   * the intermediate CA certificate
  // THIS IS NOT A FULL VERIFICATION OF THE CERTIFICATE CHAIN.

  // This will be populated with a pointer to the key identifier data of the
  // AuthorityKeyIdentifier extension from the last certificate in the chain.
  const uint8_t* authority_key_digest = NULL;

  const uint8_t* message = challenge;
  size_t message_size = CHALLENGE_SIZE;

  const uint8_t* pub_key = NULL;
  size_t pub_key_size = 0;

  alg_id_t alg_id = 0;

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

    // Skip the version, serialNumber, signature algorithm, issuer and validity
    DER_ITEM der_item = {0};
    for (int i = 0; i < 5; ++i) {
      if (!der_read_item(&tbs_cert.buf, &der_item)) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, der_read_item 3, cert %d.",
                  cert_count);
        return false;
      }
    }

    // Read the subject.
    DER_ITEM subject = {0};
    if (!der_read_item(&tbs_cert.buf, &subject)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 4, cert %d.",
                cert_count);
      return false;
    }

    if (cert_count == 1) {
      // Check the common name of the subject of the device certificate.
      const uint8_t* common_name = NULL;
      size_t common_name_size = 0;
      if (!get_name_attribute(&subject, OID_COMMON_NAME,
                              sizeof(OID_COMMON_NAME), &common_name,
                              &common_name_size) ||
          common_name_size != sizeof(SUBJECT_COMMON_NAME) ||
          memcmp(common_name, SUBJECT_COMMON_NAME,
                 sizeof(SUBJECT_COMMON_NAME)) != 0) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, invalid common name.");
        return false;
      }

#if !(defined TREZOR_MODEL_T3B1 || defined TREZOR_MODEL_T3T1)
      // Check that the serial number of the subject, matches the device.
      uint8_t device_sn[MAX_DEVICE_SN_SIZE] = {0};
      size_t device_sn_size = 0;
      if (!unit_properties_get_sn(device_sn, sizeof(device_sn),
                                  &device_sn_size) ||
          device_sn_size == 0) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, device_sn not set.");
      }

      const uint8_t* subject_sn = NULL;
      size_t subject_sn_size = 0;
      if (!get_name_attribute(&subject, OID_SERIAL_NUMBER,
                              sizeof(OID_SERIAL_NUMBER), &subject_sn,
                              &subject_sn_size)) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, serialNumber not set.");
      }

      if (subject_sn_size != device_sn_size ||
          memcmp(subject_sn, device_sn, device_sn_size) != 0) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, serial number mismatch.");
        return false;
      }
#endif
    }

    // Read the Subject Public Key Info.
    DER_ITEM pub_key_info = {0};
    if (!der_read_item(&tbs_cert.buf, &pub_key_info)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 5, cert %d.",
                cert_count);
      return false;
    }

    // Read the algorithm
    DER_ITEM alg = {0};
    if (!der_read_item(&pub_key_info.buf, &alg) ||
        !get_algorithm(&alg, &alg_id)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, reading algorithm, cert %d.",
                cert_count);
      return false;
    }

    // Read the public key.
    DER_ITEM pub_key_val = {0};
    uint8_t unused_bits = 0;
    if (!der_read_item(&pub_key_info.buf, &pub_key_val)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 6, cert %d.",
                cert_count);
      return false;
    }

    if (!buffer_get(&pub_key_val.buf, &unused_bits) ||
        !buffer_ptr(&pub_key_val.buf, &pub_key)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, reading public key, cert %d.",
                cert_count);
      return false;
    }
    pub_key_size = buffer_remaining(&pub_key_val.buf);

    // Verify the previous signature.
    if (!verify_signature(alg_id, pub_key, pub_key_size, sig, sig_size, message,
                          message_size)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, verify_signature, cert %d.",
                cert_count);
      return false;
    }

    // Get the authority key identifier from the last certificate.
    if (buffer_remaining(&chain_reader) == 0 &&
        !get_authority_key_digest(cli, &tbs_cert, &authority_key_digest)) {
      // Error returned by get_authority_key_digest().
      return false;
    }

    // Save tbsCertificate for the next signature verification.
    message = tbs_cert.buf.data;
    message_size = tbs_cert.buf.size;

    // skip the signatureAlgorithm
    DER_ITEM sig_alg = {0};
    if (!der_read_item(&cert.buf, &sig_alg)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 7, cert %d.", "%d.",
                cert_count);
      return false;
    }

    // Read the signature and save it for the next signature verification.
    DER_ITEM sig_val = {0};
    if (!der_read_item(&cert.buf, &sig_val) || sig_val.id != DER_BIT_STRING ||
        !buffer_get(&sig_val.buf, &unused_bits) || unused_bits != 0 ||
        !buffer_ptr(&sig_val.buf, &sig)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, reading signatureValue, cert %d.",
                cert_count);
      return false;
    }
    sig_size = buffer_remaining(&sig_val.buf);
  }

  if (alg_id == ALG_ID_ECDSA_P256_WITH_SHA256) {
    // Verify that the signature of the last certificate in the chain matches
    // its own AuthorityKeyIdentifier to verify the integrity of the certificate
    // data. This is done only for ECDSA, since EdDSA does not allow recovery of
    // the public key from the signature.
    uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
    sha256_Raw(message, message_size, digest);

    uint8_t decoded_sig[64] = {0};
    if (ecdsa_sig_from_der(sig, sig_size, decoded_sig) != 0) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, ecdsa_sig_from_der root.");
      return false;
    }

    bool matches = false;
    for (int recid = 0; recid < 4; ++recid) {
      uint8_t recovered_pub_key[65] = {0};
      if (ecdsa_recover_pub_from_sig(&nist256p1, recovered_pub_key, decoded_sig,
                                     digest, recid) == 0) {
        uint8_t pub_key_digest[SHA1_DIGEST_LENGTH] = {0};
        sha1_Raw(recovered_pub_key, sizeof(recovered_pub_key), pub_key_digest);
        if (memcmp(authority_key_digest, pub_key_digest,
                   sizeof(pub_key_digest)) == 0) {
          matches = true;
          break;
        }
      }
    }
    if (!matches) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, ecdsa_verify_digest root.");
      return false;
    }
  }

  if (!get_root_public_key(alg_id, authority_key_digest, &pub_key,
                           &pub_key_size)) {
    const char msg[] =
        "check_device_cert_chain, failed to get root public key.";
#if PRODUCTION
    cli_error(cli, CLI_ERROR, msg);
    return false;
#else
    // In non-production mode we succeed and write the certificate even if the
    // root key is unknown, but we at least emit a warning.
    cli_trace(cli, msg);
    return true;
#endif
  }

  // Verify the last signature.
  if (!verify_signature(alg_id, pub_key, pub_key_size, sig, sig_size, message,
                        message_size)) {
    cli_error(cli, CLI_ERROR,
              "check_device_cert_chain, verify_signature, cert %d.",
              cert_count);
    return false;
  }

  return true;
}

#ifdef USE_NRF
#define BINARY_MAXSIZE \
  (0x50000 > BOOTLOADER_MAXSIZE ? 0x50000 : BOOTLOADER_MAXSIZE)
#else
#define BINARY_MAXSIZE BOOTLOADER_MAXSIZE
#endif

__attribute__((section(".buf"),
               aligned(4))) static uint8_t binary_buffer[BINARY_MAXSIZE];
static size_t binary_len = 0;
static bool binary_update_in_progress = false;

void binary_update(cli_t* cli, bool (*finalize)(uint8_t* data, size_t len)) {
  if (cli_arg_count(cli) < 1) {
    cli_error_arg_count(cli);
    return;
  }

  const char* phase = cli_arg(cli, "phase");

  if (phase == NULL) {
    cli_error_arg(cli, "Expecting phase (begin|chunk|end).");
  }

  if (0 == strcmp(phase, "begin")) {
    if (cli_arg_count(cli) != 1) {
      cli_error_arg_count(cli);
      goto cleanup;
    }

    // Reset our state
    binary_len = 0;
    binary_update_in_progress = true;
    cli_trace(cli, "Begin");
    cli_ok(cli, "");

  } else if (0 == strcmp(phase, "chunk")) {
    if (cli_arg_count(cli) < 2) {
      cli_error_arg_count(cli);
      goto cleanup;
    }

    if (!binary_update_in_progress) {
      cli_error(cli, CLI_ERROR, "Update not started. Use 'begin' first.");
      goto cleanup;
    }

    // Receive next piece of the image
    size_t chunk_len = 0;

    if (!cli_arg_hex(cli, "hex-data", &binary_buffer[binary_len],
                     sizeof(binary_buffer) - binary_len, &chunk_len)) {
      cli_error_arg(cli, "Expecting hex data for chunk.");
      goto cleanup;
    }

    binary_len += chunk_len;

    cli_ok(cli, "%u %u", (unsigned)chunk_len, (unsigned)binary_len);

  } else if (0 == strcmp(phase, "end")) {
    if (cli_arg_count(cli) != 1) {
      cli_error_arg_count(cli);
      goto cleanup;
    }

    if (binary_len == 0) {
      cli_error(cli, CLI_ERROR, "No data received");
      goto cleanup;
    }

    if (!finalize(binary_buffer, binary_len)) {
      binary_len = 0;
      cli_error(cli, CLI_ERROR, "Error while finalizing the update");
      goto cleanup;
    }

    cli_trace(cli, "Update successful (%u bytes)", (unsigned)binary_len);
    cli_ok(cli, "");

    // Reset state so next begin must come before chunks
    binary_len = 0;
    binary_update_in_progress = false;

  } else {
    cli_error(cli, CLI_ERROR, "Unknown phase '%s' (begin|chunk|end)", phase);
    goto cleanup;
  }

  return;

cleanup:
  binary_update_in_progress = false;
  binary_len = 0;
}
