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

#include "quickmath.h"

#include <stdio.h>
#include STM32_HAL_H

// Global CORDIC driver instance
static CORDIC_HandleTypeDef g_hcordic = {.Instance = CORDIC};

// Low level initialization routine internally called from HAL_CORDIC_init()
void HAL_CORDIC_MspInit(CORDIC_HandleTypeDef *hcordic) {
  UNUSED(hcordic);

  // Enable the CORDIC peripheral at the low level
  // Since we use it in polling mode, enabling the clock is sufficient
  __HAL_RCC_CORDIC_CLK_ENABLE();
}

void quickmath_init() {
  // Initialize CORDIC instance
  HAL_CORDIC_Init(&g_hcordic);
}

void quickmath_polar_to_cartesian_i32(int32_t angle, int32_t radius,
                                      int32_t *_x, int32_t *_y) {
  // CORDIC coprocessor configuration for calculation
  // of sine and cosine functions
  const static CORDIC_ConfigTypeDef config = {
      .Function = CORDIC_FUNCTION_COSINE,
      .Precision = CORDIC_PRECISION_6CYCLES,  // 24 iterations
      .Scale = CORDIC_SCALE_0,                // scale x1
      .InSize = CORDIC_INSIZE_32BITS,         // inputs in q1.31
      .OutSize = CORDIC_OUTSIZE_32BITS,       // outputs in q1.31
      .NbWrite = CORDIC_NBWRITE_1,  // one 32-bit input, modulus fixed to 1.0
      .NbRead = CORDIC_NBREAD_2,    // two 32-bit outputs
  };

  /*HAL_StatusTypeDef* -> HAL_OK, HAL_ERROR */
  HAL_CORDIC_Configure(&g_hcordic, &config);

  // calculate phi input parameter first
  // angle [degrees] -> phi[radians/PI] 
  int32_t phi = ((int64_t)angle << 31) / 180;

  // CORDIC inputs { phi in radians divided by PI } in q1.31
  // modulus is fixed to 1.0 by hardware
  int32_t inbuff[1] = {phi};
  // CORDIC outputs { cos(phi), sin(phi) } both in q1.31
  int32_t outbuff[2];

  /*HAL_StatusTypeDef* -> HAL_OK, HAL_ERROR */
  HAL_CORDIC_Calculate(&g_hcordic, inbuff, outbuff, 1, HAL_MAX_DELAY);

  // calculate the vector coordinates
  *_x = ((int64_t)outbuff[0] * radius) >> 31;
  *_y = ((int64_t)outbuff[1] * radius) >> 31;
}

void quickmath_polar_to_cartesian_i16(int16_t angle, int16_t radius,
                                      int16_t *_x, int16_t *_y) {
  // CORDIC coprocessor configuration for calculation
  // of sine and cosine functions
  const static CORDIC_ConfigTypeDef config = {
      .Function = CORDIC_FUNCTION_COSINE,
      .Precision = CORDIC_PRECISION_5CYCLES,  // 20 iterations
      .Scale = CORDIC_SCALE_0,                // scale x1
      .InSize = CORDIC_INSIZE_16BITS,         // inputs in q1.15
      .OutSize = CORDIC_OUTSIZE_16BITS,       // outputs in q1.15
      .NbWrite = CORDIC_NBWRITE_1,            // one 32-bit input
      .NbRead = CORDIC_NBREAD_1,              // one 32-bit output
  };

  /*HAL_StatusTypeDef* -> HAL_OK, HAL_ERROR */
  HAL_CORDIC_Configure(&g_hcordic, &config);

  // angle [degrees] -> phi[radians/PI] 
  int16_t phi = (angle << 15) / 180;

  // CORDIC inputs { phi in radians divided by PI, modulus } in q1.15
  // phi in lower 16-bits, modulus is set to 1.0 in higher 16-bits
  int32_t inbuff[1] = {(uint16_t)phi + (INT16_MAX << 16)};
  // CORDIC outputs { cos(phi), sin(phi) } both in q1.15
  // cosine in lower 16-bits, sine in higher 16-bits
  int32_t outbuff[1];

  /*HAL_StatusTypeDef* -> HAL_OK, HAL_ERROR */
  HAL_CORDIC_Calculate(&g_hcordic, inbuff, outbuff, 1, HAL_MAX_DELAY);

  // calculate the vector coordinates
  *_x = ((int16_t)(outbuff[0] & 0xFFFF) * radius) >> 15;
  *_y = ((int16_t)(outbuff[0] >> 16) * radius) >> 15;
}

