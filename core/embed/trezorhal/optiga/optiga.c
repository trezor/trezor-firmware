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

#include "optiga.h"
#include <string.h>
#include "hash_to_curve.h"
#include "hmac.h"
#include "memzero.h"
#include "optiga_commands.h"
#include "rand.h"
#include "storage.h"

// Counter-protected PIN secret and reset key for OID_STRETCHED_PIN_CTR (OID
// 0xF1D0).
#define OID_PIN_SECRET (OPTIGA_OID_DATA + 0)

// Digest of the stretched PIN (OID 0xF1D4).
#define OID_STRETCHED_PIN (OPTIGA_OID_DATA + 4)

// Counter-protected key for HMAC-SHA256 PIN stretching step (OID 0xF1D5).
#define OID_PIN_HMAC (OPTIGA_OID_DATA + 8)

// Counter which limits the guesses at OID_STRETCHED_PIN (OID 0xE120).
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
#define PIN_STRETCH_ITERATIONS 2

// Value of the PIN counter when it is reset.
static const uint8_t COUNTER_RESET[] = {0, 0, 0, 0, 0, 0, 0, PIN_MAX_TRIES};

// Initial value of the counter which limits the total number of PIN stretching
// operations. The limit is 600000 stretching operations, which equates to
// 300000 / PIN_STRETCH_ITERATIONS unlock operations over the lifetime of the
// device.
static const uint8_t PIN_TOTAL_CTR_INIT[] = {0, 0, 0, 0, 0, 0x09, 0x27, 0xC0};

static const optiga_metadata_item TYPE_AUTOREF =
    OPTIGA_META_VALUE(OPTIGA_DATA_TYPE_AUTOREF);
static const optiga_metadata_item TYPE_PRESSEC =
    OPTIGA_META_VALUE(OPTIGA_DATA_TYPE_PRESSEC);
static const optiga_metadata_item ACCESS_STRETCHED_PIN =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO, OID_STRETCHED_PIN);
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

int optiga_sign(uint8_t index, const uint8_t *digest, size_t digest_size,
                uint8_t *signature, size_t max_sig_size, size_t *sig_size) {
  if (index >= OPTIGA_ECC_KEY_COUNT) {
    return OPTIGA_ERR_PARAM;
  }

  optiga_result ret =
      optiga_calc_sign(OPTIGA_OID_ECC_KEY + index, digest, digest_size,
                       &signature[2], max_sig_size - 2, sig_size);
  if (ret == OPTIGA_ERR_CMD) {
    uint8_t error_code = 0;
    (void)optiga_get_error_code(&error_code);
    return error_code + OPTIGA_COMMAND_ERROR_OFFSET;
  }

  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  // Add sequence tag and length.
  if (*sig_size >= 0x80) {
    // Length not supported.
    return OPTIGA_ERR_SIZE;
  }
  signature[0] = 0x30;
  signature[1] = *sig_size;
  *sig_size += 2;
  return OPTIGA_SUCCESS;
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

static bool read_metadata(uint16_t oid, optiga_metadata *metadata) {
  static uint8_t serialized[OPTIGA_MAX_METADATA_SIZE] = {0};
  size_t size = 0;
  optiga_result ret =
      optiga_get_data_object(oid, true, serialized, sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    return false;
  }

  ret = optiga_parse_metadata(serialized, size, metadata);
  return OPTIGA_SUCCESS == ret;
}

static bool write_metadata(uint16_t oid, const optiga_metadata *metadata) {
  uint8_t serialized[OPTIGA_MAX_METADATA_SIZE] = {0};
  size_t size = 0;

  optiga_result ret = optiga_serialize_metadata(metadata, serialized,
                                                sizeof(serialized), &size);
  if (OPTIGA_SUCCESS != ret) {
    return false;
  }

  ret = optiga_set_data_object(oid, true, serialized, size);
  return OPTIGA_SUCCESS == ret;
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

static bool optiga_pin_init_metadata(void) {
  optiga_metadata metadata = {0};

  // Set metadata for counter-protected PIN secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = ACCESS_STRETCHED_PIN;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_PIN_SECRET, &metadata)) {
    return false;
  }

  // Set metadata for stretched PIN.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_PIN_SECRET;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_STRETCHED_PIN_CTR;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_STRETCHED_PIN, &metadata)) {
    return false;
  }

  // Set metadata for HMAC-SHA256 PIN stretching secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_STRETCHED_PIN;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_HMAC_CTR;
  metadata.data_type = TYPE_PRESSEC;
  if (!optiga_set_metadata(OID_PIN_HMAC, &metadata)) {
    return false;
  }

  // Set metadata for the counter of guesses at OID_STRETCHED_PIN.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_PIN_SECRET;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!optiga_set_metadata(OID_STRETCHED_PIN_CTR, &metadata)) {
    return false;
  }

  // Set metadata for the counter of OID_PIN_HMAC uses.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_STRETCHED_PIN;
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
        optiga_set_data_object(OID_PIN_TOTAL_CTR, false, PIN_TOTAL_CTR_INIT,
                               sizeof(PIN_TOTAL_CTR_INIT));
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

