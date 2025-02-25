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

ut_t g_ut = {0};

void ut_set_records(const unit_test_record_t* unit_test_array,
                    size_t unit_test_count) {
  g_ut.unit_test_array = unit_test_array;
  g_ut.unit_test_count = unit_test_count;
}

ut_t* ut_get_records_ptr() { return &g_ut; }
