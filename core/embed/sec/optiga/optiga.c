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

#include <trezor_rtl.h>

#include <sec/optiga.h>
#include <sec/optiga_commands.h>
#include <sec/optiga_transport.h>
#include "hash_to_curve.h"
#include "hmac.h"
#include "memzero.h"
#include "rand.h"
#include "storage.h"

#ifdef KERNEL_MODE

// Counter-protected PIN secret and reset key for OID_STRETCHED_PIN_CTR (OID
// 0xF1D0).
#define OID_PIN_SECRET (OPTIGA_OID_DATA + 0)

// Digest of the stretched PIN (OID 0xF1D4).
#define OID_STRETCHED_PIN (OPTIGA_OID_DATA + 4)

// Counter-protected key for HMAC-SHA256 PIN stretching step (OID 0xF1D8).
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

// The throttling delay when the security event counter is at its maximum.
#define OPTIGA_T_MAX_MS 5000

// Value of the PIN counter when it is reset.
static const uint8_t COUNTER_RESET[] = {0, 0, 0, 0, 0, 0, 0, PIN_MAX_TRIES};

// Value of the PIN counter with one extra attempt needed in optiga_pin_set().
static const uint8_t COUNTER_RESET_EXTRA[] = {0, 0, 0, 0,
                                              0, 0, 0, PIN_MAX_TRIES + 1};

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