static int optiga_pin_init_stretch(void) {
  // Generate a new key in OID_PIN_CMAC.
  optiga_result res =
      optiga_gen_sym_key(OPTIGA_AES_256, OPTIGA_KEY_USAGE_ENC, OID_PIN_CMAC);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Generate a new key in OID_PIN_ECDH.
  uint8_t public_key[6 + 65] = {0};
  size_t size = 0;
  res =
      optiga_gen_key_pair(OPTIGA_CURVE_P256, OPTIGA_KEY_USAGE_KEYAGREE,
                          OID_PIN_ECDH, public_key, sizeof(public_key), &size);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  return OPTIGA_SUCCESS;
}

static int optiga_pin_stretch_common(
    OPTIGA_UI_PROGRESS ui_progress, HMAC_SHA256_CTX *ctx,
    const uint8_t input[OPTIGA_PIN_SECRET_SIZE], bool version4) {
  // Implements the functionality that is common to
  // optiga_pin_stretch_cmac_ecdh() and the legacy function
  // optiga_pin_stretch_secret_v4().

  uint8_t buffer[ENCRYPT_SYM_PREFIX_SIZE + OPTIGA_PIN_SECRET_SIZE] = {0};
  size_t size = 0;

  // Combine intermediate result with OID_PIN_CMAC.
  optiga_result res =
      optiga_encrypt_sym(OPTIGA_SYM_MODE_CMAC, OID_PIN_CMAC, input,
                         OPTIGA_PIN_SECRET_SIZE, buffer, sizeof(buffer), &size);
  if (res != OPTIGA_SUCCESS) {
    memzero(buffer, sizeof(buffer));
    return res;
  }

  hmac_sha256_Update(ctx, buffer, size);

  if (version4) {
    // Combine intermediate result with OID_PIN_HMAC
    res = optiga_encrypt_sym(OPTIGA_SYM_MODE_HMAC_SHA256, OID_PIN_HMAC_V4,
                             input, OPTIGA_PIN_SECRET_SIZE, buffer,
                             sizeof(buffer), &size);
    if (res != OPTIGA_SUCCESS) {
      memzero(buffer, sizeof(buffer));
      return res;
    }

    hmac_sha256_Update(ctx, buffer, size);
  }

  // Combine intermediate result with OID_PIN_ECDH
  uint8_t encoded_point[BIT_STRING_HEADER_SIZE + 65] = {0x03, 0x42, 0x00};
  if (!hash_to_curve_optiga(input, &encoded_point[BIT_STRING_HEADER_SIZE])) {
    memzero(buffer, sizeof(buffer));
    return -1;
  }
  res = optiga_calc_ssec(OPTIGA_CURVE_P256, OID_PIN_ECDH, encoded_point,
                         sizeof(encoded_point), buffer, sizeof(buffer), &size);
  memzero(encoded_point, sizeof(encoded_point));
  if (res != OPTIGA_SUCCESS) {
    memzero(buffer, sizeof(buffer));
    return res;
  }

  ui_progress(250);

  hmac_sha256_Update(ctx, buffer, size);
  memzero(buffer, sizeof(buffer));
  return OPTIGA_SUCCESS;
}

static int optiga_pin_stretch_secret_v4(
    OPTIGA_UI_PROGRESS ui_progress, uint8_t secret[OPTIGA_PIN_SECRET_SIZE]) {
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

  optiga_result res =
      optiga_pin_stretch_common(ui_progress, &ctx, secret, true);
  if (res != OPTIGA_SUCCESS) {
    memzero(&ctx, sizeof(ctx));
    return res;
  }

  hmac_sha256_Final(&ctx, secret);
  memzero(&ctx, sizeof(ctx));
  return OPTIGA_SUCCESS;
}