void quickmath_polar_to_cartesian_i16_ll(int16_t angle, int16_t radius,
                                         int16_t *_x, int16_t *_y) {
  // configure CORDIC configuration for calculation
  // of sine and cosine functions

  CORDIC->CSR = 0 | CORDIC_FUNCTION_COSINE |
                CORDIC_PRECISION_5CYCLES |  // 20 iterations
                CORDIC_SCALE_0 |            // scale x1
                CORDIC_INSIZE_16BITS |      // inputs in q1.15
                CORDIC_OUTSIZE_16BITS |     // outputs in q1.15
                CORDIC_NBWRITE_1 |          // one 32-bit input
                CORDIC_NBREAD_1;            // one 32-bit output

  // angle [degrees] -> phi[radians/PI] 
  int16_t phi = (angle << 15) / 180;

  // CORDIC outputs { phi in radians divided by PI, modulus } in q1.15
  // phi in lower 16-bits, modulus is set to 1.0 in higher 16-bits
  CORDIC->WDATA = (uint16_t)phi + (INT16_MAX << 16);

  // CORDIC inputs { cos(phi), sin(phi) } both in q1.15
  // cosine in lower 16-bits, sine in higher 16-bits
  uint32_t result = CORDIC->RDATA;

  // calculate the vector coordinates
  *_x = ((int16_t)(result & 0xFFFF) * radius) >> 15;
  *_y = ((int16_t)(result >> 16) * radius) >> 15;
}

void quickmath_polar_to_cartesian_vfp(int16_t angle, int16_t radius,
                                      int16_t *_x, int16_t *_y) {
  *_x = cosf(angle * M_PI / 180) * radius;
  *_y = sinf(angle * M_PI / 180) * radius;
}

void quickmath_performance_test() {
  // 32-bit version, ST HAL, 1M iterations

  {
    int32_t x;
    int32_t y;

    int32_t start_ticks = HAL_GetTick();

    for (int i = 0; i < 2000; i++) {
      for (int j = -250; j < 250; j += 1) {
        quickmath_polar_to_cartesian_i32(j, 1000, &x, &y);
      }
    }

    int32_t end_ticks = HAL_GetTick();
    int32_t duration = end_ticks - start_ticks;
    printf("%ld\n", duration);
  }

  // 16-bit version, ST HAL, 1M iterations

  {
    int16_t x;
    int16_t y;

    int32_t start_ticks = HAL_GetTick();

    for (int i = 0; i < 2000; i++) {
      for (int j = -250; j < 250; j += 1) {
        quickmath_polar_to_cartesian_i16(j, 1000, &x, &y);
      }
    }

    int32_t end_ticks = HAL_GetTick();
    int32_t duration = end_ticks - start_ticks;
    printf("%ld\n", duration);
  }

  // 16-bit version, direct access to registers, 1M iterations

  {
    int16_t x;
    int16_t y;

    int32_t start_ticks = HAL_GetTick();

    for (int i = 0; i < 2000; i++) {
      for (int j = -250; j < 250; j += 1) {
        quickmath_polar_to_cartesian_i16_ll(j, 1000, &x, &y);
      }
    }

    int32_t end_ticks = HAL_GetTick();
    int32_t duration = end_ticks - start_ticks;
    printf("%ld\n", duration);
  }

  // 16-bit version, lib sinf/cosf utilizing vfp, 1M iterations

  {
    int16_t x;
    int16_t y;

    int32_t start_ticks = HAL_GetTick();

    for (int i = 0; i < 2000; i++) {
      for (int j = -250; j < 250; j += 1) {
        quickmath_polar_to_cartesian_vfp(j, 1000, &x, &y);
      }
    }

    int32_t end_ticks = HAL_GetTick();
    int32_t duration = end_ticks - start_ticks;
    printf("%ld\n", duration);
  }
}

void quickmath_test() {
  {
    int32_t x;
    int32_t y;

    quickmath_polar_to_cartesian_i32(0, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(45, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(90, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(135, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(180, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(360, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(-45, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(-90, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);

    quickmath_polar_to_cartesian_i32(-180, 1000, &x, &y);
    printf("%ld,%ld\n", x, y);
  }

  {
    int16_t x;
    int16_t y;

    quickmath_polar_to_cartesian_i16_ll(0, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(45, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(90, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(135, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(180, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(360, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(-45, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(-90, 1000, &x, &y);
    printf("%d,%d\n", x, y);

    quickmath_polar_to_cartesian_i16_ll(-180, 1000, &x, &y);
    printf("%d,%d\n", x, y);
  }
}
