/**
 * Copyright (c) 2016 Daira Hopwood
 * Copyright (c) 2016 Pavol Rusnak
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include "address.h"
#include "bignum.h"

size_t address_prefix_bytes_len(uint32_t address_type) {
  if (address_type <= 0xFF) return 1;
  if (address_type <= 0xFFFF) return 2;
  if (address_type <= 0xFFFFFF) return 3;
  return 4;
}

void address_write_prefix_bytes(uint32_t address_type, uint8_t *out) {
  if (address_type > 0xFFFFFF) *(out++) = address_type >> 24;
  if (address_type > 0xFFFF) *(out++) = (address_type >> 16) & 0xFF;
  if (address_type > 0xFF) *(out++) = (address_type >> 8) & 0xFF;
  *(out++) = address_type & 0xFF;
}

bool address_check_prefix(const uint8_t *addr, uint32_t address_type) {
  if (address_type <= 0xFF) {
    return address_type == (uint32_t)(addr[0]);
  }
  if (address_type <= 0xFFFF) {
    return address_type == (((uint32_t)addr[0] << 8) | ((uint32_t)addr[1]));
  }
  if (address_type <= 0xFFFFFF) {
    return address_type == (((uint32_t)addr[0] << 16) |
                            ((uint32_t)addr[1] << 8) | ((uint32_t)addr[2]));
  }
  return address_type ==
         (((uint32_t)addr[0] << 24) | ((uint32_t)addr[1] << 16) |
          ((uint32_t)addr[2] << 8) | ((uint32_t)addr[3]));
}

#if USE_ETHEREUM
#include "sha3.h"

void ethereum_address_checksum(const uint8_t *addr, char *address, bool rskip60,
                               uint32_t chain_id) {
  const char *hex = "0123456789abcdef";
  for (int i = 0; i < 20; i++) {
    address[i * 2] = hex[(addr[i] >> 4) & 0xF];
    address[i * 2 + 1] = hex[addr[i] & 0xF];
  }
  address[40] = 0;

  SHA3_CTX ctx = {0};
  uint8_t hash[32] = {0};
  keccak_256_Init(&ctx);
  if (rskip60) {
    char prefix[16] = {0};
    int prefix_size = bn_format_uint64(chain_id, NULL, "0x", 0, 0, false,
                                       prefix, sizeof(prefix));
    keccak_Update(&ctx, (const uint8_t *)prefix, prefix_size);
  }
  keccak_Update(&ctx, (const uint8_t *)address, 40);
  keccak_Final(&ctx, hash);

  for (int i = 0; i < 20; i++) {
    if (hash[i] & 0x80 && address[i * 2] >= 'a' && address[i * 2] <= 'f') {
      address[i * 2] -= 0x20;
    }
    if (hash[i] & 0x08 && address[i * 2 + 1] >= 'a' &&
        address[i * 2 + 1] <= 'f') {
      address[i * 2 + 1] -= 0x20;
    }
  }
}
#endif
