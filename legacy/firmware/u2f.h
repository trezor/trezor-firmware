/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2015 Mark Bryars <mbryars@google.com>
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

#ifndef __U2F_H__
#define __U2F_H__

#include <stdbool.h>
#include <stdint.h>
#include "trezor.h"
#include "u2f/u2f_hid.h"

#define U2F_KEY_PATH 0x80553246

typedef struct {
  uint8_t cla, ins, p1, p2;
  uint8_t lc1, lc2, lc3;
  uint8_t data[];
} APDU;

#define APDU_LEN(A) (uint32_t)(((A).lc1 << 16) + ((A).lc2 << 8) + ((A).lc3))

void u2fhid_read(char tiny, const U2FHID_FRAME *buf);
void u2fhid_init_cmd(const U2FHID_FRAME *f);
void u2fhid_read_start(const U2FHID_FRAME *f);
bool u2fhid_write(uint8_t *buf);
void u2fhid_init(const U2FHID_FRAME *in);
void u2fhid_ping(const uint8_t *buf, uint32_t len);
void u2fhid_wink(const uint8_t *buf, uint32_t len);
void u2fhid_sync(const uint8_t *buf, uint32_t len);
void u2fhid_lock(const uint8_t *buf, uint32_t len);
void u2fhid_msg(const APDU *a, uint32_t len);
void queue_u2f_pkt(const U2FHID_FRAME *u2f_pkt);

uint8_t *u2f_out_data(void);
void u2f_register(const APDU *a);
void u2f_version(const APDU *a);
void u2f_authenticate(const APDU *a);

void send_u2f_msg(const uint8_t *data, uint32_t len);
void send_u2f_error(uint16_t err);

void send_u2fhid_msg(const uint8_t cmd, const uint8_t *data,
                     const uint32_t len);
void send_u2fhid_error(uint32_t fcid, uint8_t err);

#endif
