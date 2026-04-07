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

#include "sec/optiga_common.h"
#ifdef SECURE_MODE

#include <trezor_rtl.h>

#include <sec/optiga.h>
#include <sec/optiga_commands.h>
#include <sec/optiga_transport.h>
#include <sec/rng_strong.h>
#include <sec/secret_keys.h>
#include <sec/storage.h>
#include "ecdsa.h"
#include "hash_to_curve.h"
#include "hmac.h"
#include "memzero.h"
#include "nist256p1.h"
#include "time_estimate.h"

// Counter-protected PIN secret and reset key for OID_STRETCHED_PIN_CTR (OID
// 0xF1D0).
#define OID_PIN_SECRET (OPTIGA_OID_DATA + 0)

// Counter-protected key for HMAC-SHA256 PIN stretching step (OID 0xF1D8).
#define OID_PIN_HMAC (OPTIGA_OID_DATA + 8)

// Counter which limits the guesses at OID_STRETCHED_PINS (OID 0xE120).
#define OID_STRETCHED_PIN_CTR (OPTIGA_OID_COUNTER + 0)

// Counter which limits the use of OID_PIN_HMAC (OID 0xE122).
#define OID_PIN_HMAC_CTR (OPTIGA_OID_COUNTER + 2)

// Counter which limits the total number of PIN stretching operations over the
// lifetime of the device (OID 0xE121).
#define OID_PIN_TOTAL_CTR (OPTIGA_OID_COUNTER + 1)

// Key for HMAC-SHA256 PIN stretching step used in storage version 3 and 4 (OID
// 0xF1D1).
#define OID_PIN_HMAC_V4 (OPTIGA_OID_DATA + 1)

// Key for AES-CMAC PIN stretching step (OID 0xE200).
#define OID_PIN_CMAC OPTIGA_OID_SYM_KEY

// Key for ECDH PIN stretching step (OID 0xE0F3).
#define OID_PIN_ECDH (OPTIGA_OID_ECC_KEY + 3)

// The number of times that PIN stretching is repeated.
#if STRETCHED_PIN_COUNT > 1
#define PIN_STRETCH_ITERATIONS 1
#else
#define PIN_STRETCH_ITERATIONS 2
#endif

// Initial value of the counter which limits the total number of PIN stretching
// operations. The limit is 600000 stretching operations, which equates to
// 300000 / PIN_STRETCH_ITERATIONS unlock operations over the lifetime of the
// device.
#define PIN_TOTAL_CTR_LIMIT 600000

// Stretched PINs
// The first stretched PIN is OPTIGA_OID_DATA + 4 to preserve compatiblity with
// Trezors without Tropics.
// OPTIGA_OID_DATA + 0 and OPTIGA_OID_DATA + 8 are not used since they are
// occupied by the PIN secret and PIN HMAC secret.
static const uint16_t OID_STRETCHED_PINS[] = {
    OPTIGA_OID_DATA + 4, OPTIGA_OID_DATA + 1, OPTIGA_OID_DATA + 2,
    OPTIGA_OID_DATA + 3, OPTIGA_OID_DATA + 5, OPTIGA_OID_DATA + 6,
    OPTIGA_OID_DATA + 7, OPTIGA_OID_DATA + 9, OPTIGA_OID_DATA + 10,
    OPTIGA_OID_DATA + 11};
_Static_assert(sizeof(OID_STRETCHED_PINS) / sizeof(OID_STRETCHED_PINS[0]) >=
                   STRETCHED_PIN_COUNT,
               "STRETCHED_PIN_COUNT too large");

static const optiga_metadata_item TYPE_AUTOREF =
    OPTIGA_META_VALUE(OPTIGA_DATA_TYPE_AUTOREF);
static const optiga_metadata_item TYPE_PRESSEC =
    OPTIGA_META_VALUE(OPTIGA_DATA_TYPE_PRESSEC);
static const optiga_metadata_item ACCESS_FIRST_STRETCHED_PIN =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO, OID_STRETCHED_PINS[0]);
static const optiga_metadata_item ACCESS_LAST_STRETCHED_PIN =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO,
                            OID_STRETCHED_PINS[STRETCHED_PIN_COUNT - 1]);
static const optiga_metadata_item ACCESS_PIN_SECRET =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO, OID_PIN_SECRET);
static const optiga_metadata_item ACCESS_STRETCHED_PIN_CTR =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_LUC, OID_STRETCHED_PIN_CTR);
static const optiga_metadata_item ACCESS_PIN_TOTAL_CTR =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_LUC, OID_PIN_TOTAL_CTR);
static const optiga_metadata_item ACCESS_PIN_HMAC_CTR =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_LUC, OID_PIN_HMAC_CTR);

// Size of the DER BIT STRING header required for inputs to optiga_calc_ssec().
#define BIT_STRING_HEADER_SIZE 3

// Size of the CMAC/HMAC prefix returned by Optiga.
#define ENCRYPT_SYM_PREFIX_SIZE 3

