/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __SIGNATURES_H__
#define __SIGNATURES_H__

#include <stdbool.h>
#include <stdint.h>

extern const uint32_t FIRMWARE_MAGIC_OLD;  // TRZR
extern const uint32_t FIRMWARE_MAGIC_NEW;  // TRZF

#define SIG_OK 0x5A3CA5C3
#define SIG_FAIL 0x00000000

bool firmware_present_old(void);
int signatures_old_ok(void);

// we use the same structure as T2 firmware header
// but we don't use the field sig
// and rather introduce fields sig1, sig2, sig3
// immediately following the chunk hashes

typedef struct {
  uint32_t magic;
  uint32_t hdrlen;
  uint32_t expiry;
  uint32_t codelen;
  uint32_t version;
  uint32_t fix_version;
  uint8_t __reserved1[8];
  uint8_t hashes[512];
  uint8_t sig1[64];
  uint8_t sig2[64];
  uint8_t sig3[64];
  uint8_t sigindex1;
  uint8_t sigindex2;
  uint8_t sigindex3;
  uint8_t __reserved2[220];
  uint8_t __sigmask;
  uint8_t __sig[64];
} __attribute__((packed)) image_header;

#define FW_CHUNK_SIZE 65536

bool firmware_present_new(void);
void compute_firmware_fingerprint(const image_header *hdr, uint8_t hash[32]);
int signatures_new_ok(const image_header *hdr, uint8_t store_fingerprint[32]);
int check_firmware_hashes(const image_header *hdr);

int mem_is_empty(const uint8_t *src, uint32_t len);

#endif
