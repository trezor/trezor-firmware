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

#ifndef TREZOR_HAL_QUICKMATH_H
#define TREZOR_HAL_QUICKMATH_H

#include <stdint.h>

// Initializes the library
void quickmath_init();

// Performs a conversion from `angle` (in degrees)  and `radius`
// to a vector `x', 'y (polar to cartesian transformation)
//
// _x = cos(angle) * radius;
// _y = sin(angle) * radius;

// 3.1us, 32-bit CORDIC, using ST HAL library
void quickmath_polar_to_cartesian_i32(int32_t angle, int32_t radius,
                                      int32_t* _x, int32_t* _y);

// 1.9us, 16-bit CORDIC, using ST HAL library
void quickmath_polar_to_cartesian_i16(int16_t angle, int16_t radius,
                                      int16_t* _x, int16_t* _y);

// 0.47us, 16-bit CORDIC, NOT using ST HAL library
void quickmath_polar_to_cartesian_i16_ll(int16_t angle, int16_t radius,
                                         int16_t* _x, int16_t* _y);

// 1.7us, uses sinf, cosf runtime functions
void quickmath_polar_to_cartesian_vfp(int16_t angle, int16_t radius,
                                      int16_t* _x, int16_t* _y);

#if 1
void quickmath_test();
void quickmath_performance_test();
#endif

#endif  // TREZOR_HAL_QUICKMATH_H
