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

#ifndef PRODTEST_OPTIGA_PRODTEST_H
#define PRODTEST_OPTIGA_PRODTEST_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define OID_CERT_INF OPTIGA_OID_CERT + 0
#define OID_CERT_DEV OPTIGA_OID_CERT + 1
#define OID_CERT_FIDO OPTIGA_OID_CERT + 2
#define OID_KEY_DEV OPTIGA_OID_ECC_KEY + 0
#define OID_KEY_FIDO OPTIGA_OID_ECC_KEY + 2
#define OID_KEY_PAIRING OPTIGA_OID_PTFBIND_SECRET
#define OID_TRUST_ANCHOR (OPTIGA_OID_CA_CERT + 0)

typedef enum {
  OPTIGA_LOCKED_TRUE,
  OPTIGA_LOCKED_FALSE,
  OPTIGA_LOCKED_ERROR,
} optiga_locked_status;

void pair_optiga(void);
void optigaid_read(void);
void cert_read(uint16_t oid);
void cert_write(uint16_t oid, char *data);
void keyfido_write(char *data);
void pubkey_read(uint16_t oid);
void optiga_lock(void);
optiga_locked_status get_optiga_locked_status(void);
void check_locked(void);
void sec_read(void);
bool check_device_cert_chain(const uint8_t *chain, size_t chain_size);

#endif
