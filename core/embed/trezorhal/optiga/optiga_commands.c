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

/*
 * Reference manuals:
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/Infineon_I2C_Protocol_v2.03.pdf
 */

#include "optiga_commands.h"
#include <string.h>
#include "ecdsa.h"
#include "hmac.h"
#include "memzero.h"
#include "nist256p1.h"
#include "optiga_transport.h"
#include "sha2.h"

// Static buffer for commands and responses.
static uint8_t tx_buffer[1750] = {0};
static size_t tx_size = 0;

static optiga_result process_output_fixedlen(uint8_t *data, size_t data_size) {
  // Expecting data_size bytes of output data in the response.
  if (tx_size != 4 + data_size ||
      (tx_buffer[2] << 8) + tx_buffer[3] != tx_size - 4) {
    return OPTIGA_ERR_UNEXPECTED;
  }

  if (tx_buffer[0] != 0) {
    return OPTIGA_ERR_CMD;
  }

  if (data_size != 0) {
    memcpy(data, tx_buffer + 4, data_size);
    memzero(tx_buffer, tx_size);
  }

  return OPTIGA_SUCCESS;
}

static optiga_result process_output_varlen(uint8_t *data, size_t max_data_size,
                                           size_t *data_size) {
  // Check that there is no trailing output data in the response.
  if (tx_size < 4 || (tx_buffer[2] << 8) + tx_buffer[3] != tx_size - 4) {
    return OPTIGA_ERR_UNEXPECTED;
  }

  // Check response status code.
  if (tx_buffer[0] != 0) {
    return OPTIGA_ERR_CMD;
  }

  // Return result.
  if (tx_size - 4 > max_data_size) {
    return OPTIGA_ERR_SIZE;
  }
  *data_size = tx_size - 4;
  memcpy(data, tx_buffer + 4, tx_size - 4);
  memzero(tx_buffer, tx_size);

  return OPTIGA_SUCCESS;
}

/*
 * For metadata description see:
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#metadata-expression
 */

static const struct {
  size_t offset;
  uint8_t tag;
} METADATA_OFFSET_TAG_MAP[] = {
    {offsetof(optiga_metadata, lcso), 0xC0},
    {offsetof(optiga_metadata, version), 0xC1},
    {offsetof(optiga_metadata, max_size), 0xC4},
    {offsetof(optiga_metadata, used_size), 0xC5},
    {offsetof(optiga_metadata, change), 0xD0},
    {offsetof(optiga_metadata, read), 0xD1},
    {offsetof(optiga_metadata, execute), 0xD3},
    {offsetof(optiga_metadata, meta_update), 0xD8},
    {offsetof(optiga_metadata, algorithm), 0xE0},
    {offsetof(optiga_metadata, key_usage), 0xE1},
    {offsetof(optiga_metadata, data_type), 0xE8},
    {offsetof(optiga_metadata, reset_type), 0xF0},
};

static const size_t METADATA_TAG_COUNT =
    sizeof(METADATA_OFFSET_TAG_MAP) / sizeof(METADATA_OFFSET_TAG_MAP[0]);

optiga_result optiga_parse_metadata(const uint8_t *serialized,
                                    size_t serialized_size,
                                    optiga_metadata *metadata) {
  memzero(metadata, sizeof(*metadata));

  if (serialized_size < 2 || serialized[0] != 0x20 ||
      serialized[1] + 2 != serialized_size) {
    return OPTIGA_ERR_PARAM;
  }

  size_t pos = 2;
  while (pos < serialized_size) {
    if (pos + 2 >= serialized_size) {
      return OPTIGA_ERR_PARAM;
    }

    // Determine metadata type from tag.
    optiga_metadata_item *item = NULL;
    for (int i = 0; i < METADATA_TAG_COUNT; ++i) {
      if (METADATA_OFFSET_TAG_MAP[i].tag == serialized[pos]) {
        item = (void *)((char *)metadata + METADATA_OFFSET_TAG_MAP[i].offset);
        break;
      }
    }

    if (item == NULL || item->ptr != NULL) {
      // Invalid tag or multiply defined tag.
      return OPTIGA_ERR_PARAM;
    }

    item->ptr = &serialized[pos + 2];
    item->len = serialized[pos + 1];
    pos += 2 + serialized[pos + 1];
  }

  if (pos != serialized_size) {
    return OPTIGA_ERR_PARAM;
  }

  return OPTIGA_SUCCESS;
}