optiga_sign_result optiga_sign(uint8_t index, const uint8_t *digest,
                               size_t digest_size, uint8_t *der_signature,
                               size_t max_der_signature_size,
                               size_t *der_signature_size) {
  optiga_sign_result ret = OPTIGA_SIGN_SUCCESS;
  if (index >= OPTIGA_ECC_KEY_COUNT) {
    ret = OPTIGA_SIGN_ERROR;
    goto cleanup;
  }

#ifdef SECRET_KEY_MASKING
  uint8_t masking_key[ECDSA_PRIVATE_KEY_SIZE] = {0};
  uint8_t masked_digest[SHA256_DIGEST_LENGTH] = {0};
  bool is_masked = (index == OPTIGA_FIDO_ECC_KEY_INDEX);
  if (is_masked) {
    if (digest_size != SHA256_DIGEST_LENGTH ||
        secret_key_optiga_masking(masking_key) != sectrue ||
        ecdsa_mask_scalar(&nist256p1, masking_key, digest, masked_digest) !=
            0) {
      ret = OPTIGA_SIGN_ERROR;
      goto cleanup;
    }
    digest = masked_digest;
  }
#endif  // SECRET_KEY_MASKING

  optiga_result res = optiga_calc_sign(
      OPTIGA_OID_ECC_KEY + index, digest, digest_size, &der_signature[2],
      max_der_signature_size - 2, der_signature_size);
  if (res != OPTIGA_SUCCESS) {
    uint8_t error_code = 0;
    if (res == OPTIGA_ERR_CMD &&
        optiga_get_error_code(&error_code) == OPTIGA_SUCCESS &&
        error_code == OPTIGA_ERR_CODE_ACCESS_COND) {
      ret = OPTIGA_SIGN_INACCESSIBLE;
      goto cleanup;
    } else {
      ret = OPTIGA_SIGN_ERROR;
      goto cleanup;
    }
  }

  // Add sequence tag and length.
  if (*der_signature_size >= 0x80) {
    // Length not supported.
    ret = OPTIGA_SIGN_ERROR;
    goto cleanup;
  }
  der_signature[0] = 0x30;
  der_signature[1] = *der_signature_size;
  *der_signature_size += 2;

#ifdef SECRET_KEY_MASKING
  uint8_t raw_signature[ECDSA_RAW_SIGNATURE_SIZE] = {0};
  if (is_masked) {
    if (max_der_signature_size < MAX_DER_SIGNATURE_SIZE ||
        ecdsa_sig_from_der(der_signature, der_signature_size, raw_signature) !=
            0 ||
        ecdsa_unmask_scalar(curve, masking_key, &raw_signature[32],
                            &raw_signature[32]) != 0) {
      ret = OPTIGA_SIGN_ERROR;
      goto cleanup;
    }
    *der_signature_size = ecdsa_sig_to_der(raw_signature, der_signature);
  }
#endif  // SECRET_KEY_MASKING

cleanup:
#ifdef SECRET_KEY_MASKING
  memzero(masking_key, sizeof(masking_key));
  memzero(masked_digest, sizeof(masked_digest));
  memzero(raw_signature, sizeof(raw_signature));
#endif  // SECRET_KEY_MASKING
  return ret;
}

bool optiga_cert_size(uint8_t index, size_t *cert_size) {
  *cert_size = 0;

  if (index >= OPTIGA_CERT_COUNT) {
    return false;
  }

  uint8_t metadata_bytes[OPTIGA_MAX_METADATA_SIZE] = {0};
  size_t metadata_size = 0;
  optiga_metadata metadata = {0};
  optiga_result ret =
      optiga_get_data_object(OPTIGA_OID_CERT + index, true, metadata_bytes,
                             sizeof(metadata_bytes), &metadata_size);
  if (OPTIGA_SUCCESS != ret) {
    return false;
  }

  ret = optiga_parse_metadata(metadata_bytes, metadata_size, &metadata);
  if (OPTIGA_SUCCESS != ret || metadata.used_size.ptr == NULL) {
    return false;
  }

  for (int i = 0; i < metadata.used_size.len; ++i) {
    *cert_size = (*cert_size << 8) + metadata.used_size.ptr[i];
  }

  return true;
}

bool optiga_read_cert(uint8_t index, uint8_t *cert, size_t max_cert_size,
                      size_t *cert_size) {
  if (index >= OPTIGA_CERT_COUNT) {
    return false;
  }

  optiga_result ret = optiga_get_data_object(OPTIGA_OID_CERT + index, false,
                                             cert, max_cert_size, cert_size);
  return OPTIGA_SUCCESS == ret;
}

bool optiga_read_sec(uint8_t *sec) {
  size_t size = 0;
  optiga_result ret = optiga_get_data_object(OPTIGA_OID_SEC, false, sec,
                                             sizeof(uint8_t), &size);
  return ret == OPTIGA_SUCCESS && size == sizeof(uint8_t);
}

void optiga_set_sec_max(void) {
  uint8_t invalid_point[] = {
      0x03, 0x42, 0x00, 0x04, 0xe2, 0x67, 0x5b, 0xe0, 0xbb, 0xf4, 0xfb, 0x9d,
      0xec, 0xaa, 0x1e, 0x96, 0xac, 0xc8, 0xa7, 0xca, 0xd0, 0x05, 0x84, 0xfe,
      0xfd, 0x7f, 0x24, 0xc6, 0xe7, 0x72, 0x5b, 0x56, 0xb3, 0x45, 0x06, 0x67,
      0xbc, 0x73, 0xe3, 0xb8, 0xf5, 0x5d, 0x1c, 0xad, 0xa0, 0x3e, 0x59, 0x1b,
      0x3b, 0x9c, 0x6e, 0xc4, 0xb6, 0xd1, 0x05, 0xf7, 0xd8, 0xc0, 0x67, 0x0d,
      0xfb, 0xcc, 0xea, 0xb1, 0x65, 0xdb, 0xa6, 0x5f};
  uint8_t buffer[32] = {0};
  size_t size = 0;
  optiga_calc_ssec(OPTIGA_CURVE_P256, OID_PIN_ECDH, invalid_point,
                   sizeof(invalid_point), buffer, sizeof(buffer), &size);
}

bool optiga_random_buffer(uint8_t *dest, size_t size) {
  while (size > OPTIGA_RANDOM_MAX_SIZE) {
    if (optiga_get_random(dest, OPTIGA_RANDOM_MAX_SIZE) != OPTIGA_SUCCESS) {
      return false;
    }
    dest += OPTIGA_RANDOM_MAX_SIZE;
    size -= OPTIGA_RANDOM_MAX_SIZE;
  }

  if (size < OPTIGA_RANDOM_MIN_SIZE) {
    static uint8_t buffer[OPTIGA_RANDOM_MIN_SIZE] = {0};
    optiga_result ret = optiga_get_random(buffer, OPTIGA_RANDOM_MIN_SIZE);
    memcpy(dest, buffer, size);
    return ret == OPTIGA_SUCCESS;
  }

  return optiga_get_random(dest, size) == OPTIGA_SUCCESS;
}

void optiga_random_buffer_time(uint32_t *time_ms) {
  // Assuming the data size is 32 bytes
  return optiga_get_random_time(time_ms);
}

