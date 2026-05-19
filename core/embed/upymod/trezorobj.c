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

#include "py/runtime.h"

mp_obj_t trezor_obj_call_protected(void (*func)(void *), void *arg) {
  nlr_buf_t nlr;
  if (nlr_push(&nlr) == 0) {
    (*func)(arg);
    nlr_pop();
    return NULL;
  } else {
    return MP_OBJ_FROM_PTR(nlr.ret_val);
  }
}
