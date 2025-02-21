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

#include <trezor_types.h>

#include <rtl/unit_test.h>

extern unit_test_record_t _unit_test_section_start;
extern unit_test_record_t _unit_test_section_end;

unit_test_t g_ut = {0};

unit_test_t* unit_test_get_records(void) {
  g_ut.unit_test_array = &_unit_test_section_start;
  g_ut.unit_test_count = &_unit_test_section_end - &_unit_test_section_start;
  return &g_ut;
}
