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
#include "optiga_commands.h"

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
