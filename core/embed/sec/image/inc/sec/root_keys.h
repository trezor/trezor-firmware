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
 * You should have received a copy of the General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

/*
 * Root public keys for pq_secure_boot -- ONE key set, ALL models.
 *
 * Named after their trezorlib counterparts (firmware/models.py), which is the
 * authority and what the signer uses, so the two sides can be compared by name:
 *
 *     ROOT_SLH_DSA_KEYS      <- ROOT_SLH_DSA_KEYS            (production)
 *     ROOT_ED25519_KEYS      <- ROOT_ED25519_KEYS            (production)
 *     ROOT_SLH_DSA_KEYS_DEV  <- ROOT_SLH_DSA_KEYS_DEV_PUBLIC (devel)
 *     ROOT_ED25519_KEYS_DEV  <- ROOT_ED25519_KEYS_DEV        (devel)
 *
 * The _DEV names drop Python's _PUBLIC: C only ever holds public halves, so
 * there is no private counterpart here to distinguish them from.
 */

// clang-format off

/*
 * DEVEL/QA pool. These PUBLIC keys must NEVER be built into a shipped device.
 *
 * Their private halves are public knowledge -- the SLH-DSA ones are checked into
 * this repository (trezorlib firmware/models.py ROOT_SLH_DSA_KEYS_DEV_PRIVATE)
 * and the Ed25519 ones are not even stored, but derived from the constants 'A'
 * and 'B' (_internal/firmware_headers.py _make_dev_keys). Anyone can therefore
 * sign a boot header that a bootloader carrying these keys will accept, so such a
 * build has no secure boot at all. It is a development convenience, selected by
 * BOOTLOADER_DEVEL, and nothing more.
 */
#define ROOT_SLH_DSA_KEYS_DEV \
  (const uint8_t *)"\xec\x01\xe6\x02\x63\x02\x4f\x7e\x71\x72\x80\x13\xb7\x31\xf7\xba\x12\x99\xf5\x18\xc2\x7b\xa3\xed\x8f\x4a\x21\x99\x74\x12\x7c\x62", \
  (const uint8_t *)"\x8a\xf8\x87\x80\x85\x94\x6e\xd8\xb1\x16\xbd\x24\xc0\xf2\xaa\xc4\x8b\x7e\x8f\x11\xbf\x06\x87\x25\xcc\xfb\xb1\x52\xab\xf7\xa4\xcd",

#define ROOT_ED25519_KEYS_DEV \
  (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d", \
  (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",

/*** PRODUCTION ***/
#define ROOT_SLH_DSA_KEYS \
  (const uint8_t *)"\xec\x57\xa2\x64\x3e\x55\x3c\x59\x19\x47\x3c\xd5\x79\xcd\xdd\xa6\x50\x05\x7c\x2f\xd5\x98\xa4\x47\x57\x4b\xdb\x6c\x1f\x0f\x55\x21", \
  (const uint8_t *)"\xd2\x96\xd8\xcf\x9b\xe3\xe9\x23\xe1\x0a\xc0\x3f\x43\x56\x6d\x18\x9d\x11\xf6\xb5\xdd\xab\xdf\x8d\xc1\x2d\x29\xc0\x0e\x5a\x13\x6a", \
  (const uint8_t *)"\xb7\x2b\xd7\x1b\xf8\xe1\x09\xd3\x77\x4d\x91\xe3\xc1\xab\xd2\xa2\xe9\xff\x6b\x57\x11\x89\x6f\x8d\x87\x3a\x3d\xf9\xb9\xbe\x98\xd1",

#define ROOT_ED25519_KEYS \
  (const uint8_t *)"\xb0\xd7\x3e\x86\xae\x39\x2a\x26\xda\x72\x75\x99\x4e\x96\x50\x97\xae\x7e\xe8\xf8\x84\x55\x78\x8e\x8c\x53\x40\x21\xd5\xde\x18\x85", \
  (const uint8_t *)"\xa8\xf1\x8b\x94\x86\x16\x7c\x97\xb0\x59\xfd\x4f\x05\x3b\xe8\x24\xf7\xd5\xb0\xcb\x87\x10\xb3\xca\x12\xd2\x6d\x2d\xda\xc3\x51\xc9", \
  (const uint8_t *)"\xd2\x0f\xbd\xa4\x27\x1a\xeb\x06\xc1\x8c\x26\xc6\xf2\xad\xb6\xd6\xb0\xe3\x12\xf8\x45\xf9\x04\x41\xfd\x61\x4f\x39\x75\x54\xa8\x6e",

// clang-format on
