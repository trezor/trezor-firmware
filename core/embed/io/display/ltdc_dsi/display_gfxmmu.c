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
#include <trezor_rtl.h>

#include <sys/irq.h>

#include "display_internal.h"

extern uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE];
extern uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE];

bool display_gfxmmu_init(display_driver_t *drv) {
  // Reset GFXMMU
  __HAL_RCC_GFXMMU_FORCE_RESET();
  __HAL_RCC_GFXMMU_RELEASE_RESET();

  // GFXMMU clock enable
  __HAL_RCC_GFXMMU_CLK_ENABLE();

  // GFXMMU peripheral initialization
  drv->hlcd_gfxmmu.Instance = GFXMMU;
  drv->hlcd_gfxmmu.Init.BlocksPerLine = GFXMMU_192BLOCKS;
  drv->hlcd_gfxmmu.Init.DefaultValue = 0xFFFFFFFFU;
  drv->hlcd_gfxmmu.Init.Buffers.Buf0Address = (uint32_t)physical_frame_buffer_0;
  drv->hlcd_gfxmmu.Init.Buffers.Buf1Address = (uint32_t)physical_frame_buffer_1;
  drv->hlcd_gfxmmu.Init.Buffers.Buf2Address = 0;
  drv->hlcd_gfxmmu.Init.Buffers.Buf3Address = 0;
#if defined(GFXMMU_CR_CE)
  drv->hlcd_gfxmmu.Init.CachePrefetch.Activation = DISABLE;
  drv->hlcd_gfxmmu.Init.CachePrefetch.CacheLock = GFXMMU_CACHE_LOCK_DISABLE;
  drv->hlcd_gfxmmu.Init.CachePrefetch.CacheLockBuffer =
      GFXMMU_CACHE_LOCK_BUFFER0;  // NU
  drv->hlcd_gfxmmu.Init.CachePrefetch.CacheForce =
      GFXMMU_CACHE_FORCE_ENABLE;  // NU
  drv->hlcd_gfxmmu.Init.CachePrefetch.OutterBufferability =
      GFXMMU_OUTTER_BUFFERABILITY_DISABLE;
  drv->hlcd_gfxmmu.Init.CachePrefetch.OutterCachability =
      GFXMMU_OUTTER_CACHABILITY_DISABLE;
  drv->hlcd_gfxmmu.Init.CachePrefetch.Prefetch = GFXMMU_PREFETCH_DISABLE;
#endif  // GFXMMU_CR_CE
#if defined(GFXMMU_CR_ACE)
  drv->hlcd_gfxmmu.Init.AddressCache.Activation = DISABLE;
  drv->hlcd_gfxmmu.Init.AddressCache.AddressCacheLockBuffer =
      GFXMMU_ADDRESSCACHE_LOCK_BUFFER0;
#endif  // GFXMMU_CR_ACE
  drv->hlcd_gfxmmu.Init.Interrupts.Activation = DISABLE;
  drv->hlcd_gfxmmu.Init.Interrupts.UsedInterrupts =
      GFXMMU_AHB_MASTER_ERROR_IT;  // NU
  if (HAL_GFXMMU_Init(&drv->hlcd_gfxmmu) != HAL_OK) {
    memset(&drv->hlcd_gfxmmu, 0, sizeof(drv->hlcd_gfxmmu));
    goto cleanup;
  }

  // Initialize LUT
  if (HAL_GFXMMU_ConfigLut(&drv->hlcd_gfxmmu, 0, LCD_HEIGHT,
                           (uint32_t)panel_lut_get()) != HAL_OK) {
    goto cleanup;
  }

  if (HAL_GFXMMU_DisableLutLines(&drv->hlcd_gfxmmu, LCD_HEIGHT,
                                 1024 - LCD_HEIGHT) != HAL_OK) {
    goto cleanup;
  }

  return true;

cleanup:
  display_gfxmmu_deinit(drv);
  return false;
}

void display_gfxmmu_deinit(display_driver_t *drv) {
  if (drv->hlcd_gfxmmu.Instance != NULL) {
    HAL_GFXMMU_DeInit(&drv->hlcd_gfxmmu);
  }

  __HAL_RCC_GFXMMU_FORCE_RESET();
  __HAL_RCC_GFXMMU_RELEASE_RESET();
  __HAL_RCC_GFXMMU_CLK_DISABLE();

  memset(&drv->hlcd_gfxmmu, 0, sizeof(drv->hlcd_gfxmmu));
}

#endif
