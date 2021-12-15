/*
 * This file is part of the Micro Python project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2013, 2014 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include "extmod/utime_mphal.h"
#include "shared/timeutils/timeutils.h"

// copy of ports/stm32/modutime.c:time_localtime, without support
// for getting current clock time (i.e., timestamp must always be provided)
STATIC mp_obj_t time_gmtime2000(mp_obj_t timestamp) {
  mp_int_t seconds = mp_obj_get_int(timestamp);
  timeutils_struct_time_t tm;
  timeutils_seconds_since_2000_to_struct_time(seconds, &tm);
  mp_obj_t tuple[8] = {
      tuple[0] = mp_obj_new_int(tm.tm_year),
      tuple[1] = mp_obj_new_int(tm.tm_mon),
      tuple[2] = mp_obj_new_int(tm.tm_mday),
      tuple[3] = mp_obj_new_int(tm.tm_hour),
      tuple[4] = mp_obj_new_int(tm.tm_min),
      tuple[5] = mp_obj_new_int(tm.tm_sec),
      tuple[6] = mp_obj_new_int(tm.tm_wday),
      tuple[7] = mp_obj_new_int(tm.tm_yday),
  };
  return mp_obj_new_tuple(8, tuple);
}

MP_DEFINE_CONST_FUN_OBJ_1(time_gmtime2000_obj, time_gmtime2000);

STATIC const mp_rom_map_elem_t time_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_utime)},

    {MP_ROM_QSTR(MP_QSTR_gmtime2000), MP_ROM_PTR(&time_gmtime2000_obj)},
    {MP_ROM_QSTR(MP_QSTR_sleep), MP_ROM_PTR(&mp_utime_sleep_obj)},
    {MP_ROM_QSTR(MP_QSTR_sleep_ms), MP_ROM_PTR(&mp_utime_sleep_ms_obj)},
    {MP_ROM_QSTR(MP_QSTR_sleep_us), MP_ROM_PTR(&mp_utime_sleep_us_obj)},
    {MP_ROM_QSTR(MP_QSTR_ticks_ms), MP_ROM_PTR(&mp_utime_ticks_ms_obj)},
    {MP_ROM_QSTR(MP_QSTR_ticks_us), MP_ROM_PTR(&mp_utime_ticks_us_obj)},
    {MP_ROM_QSTR(MP_QSTR_ticks_cpu), MP_ROM_PTR(&mp_utime_ticks_cpu_obj)},
    {MP_ROM_QSTR(MP_QSTR_ticks_add), MP_ROM_PTR(&mp_utime_ticks_add_obj)},
    {MP_ROM_QSTR(MP_QSTR_ticks_diff), MP_ROM_PTR(&mp_utime_ticks_diff_obj)},
};

STATIC MP_DEFINE_CONST_DICT(time_module_globals, time_module_globals_table);

const mp_obj_module_t mp_module_utime = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&time_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_utime, mp_module_utime, MICROPY_PY_UTIME);