static bool read_metadata(uint16_t oid, optiga_metadata *metadata) {
  static uint8_t serialized[OPTIGA_MAX_METADATA_SIZE] = {0};
  size_t size = 0;
  if (optiga_get_data_object(oid, true, serialized, sizeof(serialized),
                             &size) != OPTIGA_SUCCESS) {
    return false;
  }

  return optiga_parse_metadata(serialized, size, metadata) == OPTIGA_SUCCESS;
}

static bool write_metadata(uint16_t oid, const optiga_metadata *metadata) {
  uint8_t serialized[OPTIGA_MAX_METADATA_SIZE] = {0};
  size_t size = 0;

  if (optiga_serialize_metadata(metadata, serialized, sizeof(serialized),
                                &size) != OPTIGA_SUCCESS) {
    return false;
  }

  return optiga_set_data_object(oid, true, serialized, size) == OPTIGA_SUCCESS;
}

bool optiga_set_metadata(uint16_t oid, const optiga_metadata *metadata) {
  // Read the stored metadata.
  optiga_metadata metadata_stored = {0};
  if (!read_metadata(oid, &metadata_stored)) {
    return false;
  }

  // If the stored metadata are different, then set them as requested.
  if (!optiga_compare_metadata(metadata, &metadata_stored)) {
    if (!write_metadata(oid, metadata)) {
      return false;
    }

    // Check that the metadata was written correctly.
    if (!read_metadata(oid, &metadata_stored)) {
      return false;
    }
    if (!optiga_compare_metadata(metadata, &metadata_stored)) {
      return false;
    }
  }

#if PRODUCTION
  // If the metadata aren't locked, then lock them in production builds.
  optiga_metadata metadata_locked = {0};
  metadata_locked.lcso = OPTIGA_META_LCS_OPERATIONAL;
  if (!optiga_compare_metadata(&metadata_locked, &metadata_stored)) {
    if (!write_metadata(oid, &metadata_locked)) {
      return false;
    }

    // Check that metadata were locked correctly.
    if (!read_metadata(oid, &metadata_stored)) {
      return false;
    }
    if (!optiga_compare_metadata(&metadata_locked, &metadata_stored)) {
      return false;
    }
  }
#endif

  return true;
}

void optiga_set_metadata_time(bool is_configured, uint32_t *time_ms) {
  optiga_get_data_object_time(true, time_ms);
  if (!is_configured) {
    optiga_set_data_object_time(true, time_ms);
    optiga_get_data_object_time(true, time_ms);
  }
#if PRODUCTION
  if (!is_configured) {
    optiga_set_data_object_time(true, time_ms);
    optiga_get_data_object_time(true, time_ms);
  }
#endif
}

// This is a heuristic and can only be used to estimate how long it will take to
// execute `optiga_pin_init_metadata()
static bool optiga_is_configured() {
  // Read the metadata of OID_PIN_SECRET to determine whether
  // optiga_pin_init_metadata() has been called in the past
  optiga_metadata metadata = {0};
  optiga_metadata metadata_stored = {0};

  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = ACCESS_LAST_STRETCHED_PIN;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  metadata.data_type = TYPE_AUTOREF;
#if PRODUCTION
  metadata.lcso = OPTIGA_META_LCS_OPERATIONAL;
#endif

  if (!read_metadata(OID_PIN_SECRET, &metadata_stored)) {
    return false;
  }

  return optiga_compare_metadata(&metadata, &metadata_stored);
}

static bool optiga_pin_init_metadata() {
  optiga_metadata metadata = {0};

  // Set metadata for counter-protected PIN secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = ACCESS_LAST_STRETCHED_PIN;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_PIN_SECRET, &metadata)) {
    return false;
  }

#if STRETCHED_PIN_COUNT == 1
  // Set metadata for the stretched PIN.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_PIN_SECRET;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_STRETCHED_PIN_CTR;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_STRETCHED_PINS[0], &metadata)) {
    return false;
  }
#else
  // Set metadata for the first stretched PIN.
  memzero(&metadata, sizeof(metadata));
  metadata.change =
      OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO, OID_STRETCHED_PINS[1]);
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_STRETCHED_PIN_CTR;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_STRETCHED_PINS[0], &metadata)) {
    return false;
  }

  // Set metadata for the rest of the stretched PINs.
  for (int i = 1; i < STRETCHED_PIN_COUNT - 1; i++) {
    memzero(&metadata, sizeof(metadata));
    metadata.change = OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO,
                                              OID_STRETCHED_PINS[i + 1]);
    metadata.read = OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO,
                                            OID_STRETCHED_PINS[i - 1]);
    metadata.execute = ACCESS_STRETCHED_PIN_CTR;
    metadata.data_type = TYPE_AUTOREF;
    if (!optiga_set_metadata(OID_STRETCHED_PINS[i], &metadata)) {
      return false;
    }
  }

  // Set metadata for the last stretched PIN.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_PIN_SECRET;
  metadata.read = OPTIGA_ACCESS_CONDITION(
      OPTIGA_ACCESS_COND_AUTO, OID_STRETCHED_PINS[STRETCHED_PIN_COUNT - 2]);
  metadata.execute = ACCESS_STRETCHED_PIN_CTR;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_STRETCHED_PINS[STRETCHED_PIN_COUNT - 1],
                           &metadata)) {
    return false;
  }
