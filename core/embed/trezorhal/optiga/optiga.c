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

// PIN counter reset key / Master secret (OID 0xF1D0).
#define OID_PIN_SECRET (OPTIGA_OID_DATA + 0)

// PIN counter (OID 0xE120).
#define OID_PIN_COUNTER (OPTIGA_OID_COUNTER + 0)

// PIN stretching counter (OID 0xE121).
#define OID_PIN_STRETCH_COUNTER (OPTIGA_OID_COUNTER + 1)

// Stretched PIN (OID 0xF1D4).
#define OID_STRETCHED_PIN (OPTIGA_OID_DATA + 4)

// Key for HMAC-SHA256 PIN stretching step (OID 0xF1D1).
#define OID_PIN_HMAC (OPTIGA_OID_DATA + 1)

// Key for AES-CMAC PIN stretching step (OID 0xE200).
#define OID_PIN_CMAC OPTIGA_OID_SYM_KEY

// Key for ECDH PIN stretching step (OID 0xE0F3).
#define OID_PIN_ECDH (OPTIGA_OID_ECC_KEY + 3)

// The number of times the stretching is repeated in each PIN processing phase.
#define PIN_STRETCH_ITERATIONS 1

// Value of the PIN counter when it is reset.
static const uint8_t COUNTER_RESET[] = {0, 0, 0, 0, 0, 0, 0, PIN_MAX_TRIES};

// Value of the PIN stretching counter when it is initialized. The limit is
// 600000 stretching operations, which equates to
// 100000 / PIN_STRETCH_ITERATIONS unlock operations.
static const uint8_t STRETCH_COUNTER_INIT[] = {0, 0, 0, 0, 0, 0x09, 0x27, 0xC0};

static const optiga_metadata_item TYPE_AUTOREF = {
    (const uint8_t[]){OPTIGA_DATA_TYPE_AUTOREF}, 1};
static const optiga_metadata_item TYPE_PRESSEC = {
    (const uint8_t[]){OPTIGA_DATA_TYPE_PRESSEC}, 1};
static const optiga_metadata_item ACCESS_STRETCHED_PIN =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO, OID_STRETCHED_PIN);
static const optiga_metadata_item ACCESS_PIN_SECRET =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_AUTO, OID_PIN_SECRET);
static const optiga_metadata_item ACCESS_PIN_COUNTER =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_LUC, OID_PIN_COUNTER);
static const optiga_metadata_item ACCESS_PIN_STRETCH_COUNTER =
    OPTIGA_ACCESS_CONDITION(OPTIGA_ACCESS_COND_LUC, OID_PIN_STRETCH_COUNTER);

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
    optiga_get_error_code(&error_code);
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

  // If the metadata aren't locked, then lock them.
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

  return true;
}