optiga_sign_result optiga_sign(uint8_t index, const uint8_t *digest,
                               size_t digest_size, uint8_t *signature,
                               size_t max_sig_size, size_t *sig_size) {
  if (index >= OPTIGA_ECC_KEY_COUNT) {
    return OPTIGA_SIGN_ERROR;
  }

  optiga_result res =
      optiga_calc_sign(OPTIGA_OID_ECC_KEY + index, digest, digest_size,
                       &signature[2], max_sig_size - 2, sig_size);
  if (res != OPTIGA_SUCCESS) {
    uint8_t error_code = 0;
    if (res == OPTIGA_ERR_CMD &&
        optiga_get_error_code(&error_code) == OPTIGA_SUCCESS &&
        error_code == OPTIGA_ERR_CODE_ACCESS_COND) {
      return OPTIGA_SIGN_INACCESSIBLE;
    } else {
      return OPTIGA_SIGN_ERROR;
    }
  }

  // Add sequence tag and length.
  if (*sig_size >= 0x80) {
    // Length not supported.
    return OPTIGA_SIGN_ERROR;
  }
  signature[0] = 0x30;
  signature[1] = *sig_size;
  *sig_size += 2;
  return OPTIGA_SIGN_SUCCESS;
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

uint32_t optiga_estimate_time_ms(storage_pin_op_t op) {
  uint8_t sec = 0;
  if (!optiga_read_sec(&sec)) {
    return UINT32_MAX;
  }

  // Heuristic: The SEC will increase by about 4 during the operation up to a
  // maximum of 255.
  sec = (sec < 255 - 4) ? sec + 4 : 255;

  // If the SEC is above 127, then Optiga introduces a throttling delay before
  // the execution of each protected command. The delay grows propotionally to
  // the SEC value up to a maximum delay of OPTIGA_T_MAX_MS.
  uint32_t throttling_delay =
      sec > 127 ? (sec - 127) * OPTIGA_T_MAX_MS / 128 : 0;

  // To estimate the overall time of the PIN operation we multiply the
  // throttling delay by the number of protected Optiga commands and add the
  // time required to execute all Optiga commands without throttling delays.
  switch (op) {
    case STORAGE_PIN_OP_SET:
      return throttling_delay * 6 + 1300;
    case STORAGE_PIN_OP_VERIFY:
      return throttling_delay * 7 + 1000;
    case STORAGE_PIN_OP_CHANGE:
      return throttling_delay * 13 + 2300;
    default:
      return 0;
  }
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

static bool optiga_pin_init_stretch(void) {
  // Generate a new key in OID_PIN_CMAC.
  if (optiga_gen_sym_key(OPTIGA_AES_256, OPTIGA_KEY_USAGE_ENC, OID_PIN_CMAC) !=
      OPTIGA_SUCCESS) {
    return false;
  }

  // Generate a new key in OID_PIN_ECDH.
  uint8_t public_key[6 + 65] = {0};
  size_t size = 0;
  return optiga_gen_key_pair(OPTIGA_CURVE_P256, OPTIGA_KEY_USAGE_KEYAGREE,
                             OID_PIN_ECDH, public_key, sizeof(public_key),
                             &size) == OPTIGA_SUCCESS;
}

static bool optiga_pin_stretch_common(
    optiga_ui_progress_t ui_progress, HMAC_SHA256_CTX *ctx,
    const uint8_t input[OPTIGA_PIN_SECRET_SIZE], bool version4) {
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

  ui_progress();

  hmac_sha256_Update(ctx, buffer, size);

end:
  memzero(encoded_point, sizeof(encoded_point));
  memzero(buffer, sizeof(buffer));
  return ret;
}

static bool optiga_pin_stretch_secret_v4(
    optiga_ui_progress_t ui_progress, uint8_t secret[OPTIGA_PIN_SECRET_SIZE]) {
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

  bool ret = optiga_pin_stretch_common(ui_progress, &ctx, secret, true);
  if (ret) {
    hmac_sha256_Final(&ctx, secret);
  }

  memzero(&ctx, sizeof(ctx));
  return ret;
}

static bool optiga_pin_stretch_cmac_ecdh(
    optiga_ui_progress_t ui_progress,
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

    if (!optiga_pin_stretch_common(ui_progress, &ctx, digest, false)) {
      ret = false;
      goto end;
    }

    hmac_sha256_Final(&ctx, stretched_pin);
  }

end:
  memzero(digest, sizeof(digest));
  memzero(&ctx, sizeof(ctx));
  return ret;
}

bool optiga_pin_set(optiga_ui_progress_t ui_progress,
                    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  optiga_set_ui_progress(ui_progress);

  bool ret = true;
  if (!optiga_pin_init_metadata() || !optiga_pin_init_stretch()) {
    ret = false;
    goto end;
  }

  ui_progress();

  // Stretch the PIN more with stretching secrets from the Optiga. This step
  // ensures that if an attacker extracts the value of OID_STRETCHED_PIN or
  // OID_PIN_SECRET, then it cannot be used to conduct an offline brute-force
  // search for the PIN.
  if (!optiga_pin_stretch_cmac_ecdh(ui_progress, stretched_pin)) {
    ret = false;
    goto end;
  }

  // Generate and store the counter-protected PIN secret.
  uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE] = {0};
  if (optiga_get_random(pin_secret, sizeof(pin_secret)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }
  random_xor(pin_secret, sizeof(pin_secret));

  if (optiga_set_data_object(OID_PIN_SECRET, false, pin_secret,
                             sizeof(pin_secret)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  // Generate the key for the HMAC-SHA256 PIN stretching step.
  uint8_t pin_hmac[OPTIGA_PIN_SECRET_SIZE] = {0};
  if (optiga_get_random(pin_hmac, sizeof(pin_hmac)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }
  random_xor(pin_hmac, sizeof(pin_hmac));

  // Authorise using OID_PIN_SECRET so that we can write to OID_STRETCHED_PIN
  // and OID_STRETCHED_PIN_CTR.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET, pin_secret,
                            sizeof(pin_secret)) != OPTIGA_SUCCESS) {
    ret = false;
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
  if (optiga_set_data_object(OID_STRETCHED_PIN, false, digest,
                             sizeof(digest)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  // Initialize the counter which limits the guesses at OID_STRETCHED_PIN with
  // one extra attempt that we will use up in the next step.
  if (optiga_set_data_object(OID_STRETCHED_PIN_CTR, false, COUNTER_RESET_EXTRA,
                             sizeof(COUNTER_RESET_EXTRA)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  ui_progress();

  // Authorise using OID_STRETCHED_PIN so that we can write to OID_PIN_HMAC and
  // OID_PIN_HMAC_CTR.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PIN, digest,
                            sizeof(digest)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  // Initialize the key for HMAC-SHA256 PIN stretching.
  if (optiga_set_data_object(OID_PIN_HMAC, false, pin_hmac, sizeof(pin_hmac)) !=
      OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  // Initialize the PIN counter which limits the use of OID_PIN_HMAC.
  if (optiga_set_data_object(OID_PIN_HMAC_CTR, false, COUNTER_RESET,
                             sizeof(COUNTER_RESET)) != OPTIGA_SUCCESS) {
    ret = false;
    goto end;
  }

  ui_progress();

  // Stretch the PIN more with the counter-protected PIN secret. This method
  // ensures that if the user chooses a high-entropy PIN, then even if the
  // Optiga and its communication link is completely compromised, it will not
  // reduce the security of their device any more than if the Optiga was not
  // integrated into the device in the first place.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, pin_secret,
              sizeof(pin_secret), stretched_pin);

end:
  memzero(hmac_buffer, sizeof(hmac_buffer));
  memzero(pin_hmac, sizeof(pin_hmac));
  memzero(pin_secret, sizeof(pin_secret));
  memzero(digest, sizeof(digest));
  optiga_clear_auto_state(OID_PIN_SECRET);
  optiga_clear_auto_state(OID_STRETCHED_PIN);
  optiga_set_ui_progress(NULL);
  return ret;
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
  if (!optiga_pin_stretch_secret_v4(ui_progress, stretched_pin)) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Authorise using OID_STRETCHED_PIN so that we can read from OID_PIN_SECRET.
  optiga_result res =
      optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PIN,
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

  ui_progress();

  // Authorise using OID_PIN_SECRET so that we can write to
  // OID_STRETCHED_PIN_CTR.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET, out_secret,
                            OPTIGA_PIN_SECRET_SIZE) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  ui_progress();

  // Combine the value of OID_PIN_SECRET with the PIN-derived secret and
  // stretching secrets from the Optiga.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);
  if (!optiga_pin_stretch_secret_v4(ui_progress, out_secret)) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Combine the stretched master secret with the PIN-derived secret to derive
  // the output secret.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);

end:
  memzero(stretched_pin, sizeof(stretched_pin));
  optiga_clear_auto_state(OID_STRETCHED_PIN);
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

optiga_pin_result optiga_pin_verify(
    optiga_ui_progress_t ui_progress,
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  optiga_set_ui_progress(ui_progress);
  optiga_pin_result ret = OPTIGA_PIN_SUCCESS;

  // Stretch the PIN more with stretching secrets from the Optiga.
  if (!optiga_pin_stretch_cmac_ecdh(ui_progress, stretched_pin)) {
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

  // Authorise using OID_STRETCHED_PIN so that we can read from OID_PIN_SECRET
  // and reset OID_PIN_HMAC_CTR.
  optiga_result res = optiga_set_auto_state(
      OPTIGA_OID_SESSION_CTX, OID_STRETCHED_PIN, digest, sizeof(digest));
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

  ui_progress();

  // Reset the counter which limits the use of OID_PIN_HMAC.
  if (optiga_set_data_object(OID_PIN_HMAC_CTR, false, COUNTER_RESET,
                             sizeof(COUNTER_RESET)) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Read the counter-protected PIN secret from OID_PIN_SECRET.
  uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE] = {0};
  size_t size = 0;
  if (optiga_get_data_object(OID_PIN_SECRET, false, pin_secret,
                             OPTIGA_PIN_SECRET_SIZE, &size) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Stretch the PIN more with the counter-protected PIN secret.
  hmac_sha256(stretched_pin, OPTIGA_PIN_SECRET_SIZE, pin_secret, size,
              stretched_pin);

  // Authorise using OID_PIN_SECRET so that we can reset OID_STRETCHED_PIN_CTR.
  if (optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET, pin_secret,
                            sizeof(pin_secret)) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  // Reset the counter which limits the guesses at OID_STRETCHED_PIN.
  if (optiga_set_data_object(OID_STRETCHED_PIN_CTR, false, COUNTER_RESET,
                             sizeof(COUNTER_RESET)) != OPTIGA_SUCCESS) {
    ret = OPTIGA_PIN_ERROR;
    goto end;
  }

  ui_progress();

end:
  memzero(pin_secret, sizeof(pin_secret));
  memzero(digest, sizeof(digest));
  optiga_clear_auto_state(OID_STRETCHED_PIN);
  optiga_clear_auto_state(OID_PIN_SECRET);
  optiga_set_ui_progress(NULL);
  return ret;
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

#endif  // KERNEL_MODE
