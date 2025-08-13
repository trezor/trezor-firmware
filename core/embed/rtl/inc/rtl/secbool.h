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

#pragma once

#include <stdint.h>

typedef uint32_t secbool;
#define sectrue 0xAAAAAAAAU
#define secfalse 0x00000000U

static inline secbool secbool_or(secbool a, secbool b) {
  if (sectrue == a || sectrue == b) {
    return sectrue;
  }
  return secfalse;
}

static inline secbool secbool_and(secbool a, secbool b) {
  if (sectrue == a && sectrue == b) {
    return sectrue;
  }
  return secfalse;
}

static inline secbool secbool_not(secbool a) {
  if (sectrue == a) {
    return secfalse;
  }
  return sectrue;
}

#ifndef __wur
#define __wur __attribute__((warn_unused_result))
#endif