static int optiga_pin_stretch_cmac_ecdh(
    OPTIGA_UI_PROGRESS ui_progress,
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
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

  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};
  HMAC_SHA256_CTX ctx = {0};
  for (int i = 0; i < PIN_STRETCH_ITERATIONS; ++i) {
    // Process the stretched PIN using a one-way function before sending it to
    // the Optiga. This ensures that in the unlikely case of an attacker
    // recording communication between the MCU and Optiga, they will not gain
    // knowledge of the stretched PIN.
    hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);
    hmac_sha256_Init(&ctx, stretched_pin, OPTIGA_PIN_SECRET_SIZE);

    optiga_result res =
        optiga_pin_stretch_common(ui_progress, &ctx, digest, false);
    if (res != OPTIGA_SUCCESS) {
      memzero(digest, sizeof(digest));
      memzero(&ctx, sizeof(ctx));
      return res;
    }

    hmac_sha256_Final(&ctx, stretched_pin);
  }

  memzero(digest, sizeof(digest));
  memzero(&ctx, sizeof(ctx));
  return OPTIGA_SUCCESS;
}

int optiga_pin_set(OPTIGA_UI_PROGRESS ui_progress,
                   uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  int res = OPTIGA_SUCCESS;
  if (!optiga_pin_init_metadata()) {
    res = -1;
    goto end;
  }

  res = optiga_pin_init_stretch();
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  ui_progress(300);

  // Stretch the PIN more with stretching secrets from the Optiga. This step
  // ensures that if an attacker extracts the value of OID_STRETCHED_PIN or
  // OID_PIN_SECRET, then it cannot be used to conduct an offline brute-force
  // search for the PIN.
  res = optiga_pin_stretch_cmac_ecdh(ui_progress, stretched_pin);
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  // Generate and store the counter-protected PIN secret.
  uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE] = {0};
  res = optiga_get_random(pin_secret, sizeof(pin_secret));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }
  random_xor(pin_secret, sizeof(pin_secret));

  res = optiga_set_data_object(OID_PIN_SECRET, false, pin_secret,
                               sizeof(pin_secret));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  // Generate the key for the HMAC-SHA256 PIN stretching step.
  uint8_t pin_hmac[OPTIGA_PIN_SECRET_SIZE] = {0};
  res = optiga_get_random(pin_hmac, sizeof(pin_hmac));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }
  random_xor(pin_hmac, sizeof(pin_hmac));

  // Authorise using OID_PIN_SECRET so that we can write to OID_STRETCHED_PIN
  // and OID_STRETCHED_PIN_CTR.
  res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET,
                              pin_secret, sizeof(pin_secret));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  // Process the stretched PIN using a one-way function before using it in the
  // operation that will be executed in Optiga during verification. This ensures
  // that in the unlikely case of an attacker recording communication between
  // the MCU and Optiga, they will not gain knowledge of the stretched PIN.
  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);

  // Compute the operation that will be executed in Optiga during verification.
  uint8_t hmac_buffer[ENCRYPT_SYM_PREFIX_SIZE + OPTIGA_PIN_SECRET_SIZE] = {
      0x61, 0x00, 0x20};
  hmac_sha256(pin_hmac, sizeof(pin_hmac), digest, sizeof(digest),
              &hmac_buffer[ENCRYPT_SYM_PREFIX_SIZE]);

  // Stretch the PIN with the result.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, hmac_buffer,
              sizeof(hmac_buffer), stretched_pin);

  // Process the stretched PIN using a one-way function before sending it to the
  // Optiga. This ensures that in the unlikely case of an attacker recording
  // communication between the MCU and Optiga, they will not gain knowledge of
  // the stretched PIN.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);

  // Store the digest of the stretched PIN in OID_STRETCHED_PIN.
  res =
      optiga_set_data_object(OID_STRETCHED_PIN, false, digest, sizeof(digest));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  // Initialize the counter which limits the guesses at OID_STRETCHED_PIN so
  // that we can authorise using OID_STRETCHED_PIN.
  res = optiga_set_data_object(OID_STRETCHED_PIN_CTR, false, COUNTER_RESET,
                               sizeof(COUNTER_RESET));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  ui_progress(250);

  // Authorise using OID_STRETCHED_PIN so that we can write to OID_PIN_HMAC and
  // OID_PIN_HMAC_CTR.
  res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PIN, digest,
                              sizeof(digest));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  // Initialize the key for HMAC-SHA256 PIN stretching.
  res = optiga_set_data_object(OID_PIN_HMAC, false, pin_hmac, sizeof(pin_hmac));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  // Initialize the counter which limits the guesses at OID_STRETCHED_PIN again,
  // since we just depleted one attempt.
  res = optiga_set_data_object(OID_STRETCHED_PIN_CTR, false, COUNTER_RESET,
                               sizeof(COUNTER_RESET));
  optiga_clear_auto_state(OID_PIN_SECRET);
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  // Initialize the PIN counter which limits the use of OID_PIN_HMAC.
  res = optiga_set_data_object(OID_PIN_HMAC_CTR, false, COUNTER_RESET,
                               sizeof(COUNTER_RESET));
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

  ui_progress(250);

  // Stretch the PIN more with the counter-protected PIN secret. This method
  // ensures that if the user chooses a high-entropy PIN, then even if the
  // Optiga and its communication link is completely compromised, it will not
  // reduce the security of their device any more than if the Optiga was not
  // integrated into the device in the first place.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, pin_secret,
              sizeof(pin_secret), stretched_pin);
  if (res != OPTIGA_SUCCESS) {
    goto end;
  }

