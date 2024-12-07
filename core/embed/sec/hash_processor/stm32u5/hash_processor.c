#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/hash_processor.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include "memzero.h"
#include "sha2.h"

#ifdef KERNEL_MODE

HASH_HandleTypeDef hhash = {0};
DMA_HandleTypeDef DMA_Handle = {0};

void hash_processor_init(void) {
  __HAL_RCC_HASH_CLK_ENABLE();
  __HAL_RCC_GPDMA1_CLK_ENABLE();

  hhash.Init.DataType = HASH_DATATYPE_8B;
  hhash.hdmain = &DMA_Handle;
  HAL_HASH_Init(&hhash);

  /* USER CODE END GPDMA1_Init 1 */
  DMA_Handle.Instance = GPDMA1_Channel12;
  DMA_Handle.Init.Request = GPDMA1_REQUEST_HASH_IN;
  DMA_Handle.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  DMA_Handle.Init.Direction = DMA_MEMORY_TO_PERIPH;
  DMA_Handle.Init.SrcInc = DMA_SINC_INCREMENTED;
  DMA_Handle.Init.DestInc = DMA_DINC_FIXED;
  DMA_Handle.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_WORD;
  DMA_Handle.Init.DestDataWidth = DMA_DEST_DATAWIDTH_WORD;
  DMA_Handle.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  DMA_Handle.Init.SrcBurstLength = 1;
  DMA_Handle.Init.DestBurstLength = 4;
  DMA_Handle.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  DMA_Handle.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  DMA_Handle.Init.Mode = DMA_NORMAL;
  HAL_DMA_Init(&DMA_Handle);
  HAL_DMA_ConfigChannelAttributes(
      &DMA_Handle, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC | DMA_CHANNEL_SRC_SEC |
                       DMA_CHANNEL_DEST_SEC);

  DMA_Handle.Parent = &hhash;

  NVIC_SetPriority(GPDMA1_Channel12_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel12_IRQn);
}

void GPDMA1_Channel12_IRQHandler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  HAL_DMA_IRQHandler(&DMA_Handle);
  mpu_restore(mpu_mode);
}

static void hash_processor_sha256_calc_dma(const uint8_t *data, uint32_t len,
                                           uint8_t *hash) {
  while (len > 0) {
    uint32_t chunk = len > 0x8000 ? 0x8000 : len;
    bool last = (len - chunk) <= 0;

    __HAL_HASH_SET_MDMAT();

    HAL_HASHEx_SHA256_Start_DMA(&hhash, (uint8_t *)data, chunk);
    while (HAL_HASH_GetState(&hhash) != HAL_HASH_STATE_READY)
      ;

    if (last) {
      HASH->STR |= HASH_STR_DCAL;
      HAL_HASHEx_SHA256_Finish(&hhash, hash, 1000);
    }
    data += chunk;
    len -= chunk;
  }
}

void hash_processor_sha256_calc(const uint8_t *data, uint32_t len,
                                uint8_t *hash) {
  if (((uint32_t)data & 0x3) == 0) {
    hash_processor_sha256_calc_dma(data, len, hash);
  } else {
    HAL_HASHEx_SHA256_Start(&hhash, (uint8_t *)data, len, hash, 1000);
  }
}

void hash_processor_sha256_init(hash_sha256_context_t *ctx) {
  memzero(ctx, sizeof(hash_sha256_context_t));
}

void hash_processor_sha256_update(hash_sha256_context_t *ctx,
                                  const uint8_t *data, uint32_t len) {
  if (ctx->length > 0) {
    uint32_t chunk = HASH_SHA256_BUFFER_SIZE - ctx->length;
    if (chunk > len) {
      chunk = len;
    }
    memcpy(ctx->buffer + ctx->length, data, chunk);
    ctx->length += chunk;
    data += chunk;
    len -= chunk;
    if (ctx->length == HASH_SHA256_BUFFER_SIZE) {
      HAL_HASHEx_SHA256_Accmlt(&hhash, (uint8_t *)ctx->buffer,
                               HASH_SHA256_BUFFER_SIZE);
      ctx->length = 0;
      memzero(ctx->buffer, HASH_SHA256_BUFFER_SIZE);
    }
  }

  uint32_t len_aligned = len & ~(HASH_SHA256_BUFFER_SIZE - 1);
  uint32_t len_rest = len & (HASH_SHA256_BUFFER_SIZE - 1);

  while (len_aligned > 0) {
    uint32_t chunk = len_aligned > 0x8000 ? 0x8000 : len_aligned;
    HAL_HASHEx_SHA256_Accmlt(&hhash, (uint8_t *)data, chunk);
    data += chunk;
    len_aligned -= chunk;
  }

  if (len_rest > 0) {
    memcpy(ctx->buffer, data, len_rest);
    ctx->length = len_rest;
  }
}

void hash_processor_sha256_final(hash_sha256_context_t *ctx, uint8_t *output) {
  uint32_t tmp_out[SHA256_DIGEST_LENGTH / sizeof(uint32_t)] = {0};
  memzero(ctx->buffer + ctx->length, HASH_SHA256_BUFFER_SIZE - ctx->length);
  HAL_HASHEx_SHA256_Accmlt_End(&hhash, (uint8_t *)ctx->buffer, ctx->length,
                               (uint8_t *)tmp_out, 1000);
  ctx->length = 0;
  memzero(ctx->buffer, HASH_SHA256_BUFFER_SIZE);
  memcpy(output, tmp_out, SHA256_DIGEST_LENGTH);
  memzero(tmp_out, sizeof(tmp_out));
}

#endif  // KERNEL_MODE
