#include "bg_copy.h"
#include "irq.h"

#include STM32_HAL_H

#define MAX_DATA_SIZE 0xFFF0

static volatile uint32_t dma_transfer_remaining = 0;
static volatile uint32_t dma_data_transferred = 0;
static void *data_src = NULL;
static void *data_dst = NULL;
static bg_copy_callback_t bg_copy_callback = NULL;
static DMA_HandleTypeDef DMA_Handle = {0};

void HAL_DMA_XferCpltCallback(DMA_HandleTypeDef *hdma) {
  if (dma_transfer_remaining > MAX_DATA_SIZE) {
    dma_transfer_remaining -= MAX_DATA_SIZE;
    dma_data_transferred += MAX_DATA_SIZE;
  } else {
    dma_data_transferred += dma_transfer_remaining;
    dma_transfer_remaining = 0;
  }

  if (dma_transfer_remaining > 0) {
    uint32_t data_to_send = dma_transfer_remaining > MAX_DATA_SIZE
                                ? MAX_DATA_SIZE
                                : dma_transfer_remaining;

    HAL_DMA_Start_IT(hdma,
                     (uint32_t) & ((uint8_t *)data_src)[dma_data_transferred],
                     (uint32_t)data_dst, data_to_send);
  }
}

void GPDMA1_Channel0_IRQHandler(void) {
  if ((DMA_Handle.Instance->CSR & DMA_CSR_TCF) == 0) {
    // error, abort the transfer and allow the next one to start
    dma_data_transferred = 0;
    dma_transfer_remaining = 0;
  }

  HAL_DMA_IRQHandler(&DMA_Handle);

  if (dma_transfer_remaining == 0) {
    // transfer finished, disable the channel
    HAL_DMA_DeInit(&DMA_Handle);
    HAL_NVIC_DisableIRQ(GPDMA1_Channel0_IRQn);
    data_src = NULL;
    data_dst = NULL;

    if (bg_copy_callback != NULL) {
      bg_copy_callback();
    }
  }
}

bool bg_copy_pending(void) { return dma_transfer_remaining > 0; }

void bg_copy_wait(void) {
  while (dma_transfer_remaining > 0) {
    __WFI();
  }
}

void bg_copy_start_const_out_8(const uint8_t *src, uint8_t *dst, size_t size,
                               bg_copy_callback_t callback) {
  uint32_t data_to_send = size > MAX_DATA_SIZE ? MAX_DATA_SIZE : size;
  dma_transfer_remaining = size;
  dma_data_transferred = 0;
  data_src = (void *)src;
  data_dst = (void *)dst;
  bg_copy_callback = callback;

  // setup DMA for data copy to constant output address

  __HAL_RCC_GPDMA1_CLK_ENABLE();

  /* USER CODE END GPDMA1_Init 1 */
  DMA_Handle.Instance = GPDMA1_Channel0;
  DMA_Handle.XferCpltCallback = HAL_DMA_XferCpltCallback;
  DMA_Handle.Init.Request = GPDMA1_REQUEST_HASH_IN;
  DMA_Handle.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  DMA_Handle.Init.Direction = DMA_MEMORY_TO_MEMORY;
  DMA_Handle.Init.SrcInc = DMA_SINC_INCREMENTED;
  DMA_Handle.Init.DestInc = DMA_DINC_FIXED;
  DMA_Handle.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_BYTE;
  DMA_Handle.Init.DestDataWidth = DMA_DEST_DATAWIDTH_BYTE;
  DMA_Handle.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  DMA_Handle.Init.SrcBurstLength = 1;
  DMA_Handle.Init.DestBurstLength = 1;
  DMA_Handle.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  DMA_Handle.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  DMA_Handle.Init.Mode = DMA_NORMAL;
  HAL_DMA_Init(&DMA_Handle);
  HAL_DMA_ConfigChannelAttributes(&DMA_Handle, DMA_CHANNEL_SEC |
                                                   DMA_CHANNEL_SRC_SEC |
                                                   DMA_CHANNEL_DEST_SEC);

  HAL_NVIC_SetPriority(GPDMA1_Channel0_IRQn, IRQ_PRI_DMA, 0);
  HAL_NVIC_EnableIRQ(GPDMA1_Channel0_IRQn);

  HAL_DMA_Start_IT(&DMA_Handle, (uint32_t)src, (uint32_t)dst, data_to_send);
}

void bg_copy_abort(void) {
  dma_transfer_remaining = 0;
  dma_data_transferred = 0;
  HAL_DMA_Abort(&DMA_Handle);
  HAL_DMA_DeInit(&DMA_Handle);
  HAL_NVIC_DisableIRQ(GPDMA1_Channel0_IRQn);
  data_src = NULL;
  data_dst = NULL;
}