end:
  memzero(hmac_buffer, sizeof(hmac_buffer));
  memzero(pin_hmac, sizeof(pin_hmac));
  memzero(pin_secret, sizeof(pin_secret));
  memzero(digest, sizeof(digest));
  optiga_clear_auto_state(OID_PIN_SECRET);
  optiga_clear_auto_state(OID_STRETCHED_PIN);
  return res;
}

int optiga_pin_verify_v4(OPTIGA_UI_PROGRESS ui_progress,
                         const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
                         uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]) {
  // Legacy PIN verification method used in storage version 3 and 4.

  // Process the PIN-derived secret using a one-way function before sending it
  // to the Optiga.
  uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, NULL, 0, stretched_pin);

  // Combine the result with stretching secrets from the Optiga.
  optiga_result res = optiga_pin_stretch_secret_v4(ui_progress, stretched_pin);
  if (res != OPTIGA_SUCCESS) {
    memzero(stretched_pin, sizeof(stretched_pin));
    return res;
  }

  // Authorise using OID_STRETCHED_PIN so that we can read from OID_PIN_SECRET.
  res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PIN,
                              stretched_pin, sizeof(stretched_pin));
  memzero(stretched_pin, sizeof(stretched_pin));
  if (res == OPTIGA_ERR_CMD) {
    uint8_t error_code = 0;
    (void)optiga_get_error_code(&error_code);
    return error_code + OPTIGA_COMMAND_ERROR_OFFSET;
  }

  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Read the master secret from OID_PIN_SECRET.
  size_t size = 0;
  res = optiga_get_data_object(OID_PIN_SECRET, false, out_secret,
                               OPTIGA_PIN_SECRET_SIZE, &size);
  optiga_clear_auto_state(OID_STRETCHED_PIN);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  if (size != OPTIGA_PIN_SECRET_SIZE) {
    return OPTIGA_ERR_SIZE;
  }

  ui_progress(200);

  // Authorise using OID_PIN_SECRET so that we can write to OID_PIN_COUNTER.
  res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET,
                              out_secret, OPTIGA_PIN_SECRET_SIZE);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  ui_progress(200);

  // Combine the value of OID_PIN_SECRET with the PIN-derived secret and
  // stretching secrets from the Optiga.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);
  res = optiga_pin_stretch_secret_v4(ui_progress, out_secret);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Combine the stretched master secret with the PIN-derived secret to derive
  // the output secret.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);
  return OPTIGA_SUCCESS;
}

static int optiga_pin_stretch_hmac(
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
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
  memzero(digest, sizeof(digest));
  if (res != OPTIGA_SUCCESS) {
    uint8_t error_code = 0;
    (void)optiga_get_error_code(&error_code);
    if (error_code + OPTIGA_COMMAND_ERROR_OFFSET ==
        OPTIGA_ERR_ACCESS_COND_NOT_SAT) {
      return OPTIGA_ERR_COUNTER_EXCEEDED;
    } else {
      return error_code + OPTIGA_COMMAND_ERROR_OFFSET;
    }
  }

  // Stretch the PIN with the result.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, hmac_buffer, size,
              stretched_pin);
  memzero(hmac_buffer, sizeof(hmac_buffer));
  return OPTIGA_SUCCESS;
}