static bool optiga_pin_init_metadata(void) {
  optiga_metadata metadata = {0};

  // Set metadata for PIN counter reset key / Master secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = ACCESS_STRETCHED_PIN;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_PIN_SECRET, &metadata)) {
    return false;
  }

  // Set metadata for PIN counter.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_PIN_SECRET;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!optiga_set_metadata(OID_PIN_COUNTER, &metadata)) {
    return false;
  }

  // Initialize the PIN stretching counter if write access is possible.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  if (write_metadata(OID_PIN_STRETCH_COUNTER, &metadata)) {
    optiga_result res = optiga_set_data_object(OID_PIN_STRETCH_COUNTER, false,
                                               STRETCH_COUNTER_INIT,
                                               sizeof(STRETCH_COUNTER_INIT));
    if (res != OPTIGA_SUCCESS) {
      return false;
    }
  }

  // Set metadata for PIN stretching counter.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_ALWAYS;
  metadata.execute = OPTIGA_META_ACCESS_ALWAYS;
  if (!optiga_set_metadata(OID_PIN_STRETCH_COUNTER, &metadata)) {
    return false;
  }

  // Set metadata for stretched PIN.
  memzero(&metadata, sizeof(metadata));
  metadata.change = ACCESS_PIN_SECRET;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_COUNTER;
  metadata.data_type = TYPE_AUTOREF;
  if (!optiga_set_metadata(OID_STRETCHED_PIN, &metadata)) {
    return false;
  }

  // Set metadata for AES-CMAC PIN stretching secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_STRETCH_COUNTER;
  metadata.key_usage = OPTIGA_META_KEY_USE_ENC;
  if (!optiga_set_metadata(OID_PIN_CMAC, &metadata)) {
    return false;
  }

  // Set metadata for ECDH PIN stretching secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_STRETCH_COUNTER;
  metadata.key_usage = OPTIGA_META_KEY_USE_KEYAGREE;
  if (!optiga_set_metadata(OID_PIN_ECDH, &metadata)) {
    return false;
  }

  // Generate and store the HMAC PIN stretching secret in OID_PIN_HMAC, if write
  // access is possible.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_ALWAYS;
  if (write_metadata(OID_PIN_HMAC, &metadata)) {
    uint8_t secret[OPTIGA_PIN_SECRET_SIZE] = {0};
    optiga_result res = optiga_get_random(secret, sizeof(secret));
    if (res != OPTIGA_SUCCESS) {
      return false;
    }
    random_xor(secret, sizeof(secret));

    res = optiga_set_data_object(OID_PIN_HMAC, false, secret, sizeof(secret));
    memzero(secret, sizeof(secret));
    if (res != OPTIGA_SUCCESS) {
      return false;
    }
  }

  // Set metadata for HMAC-SHA256 PIN stretching secret.
  memzero(&metadata, sizeof(metadata));
  metadata.change = OPTIGA_META_ACCESS_NEVER;
  metadata.read = OPTIGA_META_ACCESS_NEVER;
  metadata.execute = ACCESS_PIN_STRETCH_COUNTER;
  metadata.data_type = TYPE_PRESSEC;
  if (!optiga_set_metadata(OID_PIN_HMAC, &metadata)) {
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

static int optiga_pin_stretch_secret(OPTIGA_UI_PROGRESS ui_progress,
                                     uint8_t secret[OPTIGA_PIN_SECRET_SIZE]) {
  // This step hardens the PIN verification process in case an attacker is able
  // to extract the secret value of a data object in Optiga that has a
  // particular configuration, but does not allow secret extraction for other
  // kinds of data objects. An attacker would need to be able to extract each of
  // the secrets in the different data objects to conduct an offline brute-force
  // search for the PIN. Thus it reduces the number of PIN values that the
  // attacker can test in a unit of time by forcing them to involve the Optiga
  // in each attempt.

  // Pseudocode for the stretching process:
  // result_0 = secret
  // for i in range(PIN_STRETCH_ITERATIONS):
  //   cmac_i = CMAC(optiga_cmac_key, result_i)
  //   hmac_i = HMAC(optiga_hmac_key, result_i)
  //   ecdh_i = ECDH(optiga_ecdh_key, result_i)
  //   result_{i+1} = HMAC-SHA256(secret, cmac_i || hmac_i || ecdh_i)
  // secret = result_{PIN_STRETCH_ITERATIONS}

  HMAC_SHA256_CTX ctx = {0};

  uint8_t result[OPTIGA_PIN_SECRET_SIZE] = {0};
  memcpy(result, secret, sizeof(result));

  uint8_t buffer[ENCRYPT_SYM_PREFIX_SIZE + OPTIGA_PIN_SECRET_SIZE] = {0};
  size_t size = 0;
  for (int i = 0; i < PIN_STRETCH_ITERATIONS; ++i) {
    hmac_sha256_Init(&ctx, secret, OPTIGA_PIN_SECRET_SIZE);

    // Combine intermediate result with OID_PIN_CMAC.
    optiga_result res =
        optiga_encrypt_sym(OPTIGA_SYM_MODE_CMAC, OID_PIN_CMAC, result,
                           sizeof(result), buffer, sizeof(buffer), &size);
    if (res != OPTIGA_SUCCESS) {
      memzero(buffer, sizeof(buffer));
      memzero(result, sizeof(result));
      memzero(&ctx, sizeof(ctx));
      return res;
    }

    hmac_sha256_Update(&ctx, buffer, size);

    // Combine intermediate result with OID_PIN_HMAC
    res = optiga_encrypt_sym(OPTIGA_SYM_MODE_HMAC_SHA256, OID_PIN_HMAC, result,
                             sizeof(result), buffer, sizeof(buffer), &size);
    if (res != OPTIGA_SUCCESS) {
      memzero(buffer, sizeof(buffer));
      memzero(result, sizeof(result));
      memzero(&ctx, sizeof(ctx));
      return res;
    }

    hmac_sha256_Update(&ctx, buffer, size);

    ui_progress(200);

    // Combine intermediate result with OID_PIN_ECDH
    uint8_t encoded_point[BIT_STRING_HEADER_SIZE + 65] = {0x03, 0x42, 0x00};
    if (!hash_to_curve_optiga(result, &encoded_point[BIT_STRING_HEADER_SIZE])) {
      memzero(buffer, sizeof(buffer));
      memzero(result, sizeof(result));
      memzero(&ctx, sizeof(ctx));
      return -1;
    }
    res =
        optiga_calc_ssec(OPTIGA_CURVE_P256, OID_PIN_ECDH, encoded_point,
                         sizeof(encoded_point), buffer, sizeof(buffer), &size);
    memzero(encoded_point, sizeof(encoded_point));
    if (res != OPTIGA_SUCCESS) {
      memzero(buffer, sizeof(buffer));
      memzero(result, sizeof(result));
      memzero(&ctx, sizeof(ctx));
      return res;
    }

    hmac_sha256_Update(&ctx, buffer, size);

    hmac_sha256_Final(&ctx, result);

    ui_progress(200);
  }

  memcpy(secret, result, sizeof(result));
  memzero(buffer, sizeof(buffer));
  memzero(result, sizeof(result));
  memzero(&ctx, sizeof(ctx));
  return OPTIGA_SUCCESS;
}

int optiga_pin_set(OPTIGA_UI_PROGRESS ui_progress,
                   const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
                   uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]) {
  if (!optiga_pin_init_metadata()) {
    return -1;
  }

  optiga_result res = optiga_pin_init_stretch();
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  ui_progress(200);

  // Process the PIN-derived secret using a one-way function before sending it
  // to the Optiga. This ensures that in the unlikely case of an attacker
  // recording communication between the MCU and Optiga, they will not gain
  // knowledge of the PIN-derived secret.
  uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, NULL, 0, stretched_pin);

  // Combine the result with stretching secrets from the Optiga. This step
  // ensures that if an attacker extracts the value of OID_STRETCHED_PIN, then
  // it cannot be used to conduct an offline brute-force search for the PIN.
  res = optiga_pin_stretch_secret(ui_progress, stretched_pin);
  if (res != OPTIGA_SUCCESS) {
    memzero(stretched_pin, sizeof(stretched_pin));
    return res;
  }

  // Generate and store the master secret / PIN counter reset key.
  res = optiga_get_random(out_secret, OPTIGA_PIN_SECRET_SIZE);
  if (res != OPTIGA_SUCCESS) {
    memzero(stretched_pin, sizeof(stretched_pin));
    return res;
  }
  random_xor(out_secret, OPTIGA_PIN_SECRET_SIZE);

  res = optiga_set_data_object(OID_PIN_SECRET, false, out_secret,
                               OPTIGA_PIN_SECRET_SIZE);
  if (res != OPTIGA_SUCCESS) {
    memzero(stretched_pin, sizeof(stretched_pin));
    return res;
  }

  // Authorise using OID_PIN_SECRET so that we can write to OID_PIN_COUNTER and
  // OID_STRETCHED_PIN.
  res = optiga_set_auto_state(OPTIGA_OID_SESSION_CTX, OID_PIN_SECRET,
                              out_secret, OPTIGA_PIN_SECRET_SIZE);
  if (res != OPTIGA_SUCCESS) {
    memzero(stretched_pin, sizeof(stretched_pin));
    return res;
  }

  // Set the stretched PIN.
  res = optiga_set_data_object(OID_STRETCHED_PIN, false, stretched_pin,
                               sizeof(stretched_pin));
  memzero(stretched_pin, sizeof(stretched_pin));
  if (res != OPTIGA_SUCCESS) {
    optiga_clear_auto_state(OID_PIN_SECRET);
    return res;
  }

  // Initialize the PIN counter.
  res = optiga_set_data_object(OID_PIN_COUNTER, false, COUNTER_RESET,
                               sizeof(COUNTER_RESET));
  optiga_clear_auto_state(OID_PIN_SECRET);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  ui_progress(200);

  // Combine the value of OID_PIN_SECRET with the PIN-derived secret and
  // stretching secrets from the Optiga. This step ensures that if an attacker
  // extracts the value of OID_PIN_SECRET, then it cannot be used to conduct an
  // offline brute-force search for the PIN.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);
  res = optiga_pin_stretch_secret(ui_progress, out_secret);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Combine the stretched master secret with the PIN-derived secret to obtain
  // the output secret. This ensures that in the unlikely case of an attacker
  // recording communication between the MCU and Optiga, they cannot decrypt the
  // storage without having to conduct a brute-force search for the PIN.
  // NOTE: Considering how optiga_pin_stretch_secret() works internally and the
  // fact that the PIN was already combined with the value of OID_PIN_SECRET,
  // this step is not necessary. However, it is preferable to explicitly execute
  // it, than to rely on the internals of optiga_pin_stretch_secret().
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);

  // Recombining the returned secret with the PIN-derived secret means that if
  // the user chooses a high-entropy PIN, then even if the Optiga and its
  // communication link is completely compromised, it will not reduce the
  // security of their device any more than if the Optiga was not integrated
  // into the device in the first place.

  return OPTIGA_SUCCESS;
}