#endif

  // Set metadata for HMAC-SHA256 PIN stretching secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_FIRST_STRETCHED_PIN;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_HMAC_CTR;
  metadata.data_type = TYPE_PRESSEC;
  if (!optiga_set_metadata(OID_PIN_HMAC, &metadata)) {
    return false;
  }

  // Set metadata for the counter of guesses at OID_STRETCHED_PINS.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_PIN_SECRET;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!optiga_set_metadata(OID_STRETCHED_PIN_CTR, &metadata)) {
    return false;
  }

  // Set metadata for the counter of OID_PIN_HMAC uses.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_FIRST_STRETCHED_PIN;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!optiga_set_metadata(OID_PIN_HMAC_CTR, &metadata)) {
    return false;
  }

  // Initialize the counter of the total number of PIN stretching operations, if
  // write access is possible.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  if (write_metadata(OID_PIN_TOTAL_CTR, &metadata)) {
    optiga_result res =
        optiga_reset_counter(OID_PIN_TOTAL_CTR, PIN_TOTAL_CTR_LIMIT);
    if (res != OPTIGA_SUCCESS) {
      return false;
    }
  }

  // Set metadata for the counter of the total number of PIN stretching
  // operations.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!optiga_set_metadata(OID_PIN_TOTAL_CTR, &metadata)) {
    return false;
  }

  // Set metadata for AES-CMAC PIN stretching secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_TOTAL_CTR;
  metadata.key_usage = OPTIGA_META_KEY_USE_ENC;
  if (!optiga_set_metadata(OID_PIN_CMAC, &metadata)) {
    return false;
  }

  // Set metadata for ECDH PIN stretching secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_TOTAL_CTR;
  metadata.key_usage = OPTIGA_META_KEY_USE_KEYAGREE;
  if (!optiga_set_metadata(OID_PIN_ECDH, &metadata)) {
    return false;
  }

  return true;
}

static void optiga_pin_init_metadata_time(uint32_t *time_ms) {
  bool is_configured = optiga_is_configured();
  optiga_set_metadata_time(is_configured, time_ms);  // OID_PIN_SECRET

#if STRETCHED_PIN_COUNT == 1
  optiga_set_metadata_time(is_configured, time_ms);  // OID_STRETCHED_PINS[0]
#else
  optiga_set_metadata_time(is_configured, time_ms);  // OID_STRETCHED_PINS[0]
  for (int i = 1; i < STRETCHED_PIN_COUNT - 1; i++) {
    // OID_STRETCHED_PINS[i]
    optiga_set_metadata_time(is_configured, time_ms);
  }
  // OID_STRETCHED_PINS[STRETCHED_PIN_COUNT - 1]
  optiga_set_metadata_time(is_configured, time_ms);
#endif
  optiga_set_metadata_time(is_configured, time_ms);  // OID_PIN_HMAC
  optiga_set_metadata_time(is_configured, time_ms);  // OID_STRETCHED_PIN_CTR
  optiga_set_metadata_time(is_configured, time_ms);  // OID_PIN_HMAC_CTR
  optiga_set_data_object_time(true, time_ms);        // OID_PIN_TOTAL_CTR
  if (is_configured) {
    optiga_reset_counter_time(time_ms);  // OID_PIN_TOTAL_CTR
  }
  optiga_set_metadata_time(is_configured, time_ms);  // OID_PIN_TOTAL_CTR
  optiga_set_metadata_time(is_configured, time_ms);  // OID_PIN_CMAC
  optiga_set_metadata_time(is_configured, time_ms);  // OID_PIN_ECDH
}

static bool optiga_pin_init_stretch() {
  // Generate a new key in OID_PIN_CMAC.
  if (optiga_gen_sym_key(OPTIGA_AES_256, OPTIGA_KEY_USAGE_ENC, OID_PIN_CMAC) !=
      OPTIGA_SUCCESS) {
    return false;
  }

  // Generate a new key in OID_PIN_ECDH.
  uint8_t public_key[6 + 65] = {0};
  size_t size = 0;
  optiga_result res =
      optiga_gen_key_pair(OPTIGA_CURVE_P256, OPTIGA_KEY_USAGE_KEYAGREE,
                          OID_PIN_ECDH, public_key, sizeof(public_key), &size);

  return res == OPTIGA_SUCCESS;
}

static void optiga_pin_init_stretch_time(uint32_t *time_ms) {
  optiga_gen_sym_key_time(time_ms);
  optiga_gen_key_pair_time(time_ms);
}

