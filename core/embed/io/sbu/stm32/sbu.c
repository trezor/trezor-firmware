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

#include <trezor_bsp.h>

#include <io/sbu.h>

#if KERNEL_MODE

void sbu_init(void) {
  SBU_1_CLK_ENA();
  SBU_2_CLK_ENA();

  HAL_GPIO_WritePin(SBU_1_PORT, SBU_1_PIN, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(SBU_2_PORT, SBU_2_PIN, GPIO_PIN_RESET);

  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

  GPIO_InitStructure.Pin = SBU_1_PIN;
  HAL_GPIO_Init(SBU_1_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = SBU_2_PIN;
  HAL_GPIO_Init(SBU_2_PORT, &GPIO_InitStructure);
}

void sbu_set(secbool sbu1, secbool sbu2) {
  HAL_GPIO_WritePin(SBU_1_PORT, SBU_1_PIN,
                    sbu1 == sectrue ? GPIO_PIN_SET : GPIO_PIN_RESET);
  HAL_GPIO_WritePin(SBU_2_PORT, SBU_2_PIN,
                    sbu2 == sectrue ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

#endif
