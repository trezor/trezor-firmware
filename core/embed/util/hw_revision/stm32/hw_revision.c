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
#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <util/hw_revision.h>

typedef struct {
  uint8_t revision;
  bool initialized;
} hw_revision_t;

static hw_revision_t g_hw_revision;

static uint8_t hw_revision_read(void) {
  bool rev0 =
      GPIO_PIN_SET == HAL_GPIO_ReadPin(HW_REVISION_0_PORT, HW_REVISION_0_PIN);
  bool rev1 =
      GPIO_PIN_SET == HAL_GPIO_ReadPin(HW_REVISION_1_PORT, HW_REVISION_1_PIN);
  bool rev2 =
      GPIO_PIN_SET == HAL_GPIO_ReadPin(HW_REVISION_2_PORT, HW_REVISION_2_PIN);
  bool rev3 = false;
#ifdef HW_REVISION_3_PIN
  rev3 =
      GPIO_PIN_SET == HAL_GPIO_ReadPin(HW_REVISION_3_PORT, HW_REVISION_3_PIN);
#endif

  uint8_t revision = 0;
  revision |= rev0 ? 1 : 0;
  revision |= rev1 ? 2 : 0;
  revision |= rev2 ? 4 : 0;
  revision |= rev3 ? 8 : 0;

  return revision;
}

void hw_revision_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  HW_REVISION_0_CLOCK_ENABLE();
  GPIO_InitStructure.Pin = HW_REVISION_0_PIN;
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = HW_REVISION_PUPD;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  HAL_GPIO_Init(HW_REVISION_0_PORT, &GPIO_InitStructure);

  HW_REVISION_1_CLOCK_ENABLE();
  GPIO_InitStructure.Pin = HW_REVISION_1_PIN;
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = HW_REVISION_PUPD;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  HAL_GPIO_Init(HW_REVISION_1_PORT, &GPIO_InitStructure);

  HW_REVISION_2_CLOCK_ENABLE();
  GPIO_InitStructure.Pin = HW_REVISION_2_PIN;
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = HW_REVISION_PUPD;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  HAL_GPIO_Init(HW_REVISION_2_PORT, &GPIO_InitStructure);

#ifdef HW_REVISION_3_PIN
  GPIO_InitStructure.Pin = HW_REVISION_3_PIN;
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = HW_REVISION_PUPD;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  HAL_GPIO_Init(HW_REVISION_3_PORT, &GPIO_InitStructure);
#endif

  memset(&g_hw_revision, 0, sizeof(hw_revision_t));
  g_hw_revision.revision = hw_revision_read();
  g_hw_revision.initialized = true;

  // deinit the GPIOs to save power
  HAL_GPIO_DeInit(HW_REVISION_0_PORT, HW_REVISION_0_PIN);
  HAL_GPIO_DeInit(HW_REVISION_1_PORT, HW_REVISION_1_PIN);
  HAL_GPIO_DeInit(HW_REVISION_2_PORT, HW_REVISION_2_PIN);
#ifdef HW_REVISION_3_PIN
  HAL_GPIO_DeInit(HW_REVISION_3_PORT, HW_REVISION_3_PIN);
#endif
}

void hw_revision_deinit(void) {
  memset(&g_hw_revision, 0, sizeof(hw_revision_t));
}

uint8_t hw_revision_get(void) {
  hw_revision_t *hw_revision = &g_hw_revision;
  if (!hw_revision->initialized) {
    hw_revision_init();
  }

  return hw_revision->revision;
}

#endif