static bool optiga_pin_stretch_common(
    HMAC_SHA256_CTX *ctx, const uint8_t input[OPTIGA_PIN_SECRET_SIZE],
    bool version4) {
  // Implements the functionality that is common to
  // optiga_pin_stretch_cmac_ecdh() and the legacy function
  // optiga_pin_stretch_secret_v4().

  uint8_t buffer[ENCRYPT_SYM_PREFIX_SIZE + OPTIGA_PIN_SECRET_SIZE] = {0};
  size_t size = 0;
  bool ret = true;

  // Combine intermediate result with OID_PIN_CMAC.
  if (optiga_encrypt_sym(OPTIGA_SYM_MODE_CMAC, OID_PIN_CMAC, input,
                         OPTIGA_PIN_SECRET_SIZE, buffer, sizeof(buffer),
                         &size) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  hmac_sha256_Update(ctx, buffer, size);

  if (version4) {
    // Combine intermediate result with OID_PIN_HMAC
    if (optiga_encrypt_sym(OPTIGA_SYM_MODE_HMAC_SHA256, OID_PIN_HMAC_V4, input,
                           OPTIGA_PIN_SECRET_SIZE, buffer, sizeof(buffer),
                           &size) != OPTIGA_SUCCESS) {
      ret = false;
      goto end;
    }

    hmac_sha256_Update(ctx, buffer, size);
  }

  // Combine intermediate result with OID_PIN_ECDH
  uint8_t encoded_point[BIT_STRING_HEADER_SIZE + 65] = {0x03, 0x42, 0x00};
  if (!hash_to_curve_optiga(input, &encoded_point[BIT_STRING_HEADER_SIZE])) {
    ret = false;
    goto end;
  }

  if (optiga_calc_ssec(OPTIGA_CURVE_P256, OID_PIN_ECDH, encoded_point,
                       sizeof(encoded_point), buffer, sizeof(buffer),
                       &size) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  hmac_sha256_Update(ctx, buffer, size);

end:
  memzero(encoded_point, sizeof(encoded_point));
  memzero(buffer, sizeof(buffer));
  return ret;
}

static bool optiga_pin_stretch_secret_v4(
    uint8_t secret[OPTIGA_PIN_SECRET_SIZE]) {
  // Legacy PIN verification method used in storage versions 3 and 4.

  // This step hardens the PIN verification process in case an attacker is able
  // to extract the secret value of a data object in Optiga that has a
  // particular configuration, but does not allow secret extraction for other
  // kinds of data objects. An attacker would need to be able to extract each of
  // the secrets in the different data objects to conduct an offline brute-force
  // search for the PIN. Thus it reduces the number of PIN values that the
  // attacker can test in a unit of time by forcing them to involve the Optiga
  // in each attempt.

  // Pseudocode for the stretching process:
  // cmac_out = CMAC(OID_PIN_CMAC, secret)
  // hmac_out = HMAC(OID_PIN_HMAC_V4, secret)
  // ecdh_out = ECDH(OID_PIN_ECDH, secret)
  // secret = HMAC-SHA256(secret, cmac_out || hmac_out || ecdh_out)

  HMAC_SHA256_CTX ctx = {0};
  hmac_sha256_Init(&ctx, secret, OPTIGA_PIN_SECRET_SIZE);

  bool ret = optiga_pin_stretch_common(&ctx, secret, true);
  if (ret) {
    hmac_sha256_Final(&ctx, secret);
  }

  memzero(&ctx, sizeof(ctx));
  return ret;
}

bool optiga_pin_stretch_cmac_ecdh(
    optiga_ui_progress_t ui_progress,
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  optiga_set_ui_progress(ui_progress);
  // This step hardens the PIN verification process in case an attacker is able
  // to extract the secret value of a data object in Optiga that has a
  // particular configuration, but does not allow secret extraction for other
  // kinds of data objects. An attacker would need to be able to extract each of
  // the secrets in the different data objects to conduct an offline brute-force
  // search for the PIN. Thus it reduces the number of PIN values that the
  // attacker can test in a unit of time by forcing them to involve the Optiga
  // in each attempt, and restricts the overall number of attempts using
  // OID_PIN_TOTAL_CTR.

  // Pseudocode for the stretching process:
  // for _ in range(PIN_STRETCH_ITERATIONS):
  //   digest = HMAC-SHA256(stretched_pin, "")
  //   cmac_out = CMAC(OID_PIN_CMAC, digest)
  //   ecdh_out = ECDH(OID_PIN_ECDH, digest)
  //   stretched_pin = HMAC-SHA256(stretched_pin, cmac_out || ecdh_out)

  bool ret = true;
  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};
  HMAC_SHA256_CTX ctx = {0};
  for (int i = 0; i < PIN_STRETCH_ITERATIONS; ++i) {
    // Process the stretched PIN using a one-way function before sending it to
    // the Optiga. This ensures that in the unlikely case of an attacker
    // recording communication between the MCU and Optiga, they will not gain
    // knowledge of the stretched PIN.
    hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);
    hmac_sha256_Init(&ctx, stretched_pin, OPTIGA_PIN_SECRET_SIZE);

    if (!optiga_pin_stretch_common(&ctx, digest, false)) {
      ret = false;
      goto end;
    }

    hmac_sha256_Final(&ctx, stretched_pin);
  }

end:
  memzero(digest, sizeof(digest));
  memzero(&ctx, sizeof(ctx));
  optiga_set_ui_progress(NULL);
  return ret;
}

void optiga_pin_stretch_cmac_ecdh_time(
    uint32_t *time_ms, uint8_t *optiga_sec,
    uint32_t *optiga_last_time_decreased_ms) {
  for (int i = 0; i < PIN_STRETCH_ITERATIONS; ++i) {
    optiga_encrypt_sym_time(OPTIGA_SYM_MODE_CMAC, time_ms, optiga_sec,
                            optiga_last_time_decreased_ms);
    *time_ms += time_estimate_hash_to_curve_ms();
    optiga_calc_ssec_time(time_ms, optiga_sec, optiga_last_time_decreased_ms);
  }
}

bool optiga_pin_init(optiga_ui_progress_t ui_progress) {
  optiga_set_ui_progress(ui_progress);
  bool ret = optiga_pin_init_metadata() && optiga_pin_init_stretch();
  optiga_set_ui_progress(NULL);
  return ret;
}

void optiga_pin_init_time(uint32_t *time_ms) {
  optiga_pin_init_metadata_time(time_ms);
  optiga_pin_init_stretch_time(time_ms);
}

static void optiga_pin_stretch_hmac_offline(
    const uint8_t hmac_stretching_secret[OPTIGA_PIN_SECRET_SIZE],
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  uint8_t hmac_buffer[ENCRYPT_SYM_PREFIX_SIZE + OPTIGA_PIN_SECRET_SIZE] = {
      0x61, 0x00, 0x20};
  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};

  // Process the stretched PIN using a one-way function before using it in the
  // operation that will be executed in Optiga during verification. This
  // ensures that in the unlikely case of an attacker recording communication
  // between the MCU and Optiga, they will not gain knowledge of the stretched
  // PIN.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);

  // Compute the operation that will be executed in Optiga during
  // verification.
  hmac_sha256(hmac_stretching_secret, OPTIGA_PIN_SECRET_SIZE, digest,
              sizeof(digest), &hmac_buffer[ENCRYPT_SYM_PREFIX_SIZE]);

  // Stretch the PIN with the result.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, hmac_buffer,
              sizeof(hmac_buffer), stretched_pin);

  memzero(digest, sizeof(digest));
  memzero(hmac_buffer, sizeof(hmac_buffer));
}

