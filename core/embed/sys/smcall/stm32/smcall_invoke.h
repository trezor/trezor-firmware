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

#if defined(KERNEL) && defined(USE_SECMON_LAYOUT)

#include <trezor_types.h>

#include "smcall_invoke.h"
#include "smcall_numbers.h"

void smcall_invoke(smcall_args_t* args, smcall_number_t smcall);

static inline uint32_t __attribute__((no_stack_protector))
smcall_invoke0(uint32_t smcall) {
  smcall_args_t args = {0};
  smcall_invoke(&args, smcall);
  return args.arg[0];
}

static inline uint64_t __attribute__((no_stack_protector))
smcall_invoke0_ret64(uint32_t smcall) {
  smcall_args_t args = {0};
  smcall_invoke(&args, smcall);
  return ((uint64_t)args.arg[1] << 32) | args.arg[0];
}

static inline uint32_t __attribute__((no_stack_protector))
smcall_invoke1(uint32_t arg1, uint32_t smcall) {
  smcall_args_t args = {
      .arg[0] = arg1,
  };
  smcall_invoke(&args, smcall);
  return args.arg[0];
}

static inline uint32_t __attribute__((no_stack_protector))
smcall_invoke2(uint32_t arg1, uint32_t arg2, uint32_t smcall) {
  smcall_args_t args = {
      .arg[0] = arg1,
      .arg[1] = arg2,
  };
  smcall_invoke(&args, smcall);
  return args.arg[0];
}

static inline uint64_t __attribute__((no_stack_protector))
smcall_invoke2_ret64(uint32_t arg1, uint32_t arg2, uint32_t smcall) {
  smcall_args_t args = {
      .arg[0] = arg1,
      .arg[1] = arg2,
  };
  smcall_invoke(&args, smcall);
  return ((uint64_t)args.arg[1] << 32) | args.arg[0];
}

static inline uint32_t __attribute__((no_stack_protector))
smcall_invoke3(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t smcall) {
  smcall_args_t args = {
      .arg[0] = arg1,
      .arg[1] = arg2,
      .arg[2] = arg3,
  };
  smcall_invoke(&args, smcall);
  return args.arg[0];
}

static inline uint32_t __attribute__((no_stack_protector))
smcall_invoke4(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t arg4,
               uint32_t smcall) {
  smcall_args_t args = {
      .arg[0] = arg1,
      .arg[1] = arg2,
      .arg[2] = arg3,
      .arg[3] = arg4,
  };
  smcall_invoke(&args, smcall);
  return args.arg[0];
}

static inline uint32_t __attribute__((no_stack_protector))
smcall_invoke5(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t arg4,
               uint32_t arg5, uint32_t smcall) {
  smcall_args_t args = {
      .arg[0] = arg1,
      .arg[1] = arg2,
      .arg[2] = arg3,
      .arg[3] = arg4,
      .arg[4] = arg5,
  };
  smcall_invoke(&args, smcall);
  return args.arg[0];
}

static inline uint32_t __attribute__((no_stack_protector))
smcall_invoke6(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t arg4,
               uint32_t arg5, uint32_t arg6, uint32_t smcall) {
  smcall_args_t args = {
      .arg[0] = arg1,
      .arg[1] = arg2,
      .arg[2] = arg3,
      .arg[3] = arg4,
      .arg[4] = arg5,
      .arg[5] = arg6,
  };
  smcall_invoke(&args, smcall);
  return args.arg[0];
}

#endif  // defined(KERNEL) && defined(USE_SECMON_LAYOUT)
