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

#include <trezor_types.h>

#include <rtl/cli.h>

typedef enum {
  UT_PASSED = 0,
  UT_FAILED,
} ut_status_t;

// unit test handler routine prototype
typedef ut_status_t (*ut_handler_t)(cli_t* ut);

// Structure describing the registration record for a CLI unit test handler
typedef struct {
  // Unit test name
  const char* name;
  // Unit test handler
  ut_handler_t func;
  // Single line unit test description
  const char* info;
} unit_test_record_t;

#define CONCAT_UT_INDIRECT(x, y) x##y
#define CONCAT_UT(x, y) CONCAT_INDIRECT(x, y)

// Register a unit test by placing its registration record
// into a specially designated linker script section
#define REGISTER_UNIT_TEST(...)                                                \
  __attribute__((used, section(".unit_test"))) static const unit_test_record_t \
      CONCAT_UT(_ut_handler, __COUNTER__) = {__VA_ARGS__};

typedef struct {
  // Registered unit test record handlers
  const unit_test_record_t* unit_test_array;
  size_t unit_test_count;
} unit_test_t;

// Returns the pointer to unit_test_t structure with all registered records
unit_test_t* unit_test_get_records(void);