bool optiga_pin_set(
    optiga_ui_progress_t ui_progress,
    uint8_t stretched_pins[STRETCHED_PIN_COUNT][OPTIGA_PIN_SECRET_SIZE],
    uint8_t hmac_reset_key[OPTIGA_PIN_SECRET_SIZE]) {
  optiga_set_ui_progress(ui_progress);

  bool ret = true;

  uint8_t hmac_stretching_secret[OPTIGA_PIN_SECRET_SIZE] = {0};
  if (!rng_fill_buffer_strong(hmac_stretching_secret,
                              sizeof(hmac_stretching_secret))) {
    ret = false;
    goto end;
  }

  for (int i = 0; i < STRETCHED_PIN_COUNT; i++) {
    optiga_pin_stretch_hmac_offline(hmac_stretching_secret, stretched_pins[i]);
  }

  // Generate and store the counter-protected PIN secret.
  uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE] = {0};
  if (!rng_fill_buffer_strong(pin_secret, sizeof(pin_secret))) {
    ret = false;
    goto end;
  }

  if (optiga_set_data_object(OID_PIN_SECRET, false, pin_secret,
                             sizeof(pin_secret)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  // Authorise using OID_PIN_SECRET so that we can write to the last stretched
  // PIN and to OID_STRETCHED_PIN_CTR.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET, pin_secret,
                            sizeof(pin_secret)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  // Initialize the counter that limits the guesses at OID_STRETCHED_PINS with
  // OPTIGA_STRETCHED_PINS_COUNT + PIN_MAX_TRIES, of which
  // OPTIGA_STRETCHED_PINS_COUNT will be used when setting stretched PINs.
  if (optiga_reset_counter(OID_STRETCHED_PIN_CTR,
                           STRETCHED_PIN_COUNT + PIN_MAX_TRIES) !=
      OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};

  for (int i = STRETCHED_PIN_COUNT - 1; i >= 0; i--) {
    // Process the stretched PIN using a one-way function before sending it to
    // the Optiga. This ensures that in the unlikely case of an attacker
    // recording communication between the MCU and Optiga, they will not gain
    // knowledge of the stretched PIN.
    hmac_sha256(stretched_pins[i], OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);

    if (i == 0) {
      // The first stretched PIN is used to reset the HMAC counter.
      memcpy(hmac_reset_key, digest, sizeof(digest));
    }

    // Store the digest of the stretched PIN in OID_STRETCHED_PINS[i].
    if (optiga_set_data_object(OID_STRETCHED_PINS[i], false, digest,
                               sizeof(digest)) != OPTIGA_SUCCESS) {
      ret = false;
      goto end;
    }

    optiga_clear_all_auto_states();

    // Stretch the PIN more with the counter-protected PIN secret. This method
    // ensures that if the user chooses a high-entropy PIN, then even if the
    // Optiga and its communication link is completely compromised, it will not
    // reduce the security of their device any more than if the Optiga was not
    // integrated into the device in the first place.
    hmac_sha256(stretched_pins[i], OPTIGA_PIN_SECRET_SIZE, pin_secret,
                sizeof(pin_secret), stretched_pins[i]);

    // Authorise using OID_STRETCHED_PINS[i] so that we can write to
    //  * OID_STRETCHED_PINS[i - 1], if i > 0;
    //  * OID_PIN_HMAC and OID_PIN_HMAC_CTR, if i == 0.
    if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PINS[i],
                              digest, sizeof(digest)) != OPTIGA_SUCCESS) {
      ret = false;
      goto end;
    }
  }

  // Initialize the key for HMAC-SHA256 PIN stretching.
  if (optiga_set_data_object(OID_PIN_HMAC, false, hmac_stretching_secret,
                             OPTIGA_PIN_SECRET_SIZE) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  // Initialize the PIN counter which limits the use of OID_PIN_HMAC.
  if (optiga_reset_counter(OID_PIN_HMAC_CTR, PIN_MAX_TRIES) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

end:
  memzero(pin_secret, sizeof(pin_secret));
  memzero(digest, sizeof(digest));
  optiga_clear_all_auto_states();
  optiga_set_ui_progress(NULL);
  return ret;
}

void optiga_pin_set_time(uint32_t *time_ms, uint8_t *optiga_sec,
                         uint32_t *optiga_last_time_decreased_ms) {
  rng_fill_buffer_strong_time(time_ms);         // hmac_stretching_secret
  rng_fill_buffer_strong_time(time_ms);         // pin_secret
  optiga_set_data_object_time(false, time_ms);  // OID_PIN_SECRET
  // OID_PIN_SECRET
  optiga_set_auto_state_time(time_ms, optiga_sec,
                             optiga_last_time_decreased_ms);
  optiga_reset_counter_time(time_ms);  // OID_STRETCHED_PIN_CTR
  for (int i = STRETCHED_PIN_COUNT - 1; i >= 0; i--) {
    optiga_set_data_object_time(false, time_ms);  // OID_STRETCHED_PINS[i]
    // OID_STRETCHED_PINS[i - 1] or OID_PIN_SECRET
    optiga_clear_auto_state_time(time_ms);
    // OID_STRETCHED_PINS[i]
    optiga_set_auto_state_time(time_ms, optiga_sec,
                               optiga_last_time_decreased_ms);
  }
  optiga_set_data_object_time(false, time_ms);  // OID_PIN_HMAC
  optiga_reset_counter_time(time_ms);           // OID_PIN_HMAC_CTR
  // OID_STRETCHED_PINS[STRETCHED_PIN_COUNT - 1]
  optiga_clear_auto_state_time(time_ms);
}

optiga_pin_result optiga_pin_verify_v4(
    optiga_ui_progress_t ui_progress,
    const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
    uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]) {
  // Legacy PIN verification method used in storage version 3 and 4.

  optiga_set_ui_progress(ui_progress);
  optiga_pin_result ret = OPTIGA_PIN_SUCCESS;

  // Process the PIN-derived secret using a one-way function before sending it
  // to the Optiga.
  uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, NULL, 0, stretched_pin);

  // Combine the result with stretching secrets from the Optiga.
  if (!optiga_pin_stretch_secret_v4(stretched_pin)) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Authorise using OID_STRETCHED_PINS[0] so that we can read from
  // OID_PIN_SECRET.
  optiga_result res =
      optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PINS[0],
                            stretched_pin, sizeof(stretched_pin));
  if (res != OPTIGA_SUCCESS) {
    uint8_t error_code = 0;
    if (res != OPTIGA_ERR_CMD ||
        optiga_get_error_code(&error_code) != OPTIGA_SUCCESS) {
      ret = OPTIGA_PIN_ERROR;
      goto end;
    }

    switch (error_code) {
      case OPTIGA_ERR_CODE_CTR_LIMIT:
        ret = OPTIGA_PIN_COUNTER_EXCEEDED;
        break;
      case OPTIGA_ERR_CODE_AUTH_FAIL:
        ret = OPTIGA_PIN_INVALID;
        break;
      default:
        ret = OPTIGA_PIN_ERROR;
    }
    goto end;
  }

  // Read the master secret from OID_PIN_SECRET.
  size_t size = 0;
  if (optiga_get_data_object(OID_PIN_SECRET, false, out_secret,
                             OPTIGA_PIN_SECRET_SIZE, &size) != OPTIGA_SUCCESS ||
      size != OPTIGA_PIN_SECRET_SIZE) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Authorise using OID_PIN_SECRET so that we can write to
  // OID_STRETCHED_PIN_CTR.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET, out_secret,
                            OPTIGA_PIN_SECRET_SIZE) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Combine the value of OID_PIN_SECRET with the PIN-derived secret and
  // stretching secrets from the Optiga.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);
  if (!optiga_pin_stretch_secret_v4(out_secret)) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Combine the stretched master secret with the PIN-derived secret to derive
  // the output secret.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);