optiga_result optiga_serialize_metadata(const optiga_metadata *metadata,
                                        uint8_t *serialized,
                                        size_t max_serialized,
                                        size_t *serialized_size) {
  *serialized_size = 0;
  if (max_serialized < 2) {
    return OPTIGA_ERR_SIZE;
  }

  serialized[0] = 0x20;  // Metadata constructed TLV-Object tag.
  size_t pos = 2;        // Leave room for length byte.

  for (int i = 0; i < METADATA_TAG_COUNT; ++i) {
    optiga_metadata_item *item =
        (void *)((char *)metadata + METADATA_OFFSET_TAG_MAP[i].offset);
    if (item->ptr == NULL) {
      continue;
    }

    if (max_serialized < pos + 2 + item->len) {
      return OPTIGA_ERR_SIZE;
    }

    serialized[pos++] = METADATA_OFFSET_TAG_MAP[i].tag;
    serialized[pos++] = item->len;
    memcpy(&serialized[pos], item->ptr, item->len);
    pos += item->len;
  }

  // Set length byte.
  if (pos - 2 > 256) {
    return OPTIGA_ERR_SIZE;
  }
  serialized[1] = pos - 2;

  *serialized_size = pos;
  return OPTIGA_SUCCESS;
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#openapplication
 */
optiga_result optiga_open_application(void) {
  static const uint8_t OPEN_APP[] = {
      0x70, 0x00, 0x00, 0x10, 0xD2, 0x76, 0x00, 0x00, 0x04, 0x47,
      0x65, 0x6E, 0x41, 0x75, 0x74, 0x68, 0x41, 0x70, 0x70, 0x6C,
  };

  optiga_result ret =
      optiga_execute_command(false, OPEN_APP, sizeof(OPEN_APP), tx_buffer,
                             sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_fixedlen(NULL, 0);
}

optiga_result optiga_get_error_code(uint8_t *error_code) {
  size_t data_size = 0;
  optiga_result ret =
      optiga_get_data_object(0xf1c2, false, error_code, 1, &data_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  if (data_size != 1) {
    return OPTIGA_ERR_SIZE;
  }

  return OPTIGA_SUCCESS;
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#getdataobject
 */
optiga_result optiga_get_data_object(uint16_t oid, bool get_metadata,
                                     uint8_t *data, size_t max_data_size,
                                     size_t *data_size) {
  uint8_t get_data[6] = {0x01, 0x00, 0x00, 0x02};
  if (get_metadata) {
    get_data[1] = 0x01;
  }
  get_data[4] = oid >> 8;
  get_data[5] = oid & 0xff;

  optiga_result ret =
      optiga_execute_command(false, get_data, sizeof(get_data), tx_buffer,
                             sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_varlen(data, max_data_size, data_size);
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#setdataobject
 */
optiga_result optiga_set_data_object(uint16_t oid, bool set_metadata,
                                     const uint8_t *data, size_t data_size) {
  if (data_size + 8 > sizeof(tx_buffer)) {
    return OPTIGA_ERR_PARAM;
  }

  tx_size = data_size + 8;
  tx_buffer[0] = 0x02;
  tx_buffer[1] = set_metadata ? 0x01 : 0x40;
  tx_buffer[2] = (tx_size - 4) >> 8;
  tx_buffer[3] = (tx_size - 4) & 0xff;
  tx_buffer[4] = oid >> 8;
  tx_buffer[5] = oid & 0xff;
  tx_buffer[6] = 0;
  tx_buffer[7] = 0;

  if (data_size != 0) {
    memcpy(tx_buffer + 8, data, data_size);
  }

  optiga_result ret = optiga_execute_command(
      false, tx_buffer, data_size + 8, tx_buffer, sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    memzero(tx_buffer + 8, data_size);
    return ret;
  }

  ret = process_output_fixedlen(NULL, 0);
  memzero(tx_buffer + 8, data_size);
  return ret;
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#getrandom
 */
optiga_result optiga_get_random(uint8_t *random, size_t random_size) {
  if (random_size < 8 || random_size > 256) {
    return OPTIGA_ERR_SIZE;
  }

  uint8_t get_random[6] = {0x0C, 0x00, 0x00, 0x02};
  get_random[4] = random_size >> 8;
  get_random[5] = random_size & 0xff;

  optiga_result ret =
      optiga_execute_command(false, get_random, sizeof(get_random), tx_buffer,
                             sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_fixedlen(random, random_size);
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#encryptsym
 */
optiga_result optiga_encrypt_sym(optiga_sym_mode mode, uint16_t oid,
                                 const uint8_t *input, size_t input_size,
                                 uint8_t *output, size_t max_output_size,
                                 size_t *output_size) {
  if (input_size < 1 || input_size > 640) {
    return OPTIGA_ERR_PARAM;
  }

  tx_size = 9 + input_size;
  tx_buffer[0] = 0x14;
  tx_buffer[1] = mode;
  tx_buffer[2] = (tx_size - 4) >> 8;
  tx_buffer[3] = (tx_size - 4) & 0xff;
  tx_buffer[4] = oid >> 8;
  tx_buffer[5] = oid & 0xff;
  tx_buffer[6] = 0x01;
  tx_buffer[7] = input_size >> 8;
  tx_buffer[8] = input_size & 0xff;
  memcpy(tx_buffer + 9, input, input_size);

  optiga_result ret = optiga_execute_command(
      false, tx_buffer, tx_size, tx_buffer, sizeof(tx_buffer), &tx_size);
  if (ret == OPTIGA_SUCCESS) {
    ret = process_output_varlen(output, max_output_size, output_size);
  }

  memzero(tx_buffer + 7, input_size);
  return ret;
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#decryptsym
 */
optiga_result optiga_set_auto_state(uint16_t nonce_oid, uint16_t key_oid,
                                    const uint8_t key[32]) {
  uint8_t nonce[16] = {0};
  uint8_t get_random[] = {
      0x0C, 0x00, 0x00, 0x07, 0x00, sizeof(nonce), 0x00, 0x00, 0x41, 0x00, 0x00,
  };
  get_random[6] = nonce_oid >> 8;
  get_random[7] = nonce_oid & 0xff;

  optiga_result ret =
      optiga_execute_command(false, get_random, sizeof(get_random), tx_buffer,
                             sizeof(tx_buffer), &tx_size);

  ret = process_output_fixedlen(nonce, sizeof(nonce));
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  tx_size = 11 + sizeof(nonce) + 3 + 32;
  tx_buffer[0] = 0x15;
  tx_buffer[1] = 0x20;
  tx_buffer[2] = 0x00;
  tx_buffer[3] = tx_size - 4;
  tx_buffer[4] = key_oid >> 8;
  tx_buffer[5] = key_oid & 0xff;
  tx_buffer[6] = 0x01;
  tx_buffer[7] = 0x00;
  tx_buffer[8] = 2 + sizeof(nonce);
  tx_buffer[9] = nonce_oid >> 8;
  tx_buffer[10] = nonce_oid & 0xff;
  memcpy(&tx_buffer[11], nonce, sizeof(nonce));
  tx_buffer[11 + sizeof(nonce)] = 0x43;
  tx_buffer[12 + sizeof(nonce)] = 0x00;
  tx_buffer[13 + sizeof(nonce)] = 0x20;
  hmac_sha256(key, 32, nonce, sizeof(nonce), &tx_buffer[14 + sizeof(nonce)]);

  ret = optiga_execute_command(false, tx_buffer, tx_size, tx_buffer,
                               sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_fixedlen(NULL, 0);
}

optiga_result optiga_clear_auto_state(uint16_t key_oid) {
  uint8_t decrypt_sym[] = {
      0x15, 0x20, 0x00, 0x08, 0x00, 0x00, 0x01, 0x00, 0x00, 0x43, 0x00, 0x00,
  };
  decrypt_sym[4] = key_oid >> 8;
  decrypt_sym[5] = key_oid & 0xff;

  optiga_result ret =
      optiga_execute_command(false, decrypt_sym, sizeof(decrypt_sym), tx_buffer,
                             sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  // Expecting no output data. Response status code should indicate failure.
  if (tx_size != 4 || tx_buffer[0] != 0xff || tx_buffer[2] != 0 ||
      tx_buffer[3] != 0) {
    return OPTIGA_ERR_UNEXPECTED;
  }

  return OPTIGA_SUCCESS;
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#calcsign
 */
optiga_result optiga_calc_sign(uint16_t oid, const uint8_t *digest,
                               size_t digest_size, uint8_t *signature,
                               size_t max_sig_size, size_t *sig_size) {
  if (digest_size + 12 > sizeof(tx_buffer)) {
    return OPTIGA_ERR_PARAM;
  }

  tx_size = digest_size + 12;
  tx_buffer[0] = 0x31;
  tx_buffer[1] = 0x11;
  tx_buffer[2] = (tx_size - 4) >> 8;
  tx_buffer[3] = (tx_size - 4) & 0xff;
  tx_buffer[4] = 0x01;
  tx_buffer[5] = digest_size >> 8;
  tx_buffer[6] = digest_size & 0xff;
  memcpy(tx_buffer + 7, digest, digest_size);
  tx_buffer[7 + digest_size] = 0x03;
  tx_buffer[8 + digest_size] = 0x00;
  tx_buffer[9 + digest_size] = 0x02;
  tx_buffer[10 + digest_size] = oid >> 8;
  tx_buffer[11 + digest_size] = oid & 0xff;

  optiga_result ret = optiga_execute_command(
      false, tx_buffer, tx_size, tx_buffer, sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_varlen(signature, max_sig_size, sig_size);
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#genkeypair
 */
optiga_result optiga_gen_key_pair(optiga_curve curve, optiga_key_usage usage,
                                  uint16_t oid, uint8_t *public_key,
                                  size_t max_public_key_size,
                                  size_t *public_key_size) {
  tx_size = 13;
  tx_buffer[0] = 0x38;
  tx_buffer[1] = curve;
  tx_buffer[2] = 0x00;
  tx_buffer[3] = 0x09;
  tx_buffer[4] = 0x01;
  tx_buffer[5] = 0x00;
  tx_buffer[6] = 0x02;
  tx_buffer[7] = oid >> 8;
  tx_buffer[8] = oid & 0xff;
  tx_buffer[9] = 0x02;
  tx_buffer[10] = 0x00;
  tx_buffer[11] = 0x01;
  tx_buffer[12] = usage;

  optiga_result ret = optiga_execute_command(
      false, tx_buffer, tx_size, tx_buffer, sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_varlen(public_key, max_public_key_size,
                               public_key_size);
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#gensymkey
 */
optiga_result optiga_gen_sym_key(optiga_aes algorithm, optiga_key_usage usage,
                                 uint16_t oid) {
  tx_size = 13;
  tx_buffer[0] = 0x39;
  tx_buffer[1] = algorithm;
  tx_buffer[2] = 0x00;
  tx_buffer[3] = 0x09;
  tx_buffer[4] = 0x01;
  tx_buffer[5] = 0x00;
  tx_buffer[6] = 0x02;
  tx_buffer[7] = oid >> 8;
  tx_buffer[8] = oid & 0xff;
  tx_buffer[9] = 0x02;
  tx_buffer[10] = 0x00;
  tx_buffer[11] = 0x01;
  tx_buffer[12] = usage;

  optiga_result ret = optiga_execute_command(
      false, tx_buffer, tx_size, tx_buffer, sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_fixedlen(NULL, 0);
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#calcssec
 */
optiga_result optiga_calc_ssec(optiga_curve curve, uint16_t oid,
                               const uint8_t *public_key,
                               size_t public_key_size, uint8_t *secret,
                               size_t max_secret_size, size_t *secret_size) {
  // Size of a P521 public key encode as a DER BIT STRING.
  static const size_t MAX_PUBKEY_SIZE = 5 + 2 * 66;

  if (public_key_size > MAX_PUBKEY_SIZE) {
    return OPTIGA_ERR_PARAM;
  }

  tx_size = 16 + public_key_size + 3;
  tx_buffer[0] = 0x33;
  tx_buffer[1] = 0x01;
  tx_buffer[2] = 0x00;
  tx_buffer[3] = tx_size - 4;
  tx_buffer[4] = 0x01;
  tx_buffer[5] = 0x00;
  tx_buffer[6] = 0x02;
  tx_buffer[7] = oid >> 8;
  tx_buffer[8] = oid & 0xff;
  tx_buffer[9] = 0x05;
  tx_buffer[10] = 0x00;
  tx_buffer[11] = 0x01;
  tx_buffer[12] = curve;
  tx_buffer[13] = 0x06;
  tx_buffer[14] = 0x00;
  tx_buffer[15] = public_key_size;
  memcpy(&tx_buffer[16], public_key, public_key_size);
  tx_buffer[16 + public_key_size] = 0x07;
  tx_buffer[17 + public_key_size] = 0x00;
  tx_buffer[18 + public_key_size] = 0x00;

  optiga_result ret = optiga_execute_command(
      false, tx_buffer, tx_size, tx_buffer, sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_varlen(secret, max_secret_size, secret_size);
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#derivekey
 */
optiga_result optiga_derive_key(optiga_key_derivation deriv, uint16_t oid,
                                const uint8_t *salt, size_t salt_size,
                                uint8_t *info, size_t info_size, uint8_t *key,
                                size_t key_size) {
  const bool is_hkdf =
      (deriv == OPTIGA_DERIV_HKDF_SHA256 || deriv == OPTIGA_DERIV_HKDF_SHA384 ||
       deriv == OPTIGA_DERIV_HKDF_SHA512);

  if (salt_size > 1024 || (!is_hkdf && salt_size < 8)) {
    return OPTIGA_ERR_PARAM;
  }

  if (info_size > 256 || (!is_hkdf && info_size != 0)) {
    return OPTIGA_ERR_PARAM;
  }

  tx_size = is_hkdf ? 23 + salt_size + info_size : 20 + salt_size;
  tx_buffer[0] = 0x34;
  tx_buffer[1] = deriv;
  tx_buffer[2] = (tx_size - 4) >> 8;
  tx_buffer[3] = (tx_size - 4) & 0xff;
  tx_buffer[4] = 0x01;
  tx_buffer[5] = 0x00;
  tx_buffer[6] = 0x02;
  tx_buffer[7] = oid >> 8;
  tx_buffer[8] = oid & 0xff;
  tx_buffer[9] = 0x02;
  tx_buffer[10] = salt_size >> 8;
  tx_buffer[11] = salt_size & 0xff;
  if (salt_size != 0) {
    memcpy(&tx_buffer[12], salt, salt_size);
  }
  tx_buffer[12 + salt_size] = 0x03;
  tx_buffer[13 + salt_size] = 0x00;
  tx_buffer[14 + salt_size] = 0x02;
  tx_buffer[15 + salt_size] = key_size >> 8;
  tx_buffer[16 + salt_size] = key_size & 0xff;

  if (is_hkdf) {
    tx_buffer[17 + salt_size] = 0x04;
    tx_buffer[18 + salt_size] = info_size >> 8;
    tx_buffer[19 + salt_size] = info_size & 0xff;
    if (info_size != 0) {
      memcpy(&tx_buffer[20 + salt_size], info, info_size);
    }
    tx_buffer[20 + salt_size + info_size] = 0x07;
    tx_buffer[21 + salt_size + info_size] = 0x00;
    tx_buffer[22 + salt_size + info_size] = 0x00;
  } else {
    tx_buffer[17 + salt_size] = 0x07;
    tx_buffer[18 + salt_size] = 0x00;
    tx_buffer[19 + salt_size] = 0x00;
  }

  optiga_result ret = optiga_execute_command(
      false, tx_buffer, tx_size, tx_buffer, sizeof(tx_buffer), &tx_size);
  if (ret == OPTIGA_SUCCESS) {
    ret = process_output_fixedlen(key, key_size);
  }

  memzero(&tx_buffer[12], salt_size);
  memzero(&tx_buffer[20 + salt_size], info_size);
  return ret;
}

optiga_result optiga_set_trust_anchor(void) {
  // Trust anchor certificate.
  const uint8_t TA_CERT[] = {
      0x30, 0x82, 0x01, 0x49, 0x30, 0x81, 0xf0, 0xa0, 0x03, 0x02, 0x01, 0x02,
      0x02, 0x01, 0x01, 0x30, 0x0a, 0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d,
      0x04, 0x03, 0x02, 0x30, 0x0d, 0x31, 0x0b, 0x30, 0x09, 0x06, 0x03, 0x55,
      0x04, 0x03, 0x0c, 0x02, 0x54, 0x41, 0x30, 0x20, 0x17, 0x0d, 0x32, 0x33,
      0x30, 0x37, 0x32, 0x34, 0x31, 0x35, 0x31, 0x31, 0x34, 0x37, 0x5a, 0x18,
      0x0f, 0x32, 0x30, 0x35, 0x33, 0x30, 0x37, 0x32, 0x33, 0x31, 0x35, 0x31,
      0x31, 0x34, 0x37, 0x5a, 0x30, 0x0d, 0x31, 0x0b, 0x30, 0x09, 0x06, 0x03,
      0x55, 0x04, 0x03, 0x0c, 0x02, 0x54, 0x41, 0x30, 0x59, 0x30, 0x13, 0x06,
      0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01, 0x06, 0x08, 0x2a, 0x86,
      0x48, 0xce, 0x3d, 0x03, 0x01, 0x07, 0x03, 0x42, 0x00, 0x04, 0x9b, 0xbf,
      0x06, 0xda, 0xd9, 0xab, 0x59, 0x05, 0xe0, 0x54, 0x71, 0xce, 0x16, 0xd5,
      0x22, 0x2c, 0x89, 0xc2, 0xca, 0xa3, 0x9f, 0x26, 0x26, 0x7a, 0xc0, 0x74,
      0x71, 0x29, 0x88, 0x5f, 0xbd, 0x44, 0x1b, 0xcc, 0x7f, 0xa8, 0x4d, 0xe1,
      0x20, 0xa3, 0x67, 0x55, 0xda, 0xf3, 0x0a, 0x6f, 0x47, 0xe8, 0xc0, 0xd4,
      0xbd, 0xdc, 0x15, 0x03, 0x6e, 0xd2, 0xa3, 0x44, 0x7d, 0xfa, 0x7a, 0x1d,
      0x3e, 0x88, 0xa3, 0x3f, 0x30, 0x3d, 0x30, 0x0c, 0x06, 0x03, 0x55, 0x1d,
      0x13, 0x01, 0x01, 0xff, 0x04, 0x02, 0x30, 0x00, 0x30, 0x0e, 0x06, 0x03,
      0x55, 0x1d, 0x0f, 0x01, 0x01, 0xff, 0x04, 0x04, 0x03, 0x02, 0x07, 0x80,
      0x30, 0x1d, 0x06, 0x03, 0x55, 0x1d, 0x0e, 0x04, 0x16, 0x04, 0x14, 0x68,
      0x36, 0xfc, 0x5d, 0x40, 0xb5, 0xbe, 0x47, 0xd4, 0xb0, 0xe2, 0x46, 0x7a,
      0xfe, 0x54, 0x3d, 0x8a, 0xd7, 0x0e, 0x26, 0x30, 0x0a, 0x06, 0x08, 0x2a,
      0x86, 0x48, 0xce, 0x3d, 0x04, 0x03, 0x02, 0x03, 0x48, 0x00, 0x30, 0x45,
      0x02, 0x21, 0x00, 0xff, 0x39, 0x3d, 0x00, 0x1d, 0x9f, 0x88, 0xdc, 0xc1,
      0x58, 0x12, 0x68, 0xa5, 0x7f, 0x06, 0x18, 0x1e, 0x65, 0x77, 0x88, 0x12,
      0xcb, 0xa5, 0x9d, 0x47, 0xd0, 0x17, 0x85, 0xcd, 0xb8, 0xdc, 0xaa, 0x02,
      0x20, 0x08, 0xb8, 0xbe, 0x65, 0xd4, 0xbe, 0x31, 0xe7, 0x74, 0x64, 0x46,
      0xfb, 0xe7, 0x70, 0x48, 0x02, 0xd1, 0x08, 0x64, 0xf8, 0xe8, 0x4e, 0xfc,
      0xb0, 0xa5, 0x21, 0x2c, 0x54, 0x3a, 0x6c, 0x04, 0x72,
  };

  return optiga_set_data_object(0xe0e8, false, TA_CERT, sizeof(TA_CERT));
}

/*
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#setobjectprotected
 */
optiga_result optiga_set_priv_key(uint16_t oid, const uint8_t priv_key[32]) {
  uint8_t metadata_buffer[256] = {0};
  size_t metadata_size = 0;
  optiga_result ret = optiga_get_data_object(
      oid, true, metadata_buffer, sizeof(metadata_buffer), &metadata_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  optiga_metadata metadata = {0};
  ret = optiga_parse_metadata(metadata_buffer, metadata_size, &metadata);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  uint16_t payload_version = 0;
  if (metadata.version.ptr != NULL) {
    if (metadata.version.len != 2) {
      return OPTIGA_ERR_UNEXPECTED;
    }
    payload_version = (metadata.version.ptr[0] << 8) + metadata.version.ptr[1];
  }
  payload_version += 1;

  if (payload_version > 23) {
    // CBOR integer encoding not implemented.
    return OPTIGA_ERR_PARAM;
  }

  // Trust anchor private key.
  const uint8_t TA_PRIV_KEY[32] = {1};

  // First part of the SetObjectProtected command containing the manifest.
  uint8_t sop_cmd1[145] = {
      0x03, 0x01, 0x00, 0x8d, 0x30, 0x00, 0x8a, 0x84, 0x43, 0xA1, 0x01, 0x26,
      0xA1, 0x04, 0x42, 0xE0, 0xE8, 0x58, 0x3C, 0x86, 0x01, 0xF6, 0xF6, 0x84,
      0x22, 0x18, 0x23, 0x03, 0x82, 0x03, 0x10, 0x82, 0x82, 0x20, 0x58, 0x25,
      0x82, 0x18, 0x29, 0x58, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
      0x00, 0xF6, 0x82, 0x40, 0x42, 0xE0, 0xF2, 0x58, 0x40,
  };

  // Second part of the SetObjectProtected command containing the fragment
  // with the private key.
  uint8_t sop_cmd2[42] = {
      0x03, 0x01, 0x00, 0x26, 0x31, 0x00, 0x23, 0x01, 0x00, 0x20,
  };

  memcpy(&sop_cmd2[10], &priv_key[0], 32);

  sha256_Raw(&sop_cmd2[7], 35, &sop_cmd1[41]);

  sop_cmd1[27] = payload_version;
  sop_cmd1[77] = oid >> 8;
  sop_cmd1[78] = oid & 0xff;
  // NOTE sop_cmd1[26] = fragment length (1 + 2 + 32)
  // NOTE sop_cmd1[30] = key usage

  const uint8_t signature_header[] = {
      0x84, 0x4A, 0x53, 0x69, 0x67, 0x6E, 0x61, 0x74, 0x75,
      0x72, 0x65, 0x31, 0x43, 0xA1, 0x01, 0x26, 0x40,
  };
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  SHA256_CTX context = {0};
  sha256_Init(&context);
  sha256_Update(&context, signature_header, sizeof(signature_header));
  sha256_Update(&context, &sop_cmd1[17], 62);
  sha256_Final(&context, digest);

  if (0 != ecdsa_sign_digest(&nist256p1, TA_PRIV_KEY, digest, &sop_cmd1[81],
                             NULL, NULL)) {
    memzero(sop_cmd2, sizeof(sop_cmd2));
    return OPTIGA_ERR_PROCESS;
  }

  ret = optiga_execute_command(false, sop_cmd1, sizeof(sop_cmd1), tx_buffer,
                               sizeof(tx_buffer), &tx_size);
  if (ret != OPTIGA_SUCCESS) {
    memzero(sop_cmd2, sizeof(sop_cmd2));
    return ret;
  }

  ret = process_output_fixedlen(NULL, 0);
  if (ret != OPTIGA_SUCCESS) {
    memzero(sop_cmd2, sizeof(sop_cmd2));
    return ret;
  }

  ret = optiga_execute_command(false, sop_cmd2, sizeof(sop_cmd2), tx_buffer,
                               sizeof(tx_buffer), &tx_size);
  memzero(sop_cmd2, sizeof(sop_cmd2));
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  return process_output_fixedlen(NULL, 0);
}