int optiga_pin_verify(OPTIGA_UI_PROGRESS ui_progress,
                      uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  // Stretch the PIN more with stretching secrets from the Optiga.
  optiga_result res = optiga_pin_stretch_cmac_ecdh(ui_progress, stretched_pin);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  res = optiga_pin_stretch_hmac(stretched_pin);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Process the stretched PIN using a one-way function before sending it to the
  // Optiga.
  uint8_t digest[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, NULL, 0, digest);

  // Authorise using OID_STRETCHED_PIN so that we can read from OID_PIN_SECRET
  // and reset OID_PIN_HMAC_CTR.
  res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PIN, digest,
                              sizeof(digest));
  memzero(digest, sizeof(digest));
  if (res == OPTIGA_ERR_CMD) {
    uint8_t error_code = 0;
    (void)optiga_get_error_code(&error_code);
    return error_code + OPTIGA_COMMAND_ERROR_OFFSET;
  }

  ui_progress(200);

  // Reset the counter which limits the use of OID_PIN_HMAC.
  res = optiga_set_data_object(OID_PIN_HMAC_CTR, false, COUNTER_RESET,
                               sizeof(COUNTER_RESET));
  if (res != OPTIGA_SUCCESS) {
    optiga_clear_auto_state(OID_STRETCHED_PIN);
    return res;
  }

  // Read the counter-protected PIN secret from OID_PIN_SECRET.
  uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE] = {0};
  size_t size = 0;
  res = optiga_get_data_object(OID_PIN_SECRET, false, pin_secret,
                               OPTIGA_PIN_SECRET_SIZE, &size);
  optiga_clear_auto_state(OID_STRETCHED_PIN);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Stretch the PIN more with the counter-protected PIN secret.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, pin_secret, size,
              stretched_pin);

  // Authorise using OID_PIN_SECRET so that we can reset OID_STRETCHED_PIN_CTR.
  res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET,
                              pin_secret, sizeof(pin_secret));
  memzero(pin_secret, sizeof(pin_secret));
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Reset the counter which limits the guesses at OID_STRETCHED_PIN.
  res = optiga_set_data_object(OID_STRETCHED_PIN_CTR, false, COUNTER_RESET,
                               sizeof(COUNTER_RESET));
  optiga_clear_auto_state(OID_PIN_SECRET);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  ui_progress(200);

  return OPTIGA_SUCCESS;
}

static int optiga_get_counter(uint16_t oid, uint32_t *ctr) {
  uint8_t counter[8] = {0};
  size_t counter_size = 0;
  optiga_result res = optiga_get_data_object(oid, false, counter,
                                             sizeof(counter), &counter_size);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  if (counter_size != sizeof(counter)) {
    return OPTIGA_ERR_SIZE;
  }

  *ctr = counter[0];
  *ctr = (*ctr << 8) + counter[1];
  *ctr = (*ctr << 8) + counter[2];
  *ctr = (*ctr << 8) + counter[3];

  return OPTIGA_SUCCESS;
}

int optiga_pin_get_fails_v4(uint32_t *ctr) {
  return optiga_get_counter(OID_STRETCHED_PIN_CTR, ctr);
}

int optiga_pin_get_fails(uint32_t *ctr) {
  uint32_t ctr1 = 0;
  uint32_t ctr2 = 0;
  if (optiga_get_counter(OID_PIN_HMAC_CTR, &ctr1) != OPTIGA_SUCCESS ||
      optiga_get_counter(OID_STRETCHED_PIN_CTR, &ctr2) != OPTIGA_SUCCESS) {
    return -1;
  }

  // Ensure that the counters are in sync.
  if (ctr1 > ctr2) {
    if (optiga_count_data_object(OID_STRETCHED_PIN_CTR, ctr1 - ctr2) !=
        OPTIGA_SUCCESS) {
      return -1;
    }
    *ctr = ctr1;
  } else if (ctr2 > ctr1) {
    if (optiga_count_data_object(OID_PIN_HMAC_CTR, ctr2 - ctr1) !=
        OPTIGA_SUCCESS) {
      return -1;
    }
    *ctr = ctr2;
  } else {
    *ctr = ctr2;
  }
  return OPTIGA_SUCCESS;
}

int optiga_pin_fails_increase_v4(uint32_t count) {
  if (count > 0xff) {
    return OPTIGA_ERR_PARAM;
  }

  return optiga_count_data_object(OID_STRETCHED_PIN_CTR, count);
}

int optiga_pin_fails_increase(uint32_t count) {
  if (count > 0xff) {
    return OPTIGA_ERR_PARAM;
  }

  if (optiga_count_data_object(OID_PIN_HMAC_CTR, count) != OPTIGA_SUCCESS ||
      optiga_count_data_object(OID_STRETCHED_PIN_CTR, count) !=
          OPTIGA_SUCCESS) {
    return -1;
  }
  return OPTIGA_SUCCESS;
}