end:
  memzero(stretched_pin, sizeof(stretched_pin));
  optiga_clear_all_auto_states();
  optiga_set_ui_progress(NULL);
  return ret;
}

static optiga_pin_result optiga_pin_stretch_hmac(
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  optiga_pin_result ret = OPTIGA_PIN_SUCCESS;

  // Process the stretched PIN using a one-way function before sending it to the
  // Optiga.
  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);

  // HMAC the digest with the key in OID_PIN_HMAC.
  uint8_t hmac_buffer[ENCRYPT_SYM_PREFIX_SIZE + OPTIGA_PIN_SECRET_SIZE] = {0};
  size_t size = 0;
  optiga_result res = optiga_encrypt_sym(
      OPTIGA_SYM_MODE_HMAC_SHA256, OID_PIN_HMAC, digest, sizeof(digest),
      hmac_buffer, sizeof(hmac_buffer), &size);
  if (res != OPTIGA_SUCCESS) {
    uint8_t error_code = 0;
    if (res == OPTIGA_ERR_CMD &&
        optiga_get_error_code(&error_code) == OPTIGA_SUCCESS &&
        error_code == OPTIGA_ERR_CODE_ACCESS_COND) {
      ret = OPTIGA_PIN_COUNTER_EXCEEDED;
    } else {
      ret = OPTIGA_PIN_ERROR;
    }
    goto end;
  }

  // Stretch the PIN with the result.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, hmac_buffer, size,
              stretched_pin);

end:
  memzero(digest, sizeof(digest));
  memzero(hmac_buffer, sizeof(hmac_buffer));
  return ret;
}

static void optiga_pin_stretch_hmac_time(
    uint32_t *time_ms, uint8_t *optiga_sec,
    uint32_t *optiga_last_time_decreased_ms) {
  optiga_encrypt_sym_time(OPTIGA_SYM_MODE_HMAC_SHA256, time_ms, optiga_sec,
                          optiga_last_time_decreased_ms);
}

optiga_pin_result optiga_pin_verify(
    optiga_ui_progress_t ui_progress, uint8_t pin_index,
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  optiga_set_ui_progress(ui_progress);
  optiga_pin_result ret = OPTIGA_PIN_SUCCESS;

  if (pin_index >= STRETCHED_PIN_COUNT) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  ret = optiga_pin_stretch_hmac(stretched_pin);
  if (ret != OPTIGA_PIN_SUCCESS) {
    goto end;
  }

  // Process the stretched PIN using a one-way function before sending it to the
  // Optiga.
  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);

  // Authorise using OID_STRETCHED_PINS[pin_index] so that we can read from
  // OID_STRETCHED_PINS[pin_index + 1] and eventually from OID_PIN_SECRET.
  optiga_result res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX,
                                            OID_STRETCHED_PINS[pin_index],
                                            digest, sizeof(digest));
  if (res != OPTIGA_SUCCESS) {
    uint8_t error_code = 0;
    if (res != OPTIGA_ERR_CMD ||
        optiga_get_error_code(&error_code) != OPTIGA_SUCCESS) {
      ret = OPTIGA_PIN_ERROR;
      goto end;
    }

    switch (error_code) {
      case OPTIGA_ERR_CODE_CTR_LIMIT:
        ret = OPTIGA_PIN_COUNTER_EXCEEDED;
        break;
      case OPTIGA_ERR_CODE_AUTH_FAIL:
        ret = OPTIGA_PIN_INVALID;
        break;
      default:
        ret = OPTIGA_PIN_ERROR;
    }
    goto end;
  }

  uint8_t stretched_pin_ctr_limit = PIN_MAX_TRIES;
  if (pin_index == 0) {
    //  If this is the first PIN attempt or there is only one stretched PIN
    //  slot, the HMAC counter can be reset immediately. Otherwise, the counter
    //  is reset in optiga_pin_reset_hmac_counter().
    if (optiga_reset_counter(OID_PIN_HMAC_CTR, PIN_MAX_TRIES) !=
        OPTIGA_SUCCESS) {
      ret = OPTIGA_PIN_ERROR;
      goto end;
    }
  } else {
    // An extra attempt will be needed to authorize using OID_STRETCHED_PIN[0]
    // in optiga_pin_reset_hmac_counter().
    stretched_pin_ctr_limit += 1;
  }

  for (int i = pin_index + 1; i < STRETCHED_PIN_COUNT; i++) {
    size_t size = 0;
    if (optiga_get_data_object(OID_STRETCHED_PINS[i], false, digest,
                               OPTIGA_PIN_SECRET_SIZE,
                               &size) != OPTIGA_SUCCESS) {
      ret = OPTIGA_PIN_ERROR;
      goto end;
    }

    optiga_clear_all_auto_states();

    if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PINS[i],
                              digest, sizeof(digest)) != OPTIGA_SUCCESS) {
      ret = OPTIGA_PIN_ERROR;
      goto end;
    }
  }

  // Read the counter-protected PIN secret from OID_PIN_SECRET.
  uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE] = {0};
  size_t size = 0;
  if (optiga_get_data_object(OID_PIN_SECRET, false, pin_secret,
                             OPTIGA_PIN_SECRET_SIZE, &size) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  optiga_clear_all_auto_states();

  // Stretch the PIN more with the counter-protected PIN secret.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, pin_secret, size,
              stretched_pin);

  // Authorise using OID_PIN_SECRET so that we can reset OID_STRETCHED_PIN_CTR.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET, pin_secret,
                            sizeof(pin_secret)) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  if (optiga_reset_counter(OID_STRETCHED_PIN_CTR, stretched_pin_ctr_limit) !=
      OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

end:
  memzero(pin_secret, sizeof(pin_secret));
  memzero(digest, sizeof(digest));
  optiga_clear_all_auto_states();
  optiga_set_ui_progress(NULL);
  return ret;
}

