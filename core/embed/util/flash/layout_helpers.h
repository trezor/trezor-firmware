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

#ifndef TREZORHAL_LAYOUT_HELPERS_H
#define TREZORHAL_LAYOUT_HELPERS_H

#ifdef TREZOR_EMULATOR
#define ENSURE_SECTOR_AT(addr, sector)
#else
// Static assertions ensuring that the flash address coresponds
// to the expected sector start. This macro is used in the
// definitions below.
#define ENSURE_SECTOR_AT(addr, sector)                             \
  _Static_assert(FLASH_SECTOR_TO_ADDR(EVAL(sector)) == EVAL(addr), \
                 "Sector address mismatch")
#endif

// Helper that expands to its argument
#define EVAL(x) x

// Defines flash_subarea_t structure
#define SUBAREA(_first_sector, _end_sectors)             \
  {                                                      \
    .first_sector = (_first_sector),                     \
    .num_sectors = (_end_sectors) - (_first_sector) + 1, \
  }

// Defines flash area containing 1 subarea
#define DEFINE_SINGLE_AREA(id, prefix)                                   \
  ENSURE_SECTOR_AT(prefix##_START, prefix##_SECTOR_START);               \
  ENSURE_SECTOR_AT(prefix##_START + prefix##_MAXSIZE,                    \
                   prefix##_SECTOR_END + 1);                             \
  const flash_area_t prefix##_AREA = {                                   \
      .num_subareas = 1,                                                 \
      .subarea[0] = SUBAREA(prefix##_SECTOR_START, prefix##_SECTOR_END), \
  }

// Defines flash area containing two subareas from two
// different blocks giveng by their prefixes
#define DEFINE_SPLIT2_AREA(id, prefix1, prefix2)                           \
  ENSURE_SECTOR_AT(prefix1##_START, prefix1##_SECTOR_START);               \
  ENSURE_SECTOR_AT(prefix1##_START + prefix1##_MAXSIZE,                    \
                   prefix1##_SECTOR_END + 1);                              \
  ENSURE_SECTOR_AT(prefix2##_START, prefix2##_SECTOR_START);               \
  ENSURE_SECTOR_AT(prefix2##_START + prefix2##_MAXSIZE,                    \
                   prefix2##_SECTOR_END + 1);                              \
  const flash_area_t id = {                                                \
      .num_subareas = 2,                                                   \
      .subarea[0] = SUBAREA(prefix1##_SECTOR_START, prefix1##_SECTOR_END), \
      .subarea[1] = SUBAREA(prefix2##_SECTOR_START, prefix2##_SECTOR_END), \
  }

// Defines array of two flash areas from two differenc blocks
// given by their prefixes
#define DEFINE_ARRAY2_AREA(id, prefix1, prefix2)                               \
  ENSURE_SECTOR_AT(prefix1##_START, prefix1##_SECTOR_START);                   \
  ENSURE_SECTOR_AT(prefix1##_START + prefix1##_MAXSIZE,                        \
                   prefix1##_SECTOR_END + 1);                                  \
  ENSURE_SECTOR_AT(prefix2##_START, prefix2##_SECTOR_START);                   \
  ENSURE_SECTOR_AT(prefix2##_START + prefix2##_MAXSIZE,                        \
                   prefix2##_SECTOR_END + 1);                                  \
  const flash_area_t id[] = {                                                  \
      {                                                                        \
          .num_subareas = 1,                                                   \
          .subarea[0] = SUBAREA(prefix1##_SECTOR_START, prefix1##_SECTOR_END), \
      },                                                                       \
      {                                                                        \
          .num_subareas = 1,                                                   \
          .subarea[0] = SUBAREA(prefix2##_SECTOR_START, prefix2##_SECTOR_END), \
      }}

#define DEFINE_EMPTY_AREA(id) const flash_area_t id = {.num_subareas = 0}

#endif  // TREZORHAL_LAYOUT_HELPERS_H