int optiga_pin_verify(OPTIGA_UI_PROGRESS ui_progress,
                      const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
                      uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]) {
  // Process the PIN-derived secret using a one-way function before sending it
  // to the Optiga.
  uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE] = {0};
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, NULL, 0, stretched_pin);

  // Combine the result with stretching secrets from the Optiga.
  optiga_result res = optiga_pin_stretch_secret(ui_progress, stretched_pin);
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
    optiga_get_error_code(&error_code);
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

  // Reset the PIN counter.
  res = optiga_set_data_object(OID_PIN_COUNTER, false, COUNTER_RESET,
                               sizeof(COUNTER_RESET));
  optiga_clear_auto_state(OID_PIN_SECRET);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  ui_progress(200);

  // Combine the value of OID_PIN_SECRET with the PIN-derived secret and
  // stretching secrets from the Optiga.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);
  res = optiga_pin_stretch_secret(ui_progress, out_secret);
  if (res != OPTIGA_SUCCESS) {
    return res;
  }

  // Combine the stretched master secret with the PIN-derived secret to derive
  // the output secret.
  hmac_sha256(pin_secret, OPTIGA_PIN_SECRET_SIZE, out_secret,
              OPTIGA_PIN_SECRET_SIZE, out_secret);
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

int optiga_pin_get_fails(uint32_t *ctr) {
  return optiga_get_counter(OID_PIN_COUNTER, ctr);
}

int optiga_pin_fails_increase(uint32_t count) {
  if (count > 0xff) {
    return OPTIGA_ERR_PARAM;
  }

  return optiga_count_data_object(OID_PIN_COUNTER, count);
}