void optiga_pin_verify_time(uint8_t pin_index, uint32_t *time_ms,
                            uint8_t *optiga_sec, uint32_t *optiga_last_time) {
  optiga_pin_stretch_hmac_time(time_ms, optiga_sec, optiga_last_time);
  // OID_STRETCHED_PINS[pin_index]
  optiga_set_auto_state_time(time_ms, optiga_sec, optiga_last_time);
  if (pin_index == 0) {
    optiga_reset_counter_time(time_ms);  // OID_PIN_HMAC_CTR
  }
  for (int i = pin_index + 1; i < STRETCHED_PIN_COUNT; i++) {
    optiga_get_data_object_time(false, time_ms);  // OID_STRETCHED_PINS[i]
    optiga_clear_auto_state_time(time_ms);        // OID_STRETCHED_PINS[i - 1]
    // OID_STRETCHED_PINS[i]
    optiga_set_auto_state_time(time_ms, optiga_sec, optiga_last_time);
  }
  optiga_get_data_object_time(false, time_ms);  // OID_PIN_SECRET
  // OID_STRETCHED_PIN_CTR[STRETCHED_PIN_COUNT - 1]
  optiga_clear_auto_state_time(time_ms);
  // OID_PIN_SECRET
  optiga_set_auto_state_time(time_ms, optiga_sec, optiga_last_time);
  optiga_reset_counter_time(time_ms);     // OID_STRETCHED_PIN_CTR
  optiga_clear_auto_state_time(time_ms);  // OID_PIN_SECRET
}

bool optiga_pin_reset_hmac_counter(
    optiga_ui_progress_t ui_progress,
    const uint8_t hmac_reset_key[OPTIGA_PIN_SECRET_SIZE]) {
  optiga_set_ui_progress(ui_progress);

  bool res = false;

  // Authorize using the first stretched PIN.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PINS[0],
                            hmac_reset_key,
                            OPTIGA_PIN_SECRET_SIZE) != OPTIGA_SUCCESS) {
    goto cleanup;
  }

  // Reset the counter.
  if (optiga_reset_counter(OID_PIN_HMAC_CTR, PIN_MAX_TRIES) != OPTIGA_SUCCESS) {
    goto cleanup;
  }

  res = true;

cleanup:
  optiga_clear_all_auto_states();
  optiga_set_ui_progress(NULL);
  return res;
}

void optiga_pin_reset_hmac_counter_time(
    uint32_t *time_ms, uint8_t *optiga_sec,
    uint32_t *optiga_last_time_decreased_ms) {
  optiga_set_auto_state_time(
      time_ms, optiga_sec,
      optiga_last_time_decreased_ms);     // OID_STRETCHED_PINS[0]
  optiga_reset_counter_time(time_ms);     // OID_PIN_HMAC_CTR
  optiga_clear_auto_state_time(time_ms);  // OID_STRETCHED_PINS[0]
}

static uint32_t uint32_from_be(uint8_t buf[4]) {
  uint32_t i = buf[0];
  i = (i << 8) + buf[1];
  i = (i << 8) + buf[2];
  i = (i << 8) + buf[3];
  return i;
}

static bool optiga_get_counter_rem(uint16_t oid, uint32_t *ctr) {
  uint8_t counter[8] = {0};
  size_t counter_size = 0;
  if (optiga_get_data_object(oid, false, counter, sizeof(counter),
                             &counter_size) != OPTIGA_SUCCESS ||
      counter_size != sizeof(counter)) {
    return false;
  }

  *ctr = uint32_from_be(&counter[4]) - uint32_from_be(&counter[0]);
  return true;
}

bool optiga_pin_get_rem_v4(uint32_t *ctr) {
  return optiga_get_counter_rem(OID_STRETCHED_PIN_CTR, ctr);
}

bool optiga_pin_get_rem(uint32_t *ctr) {
  uint32_t ctr1 = 0;
  uint32_t ctr2 = 0;
  if (!optiga_get_counter_rem(OID_PIN_HMAC_CTR, &ctr1) ||
      !optiga_get_counter_rem(OID_STRETCHED_PIN_CTR, &ctr2)) {
    return false;
  }

  // Ensure that the counters are in sync.
  if (ctr1 > ctr2) {
    if (optiga_count_data_object(OID_PIN_HMAC_CTR, ctr1 - ctr2) !=
        OPTIGA_SUCCESS) {
      return false;
    }
    *ctr = ctr2;
  } else if (ctr2 > ctr1) {
    if (optiga_count_data_object(OID_STRETCHED_PIN_CTR, ctr2 - ctr1) !=
        OPTIGA_SUCCESS) {
      return false;
    }
    *ctr = ctr1;
  } else {
    *ctr = ctr2;
  }
  return true;
}

bool optiga_pin_decrease_rem_v4(uint32_t count) {
  if (count > 0xff) {
    return false;
  }

  return optiga_count_data_object(OID_STRETCHED_PIN_CTR, count) ==
         OPTIGA_SUCCESS;
}

bool optiga_pin_decrease_rem(uint32_t count) {
  if (count > 0xff) {
    return false;
  }

  return optiga_count_data_object(OID_PIN_HMAC_CTR, count) == OPTIGA_SUCCESS &&
         optiga_count_data_object(OID_STRETCHED_PIN_CTR, count) ==
             OPTIGA_SUCCESS;
}

#endif  // SECURE_MODE
