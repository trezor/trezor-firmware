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

#ifndef __TREZORHAL_IMAGE_H__
#define __TREZORHAL_IMAGE_H__

#include <stdint.h>
#include "secbool.h"

#define BOARDLOADER_START 0x08000000
#define BOOTLOADER_START 0x08020000
#define FIRMWARE_START 0x08040000

#define IMAGE_HEADER_SIZE 0x400  // size of the bootloader or firmware header
#define IMAGE_SIG_SIZE 65
#define IMAGE_CHUNK_SIZE (128 * 1024)
#define IMAGE_INIT_CHUNK_SIZE (16 * 1024)

#define BOOTLOADER_IMAGE_MAGIC 0x425A5254  // TRZB
#define BOOTLOADER_IMAGE_MAXSIZE (BOOTLOADER_SECTORS_COUNT * IMAGE_CHUNK_SIZE)

#define FIRMWARE_IMAGE_MAGIC 0x465A5254  // TRZF
#define FIRMWARE_IMAGE_MAXSIZE (FIRMWARE_SECTORS_COUNT * IMAGE_CHUNK_SIZE)

typedef struct {
  uint32_t magic;
  uint32_t hdrlen;
  uint32_t expiry;
  uint32_t codelen;
  uint32_t version;
  uint32_t fix_version;
  uint32_t hw_model;
  uint8_t hw_revision;
  uint8_t monotonic;
  uint8_t reserved_0[2];
  uint8_t hashes[512];
  uint8_t reserved_1[415];
  uint8_t sigmask;
  uint8_t sig[64];
} image_header;

#define MAX_VENDOR_PUBLIC_KEYS 8

#define VTRUST_WAIT 0x000F
#define VTRUST_RED 0x0010
#define VTRUST_CLICK 0x0020
#define VTRUST_STRING 0x0040
#define VTRUST_ALL (VTRUST_WAIT | VTRUST_RED | VTRUST_CLICK | VTRUST_STRING)

typedef struct {
  uint32_t magic;
  uint32_t hdrlen;
  uint32_t expiry;
  uint16_t version;
  uint8_t vsig_m;
  uint8_t vsig_n;
  uint16_t vtrust;
  // uint8_t reserved[14];
  const uint8_t *vpub[MAX_VENDOR_PUBLIC_KEYS];
  uint8_t vstr_len;
  const char *vstr;
  const uint8_t *vimg;
  uint8_t sigmask;
  uint8_t sig[64];
  const uint8_t *origin;  // pointer to the underlying data
} vendor_header;

const image_header *read_image_header(const uint8_t *const data,
                                      const uint32_t magic,
                                      const uint32_t maxsize);

secbool __wur check_image_model(const image_header *const hdr);

secbool __wur check_image_header_sig(const image_header *const hdr,
                                     uint8_t key_m, uint8_t key_n,
                                     const uint8_t *const *keys);

secbool __wur read_vendor_header(const uint8_t *const data,
                                 vendor_header *const vhdr);

secbool __wur check_vendor_header_sig(const vendor_header *const vhdr,
                                      uint8_t key_m, uint8_t key_n,
                                      const uint8_t *const *keys);

void vendor_header_hash(const vendor_header *const vhdr, uint8_t *hash);

secbool __wur check_single_hash(const uint8_t *const hash,
                                const uint8_t *const data, int len);

secbool __wur check_image_contents(const image_header *const hdr,
                                   uint32_t firstskip, const uint8_t *sectors,
                                   int blocks);

void get_image_fingerprint(const image_header *const hdr, uint8_t *const out);

#endif
