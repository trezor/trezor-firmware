#ifdef KERNEL_MODE
#include <trezor_bsp.h>

#include <sys/irq.h>

#include "display_internal.h"

extern uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE];
extern uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE];

extern const uint32_t gfxmmu_lut_config[2 * GFXMMU_LUT_SIZE];

bool display_gfxmmu_init(display_driver_t *drv) {
  __HAL_RCC_GFXMMU_FORCE_RESET();
  __HAL_RCC_GFXMMU_RELEASE_RESET();

  /* GFXMMU clock enable */
  __HAL_RCC_GFXMMU_CLK_ENABLE();

  /* GFXMMU peripheral initialization */
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
      GFXMMU_CACHE_LOCK_BUFFER0; /* NU */
  drv->hlcd_gfxmmu.Init.CachePrefetch.CacheForce =
      GFXMMU_CACHE_FORCE_ENABLE; /* NU */
  drv->hlcd_gfxmmu.Init.CachePrefetch.OutterBufferability =
      GFXMMU_OUTTER_BUFFERABILITY_DISABLE;
  drv->hlcd_gfxmmu.Init.CachePrefetch.OutterCachability =
      GFXMMU_OUTTER_CACHABILITY_DISABLE;
  drv->hlcd_gfxmmu.Init.CachePrefetch.Prefetch = GFXMMU_PREFETCH_DISABLE;
#endif /* GFXMMU_CR_CE */
#if defined(GFXMMU_CR_ACE)
  drv->hlcd_gfxmmu.Init.AddressCache.Activation = DISABLE;
  drv->hlcd_gfxmmu.Init.AddressCache.AddressCacheLockBuffer =
      GFXMMU_ADDRESSCACHE_LOCK_BUFFER0;
#endif /* GFXMMU_CR_ACE */
  drv->hlcd_gfxmmu.Init.Interrupts.Activation = DISABLE;
  drv->hlcd_gfxmmu.Init.Interrupts.UsedInterrupts =
      GFXMMU_AHB_MASTER_ERROR_IT; /* NU */
  if (HAL_GFXMMU_Init(&drv->hlcd_gfxmmu) != HAL_OK) {
    return false;
  }

  /* Initialize LUT */
  if (HAL_GFXMMU_ConfigLut(&drv->hlcd_gfxmmu, 0, LCD_HEIGHT,
                           (uint32_t)&gfxmmu_lut_config) != HAL_OK) {
    return false;
  }

  if (HAL_GFXMMU_DisableLutLines(&drv->hlcd_gfxmmu, LCD_HEIGHT,
                                 1024 - LCD_HEIGHT) != HAL_OK) {
    return false;
  }

  return true;
}
#endif
