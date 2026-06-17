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

#include <math.h>

// Applies gamma correction to a brightness input value.
//
// eq: OUT = ( ( (IN - k) / d ) ^ GAMMA) * q
//
// Parameters:
//   in        - Input brightness value (e.g., 0-255).
//   in_offset - Minimum input value (k in the equation),
//               below which input is clamped.
//   in_max    - Maximum input value (d + k in the equation).
//   gamma_exp - Gamma exponent (GAMMA in the equation).
//   out_max   - Maximum output value (q in the equation).
//
// The transformation performed is:
//   OUT = ( ( (max(IN, in_offset) - in_offset) / (in_max - in_offset) ) ^
//         gamma_exp) * out_max
//
// This normalizes the input, applies gamma correction, and scales to the output
// range.
static inline uint32_t backlight_gamma_correct(uint8_t in, uint8_t in_offset,
                                               uint8_t in_max, float gamma_exp,
                                               uint32_t out_max) {
  uint8_t clamped = in < in_offset ? in_offset : in;

  float out = (float)(clamped - in_offset) /
              (in_max - in_offset);  // Input normalization to <0;1>
  out = powf(out, gamma_exp);        // Gamma correction
  out = out * out_max;               // Output denormalization to <0;out_max>

  return (uint32_t)out;
}

// Inverts backlight_gamma_correct(), recovering the original brightness input
// from a gamma-corrected output value.
//
// eq: IN = ( (OUT / q) ^ (1 / GAMMA) ) * d + k
//
// Parameters mirror backlight_gamma_correct():
//   out       - Gamma-corrected output value (e.g., a PWM duty), 0..out_max.
//   in_offset - Minimum input value (k in the equation).
//   in_max    - Maximum input value (d + k in the equation).
//   gamma_exp - Gamma exponent (GAMMA in the equation), must be non-zero.
//   out_max   - Maximum output value (q in the equation).
//
// The result is clamped to the <in_offset; in_max> range.
static inline uint8_t backlight_gamma_uncorrect(uint32_t out, uint8_t in_offset,
                                                uint8_t in_max, float gamma_exp,
                                                uint32_t out_max) {
  float norm = (float)out / out_max;  // Output normalization to <0;1>
  if (norm > 1.0f) {
    norm = 1.0f;
  }
  norm = powf(norm, 1.0f / gamma_exp);  // Invert gamma correction

  uint32_t in = in_offset + (uint32_t)(norm * (in_max - in_offset));

  // backlight_gamma_correct() floors (cast to uint32_t), so it is not
  // invertible: this inverse systematically underestimates by up to one input
  // step. Correct that bias: if in+1 maps back to the same output, it is a
  // better preimage (same brightness, higher API value), which keeps the
  // correct/uncorrect round-trip stable on BACKLIGHT_RETAIN.
  if (in < in_max &&
      backlight_gamma_correct((uint8_t)(in + 1), in_offset, in_max, gamma_exp,
                              out_max) == out) {
    in++;
  }

  return in < in_max ? (uint8_t)in : in_max;
}
