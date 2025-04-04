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

#include <gfx/dma2d_bitblt.h>
#include <gfx/jpegdec.h>
#include <rtl/sizedefs.h>
#include <sys/systick.h>

// Fixes of STMicro bugs in cmsis-device-u5
#undef JPEG_BASE_S
#define JPEG_BASE_S (AHB1PERIPH_BASE_S + 0x0A000UL)
#undef JPEG_CFR_CEOCF_Pos
#define JPEG_CFR_CEOCF_Pos (5U)
#undef JPEG_CFR_CHPDF_Pos
#define JPEG_CFR_CHPDF_Pos (6U)

// JPEG decoder processing timeout in microseconds.
// The timeout must be selected to be long enough to process a single slice.
// 100us @ 160MHZ CPU clock speed => 8000 CPU cycles
// JPEG decoder issues 1pixel/1cycles => 125 8x8 blocks
#define JPEGDEC_PROCESSING_TIMEOUT_US 100

// JPEG decoder state
struct jpegdec {
  // Set if the decoder is in use
  bool inuse;

  // DMA channel for JPEG data output
  DMA_HandleTypeDef hdma;

  // Current state of the FSM
  jpegdec_state_t state;
  // Decoded image parameters
  jpegdec_image_t image;

  // Decoded image MCU width
  int16_t mcu_width;
  // Decoded image MCU height
  int16_t mcu_height;
  // Decoded image MCU size in bytes
  size_t mcu_size;

  // Decoded YCbCr data for the current slice
  uint32_t ycbcr_buffer[JPEGDEC_YCBCR_BUFFER_SIZE / sizeof(uint32_t)];

  // Current slice x-coordinate
  int16_t slice_x;
  // Current slice y-coordinate
  int16_t slice_y;
  // Current slice width
  int16_t slice_width;
  // Current slice height
  int16_t slice_height;
};

// JPEG decoder instance
jpegdec_t g_jpegdec = {
    .inuse = false,
};

bool jpegdec_open(void) {
  jpegdec_t *dec = &g_jpegdec;

  if (dec->inuse) {
    return false;
  }

  memset(dec, 0, sizeof(jpegdec_t));
  dec->inuse = true;

  __HAL_RCC_JPEG_FORCE_RESET();
  __HAL_RCC_JPEG_RELEASE_RESET();
  __HAL_RCC_JPEG_CLK_ENABLE();

  // Configure JPEG codec for decoding and header parsing
  JPEG->CR |= JPEG_CR_JCEN;
  JPEG->CONFR1 |= JPEG_CONFR1_DE;
  JPEG->CONFR1 |= JPEG_CONFR1_HDR;
  JPEG->CONFR0 |= JPEG_CONFR0_START;
  JPEG->CR |= JPEG_CR_OFF | JPEG_CR_IFF;

  // Configure DMA channel for JPEG data output
  __HAL_RCC_GPDMA1_CLK_ENABLE();
  dec->hdma.Instance = GPDMA1_Channel4;
  dec->hdma.Init.Request = GPDMA1_REQUEST_JPEG_TX;
  dec->hdma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  dec->hdma.Init.Direction = DMA_PERIPH_TO_MEMORY;
  dec->hdma.Init.SrcInc = DMA_SINC_FIXED;
  dec->hdma.Init.DestInc = DMA_DINC_INCREMENTED;
  dec->hdma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_WORD;
  dec->hdma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_WORD;
  dec->hdma.Init.Priority = DMA_LOW_PRIORITY_LOW_WEIGHT;
  dec->hdma.Init.SrcBurstLength = 8;
  dec->hdma.Init.DestBurstLength = 8;
  dec->hdma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  dec->hdma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  dec->hdma.Init.Mode = DMA_NORMAL;

  if (HAL_DMA_Init(&dec->hdma) != HAL_OK) {
    dec->hdma.Instance = NULL;
    goto cleanup;
  }

  if (HAL_DMA_ConfigChannelAttributes(
          &dec->hdma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC | DMA_CHANNEL_SRC_SEC |
                          DMA_CHANNEL_DEST_SEC) != HAL_OK) {
    goto cleanup;
  }

  return true;

cleanup:
  jpegdec_close();
  return false;
}

void jpegdec_close(void) {
  jpegdec_t *dec = &g_jpegdec;

  if (dec->hdma.Instance != NULL) {
    HAL_DMA_Abort(&dec->hdma);
    HAL_DMA_DeInit(&dec->hdma);
  }

  __HAL_RCC_JPEG_CLK_DISABLE();
  __HAL_RCC_JPEG_FORCE_RESET();
  __HAL_RCC_JPEG_RELEASE_RESET();

  memset(dec, 0, sizeof(jpegdec_t));
}

#define READ_REG_FIELD(reg, field) (((reg) & field##_Msk) >> field##_Pos)

// Extracts image parameters from the JPEG codec registers
// and set `dec->image` and `dec->mcu_xxx` fields
static bool jpegdec_extract_header_info(jpegdec_t *dec) {
  jpegdec_image_t image = {0};
  size_t mcu_size = 64;  // Grayscale, 8x8 blocks
  int16_t mcu_width = 8;
  int16_t mcu_height = 8;

  image.height = READ_REG_FIELD(JPEG->CONFR1, JPEG_CONFR1_YSIZE);
  image.width = READ_REG_FIELD(JPEG->CONFR3, JPEG_CONFR3_XSIZE);

  if (image.height == 0 || image.width == 0) {
    // Image size is zero, invalid header
    return false;
  }

  if (image.height > 32767 || image.width > 32767) {
    // Image is too large
    return false;
  }

  // Number of quantization tables
  int n_qt = 1 + READ_REG_FIELD(JPEG->CONFR1, JPEG_CONFR1_NF);

  if (n_qt == 1) {
    // 1 quantization table => Grayscale
    image.format = JPEGDEC_IMAGE_GRAYSCALE;
  } else if (n_qt == 3) {
    // 3 quantization table => YCbCr
    int y_blocks = 1 + READ_REG_FIELD(JPEG->CONFR4, JPEG_CONFR4_NB);
    int cb_blocks = 1 + READ_REG_FIELD(JPEG->CONFR5, JPEG_CONFR5_NB);
    int cr_blocks = 1 + READ_REG_FIELD(JPEG->CONFR6, JPEG_CONFR6_NB);

    mcu_size = (y_blocks + cb_blocks + cr_blocks) * 64;
    mcu_width = (y_blocks == 1) ? 8 : 16;
    mcu_height = (y_blocks == 4) ? 16 : 8;

    if (y_blocks == 2 && cb_blocks == 1 && cr_blocks == 1) {
      // 4:2:2 subsampling
      image.format = JPEGDEC_IMAGE_YCBCR422;
    } else if (y_blocks == 4 && cb_blocks == 1 && cr_blocks == 1) {
      // 4:2:0 subsampling
      image.format = JPEGDEC_IMAGE_YCBCR420;
    } else if (y_blocks == 1 && cb_blocks == 1 && cr_blocks == 1) {
      // 4:4:4 subsampling
      image.format = JPEGDEC_IMAGE_YCBCR444;
    } else {
      // Unsupported subsampling
      return false;
    }
  } else {
    // 2 or 4 quantization tables are not supported
    return false;
  }

  dec->image = image;
  dec->mcu_size = mcu_size;
  dec->mcu_width = mcu_width;
  dec->mcu_height = mcu_height;
  return true;
}

// Starts DMA transfer of the decoded YCbCr data for the current slice
static bool jpegdec_start_dma_transfer(jpegdec_t *dec) {
  // Number ofs MCU that fit into the YCbCr buffer
  int n_ycbcr = sizeof(dec->ycbcr_buffer) / dec->mcu_size;
  // Number ofs MCUs that fit into the RGB buffer
  int n_rgb =
      JPEGDEC_MAX_SLICE_BLOCKS / ((dec->mcu_width * dec->mcu_height) / 64);
  // Number of remaining MCUs in the current row
  int n_row =
      (dec->image.width - dec->slice_x + dec->mcu_width - 1) / dec->mcu_width;
  // Number of MCUs to decode in the current slice
  int mcu_count = MIN(MIN(n_ycbcr, n_rgb), n_row);

  dec->slice_width = dec->mcu_width * mcu_count;
  dec->slice_height = dec->mcu_height;

  if (HAL_DMA_Start(&dec->hdma, (uint32_t)&JPEG->DOR,
                    (uint32_t)dec->ycbcr_buffer,
                    dec->mcu_size * mcu_count) != HAL_OK) {
    return false;
  }

  JPEG->CR |= JPEG_CR_ODMAEN;
  return true;
}

// Feeds the input FIFO with the data from the input buffer.
// Returns `true` if at least one word was written to the FIFO.
static inline bool jpegdec_feed_fifo(jpegdec_t *dec, jpegdec_input_t *inp) {
  // Input FIFO needs data
  uint32_t *ptr = (uint32_t *)&inp->data[inp->offset];
  if (inp->offset + 16 <= inp->size) {
    // Feed the FIFO with 16 bytes
    JPEG->DIR = ptr[0];
    JPEG->DIR = ptr[1];
    JPEG->DIR = ptr[2];
    JPEG->DIR = ptr[3];
    inp->offset += 16;
    return true;
  } else if (inp->offset < inp->size) {
    // Feed the FIFO with the remaining data
    while (inp->offset + 4 < inp->size) {
      JPEG->DIR = *ptr++;
      inp->offset += 4;
    }
    if (inp->offset < inp->size) {
      size_t bits = (inp->size - inp->offset) * 8;
      JPEG->DIR = *ptr & (0xFFFFFFFF >> (32 - bits));
      inp->offset = inp->size;
    }
    return true;
  }

  return false;
}

// Advances the slice coordinates to the next slice.
// Returns `true` if the decoding is complete.
static inline bool jpegdec_advance_slice_coordinates(jpegdec_t *dec) {
  dec->slice_x += dec->slice_width;
  if (dec->slice_x >= dec->image.width) {
    dec->slice_x = 0;
    dec->slice_y += dec->slice_height;
  }
  return dec->slice_y >= dec->image.height;
}

jpegdec_state_t jpegdec_process(jpegdec_input_t *inp) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return JPEGDEC_STATE_ERROR;
  }

  // Check input buffer alignment
  if (inp->offset < inp->size) {
    if (!IS_ALIGNED(inp->offset, 4) ||
        (!IS_ALIGNED(inp->size, 4) && !inp->last_chunk)) {
      return JPEGDEC_STATE_ERROR;
    }
  }

  switch (dec->state) {
    case JPEGDEC_STATE_ERROR:
    case JPEGDEC_STATE_FINISHED:
      return dec->state;

    case JPEGDEC_STATE_SLICE_READY:
      if (jpegdec_advance_slice_coordinates(dec)) {
        dec->state = JPEGDEC_STATE_FINISHED;
        return dec->state;
      }
      // pass through
    case JPEGDEC_STATE_INFO_READY:
      if (!jpegdec_start_dma_transfer(dec)) {
        dec->state = JPEGDEC_STATE_ERROR;
        return dec->state;
      }
      break;

    default:
      break;
  }

  uint64_t expire_time = 0;  // = 0 => not active
  bool timed_out = false;
  uint8_t poll_counter = 0;

  for (;;) {
    uint32_t sr = JPEG->SR;

    if ((sr & JPEG_SR_IFTF) != 0) {
      if (jpegdec_feed_fifo(dec, inp)) {
        expire_time = 0;
        continue;  // Feed the FIFO as fast as possible
      } else if (!inp->last_chunk) {
        dec->state = JPEGDEC_STATE_NEED_DATA;
        break;
      }
    }

    if (__HAL_DMA_GET_FLAG(&dec->hdma, DMA_FLAG_TC)) {
      // Clear status flags and prepare for the next transfer
      HAL_DMA_PollForTransfer(&dec->hdma, HAL_DMA_FULL_TRANSFER, 0);
      dec->state = JPEGDEC_STATE_SLICE_READY;
      break;
    }

    if ((sr & JPEG_SR_HPDF) != 0) {
      // Header parsing is complete
      // Clear the HPDF flag
      JPEG->CFR |= JPEG_CFR_CHPDF;
      bool unexpected_header = dec->image.width > 0;
      if (unexpected_header || !jpegdec_extract_header_info(dec)) {
        dec->state = JPEGDEC_STATE_ERROR;
      } else {
        dec->state = JPEGDEC_STATE_INFO_READY;
      }
      break;
    }

    // Timeout processing (especially `systick_us()`) is quite expensive
    // and therefore it is done only every 16 passes.
    if (poll_counter-- == 0) {
      poll_counter = 16;
      if (expire_time == 0) {
        // The timeout handles two situations:
        // 1) Invalid input data that causes the JPEG codec not produce
        //    any output and the processing is stuck.
        // 2) Unexpected JPEG codec stuck in the processing state.
        expire_time = systick_us() + JPEGDEC_PROCESSING_TIMEOUT_US;
      } else if (timed_out) {
        dec->state = JPEGDEC_STATE_ERROR;
        break;
      } else {
        // `timed_out` flag is checked in the next pass
        timed_out = systick_us() > expire_time;
      }
    }
  }

  if (dec->state == JPEGDEC_STATE_ERROR ||
      dec->state == JPEGDEC_STATE_FINISHED) {
    JPEG->CR &= ~JPEG_CR_JCEN;
    HAL_DMA_Abort(&dec->hdma);
  }

  return dec->state;
}

bool jpegdec_get_info(jpegdec_image_t *image) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return false;
  }

  if (dec->image.width == 0 || dec->image.height == 0) {
    return false;
  }

  *image = dec->image;
  return true;
}

bool jpegdec_get_slice_rgba8888(uint32_t *rgba8888, jpegdec_slice_t *slice) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return false;
  }

  if (dec->state != JPEGDEC_STATE_SLICE_READY) {
    return false;
  }

  if (!IS_ALIGNED((uint32_t)rgba8888, 4)) {
    return false;
  }

  slice->width = dec->slice_width;
  slice->height = dec->slice_height;
  slice->x = dec->slice_x;
  slice->y = dec->slice_y;

  gfx_bitblt_t bb = {
      .height = dec->slice_height,
      .width = dec->slice_width,
      .dst_row = rgba8888,
      .dst_stride = dec->slice_width * 4,
      .dst_x = 0,
      .dst_y = 0,
      .src_row = dec->ycbcr_buffer,
      .src_stride = 0,
      .src_x = 0,
      .src_y = 0,
      .src_fg = 0,
      .src_bg = 0,
      .src_alpha = 255,
  };

  bool result = false;

  switch (dec->image.format) {
    case JPEGDEC_IMAGE_YCBCR420:
      result = dma2d_rgba8888_copy_ycbcr420(&bb);
      break;
    case JPEGDEC_IMAGE_YCBCR422:
      result = dma2d_rgba8888_copy_ycbcr422(&bb);
      break;
    case JPEGDEC_IMAGE_YCBCR444:
      result = dma2d_rgba8888_copy_ycbcr444(&bb);
      break;
    case JPEGDEC_IMAGE_GRAYSCALE:
      result = dma2d_rgba8888_copy_y(&bb);
      break;
    default:
      result = false;
      break;
  }

  // Wait until the DMA transfer is complete so that the caller can use
  // data in the `rgba8888` buffer immediately.
  dma2d_wait();

  return result;
}

// Initialize DMA base copy for fast copying of 8x8 blocks
//
// 'dst_stride' is the number of bytes between the start of two consecutive
// rows in the destination buffer.
static void fast_copy_init(DMA_HandleTypeDef *hdma, size_t dst_stride) {
  hdma->Instance = GPDMA1_Channel13;
  hdma->Init.Request = GPDMA1_REQUEST_HASH_IN;
  hdma->Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  hdma->Init.Direction = DMA_MEMORY_TO_MEMORY;
  hdma->Init.SrcInc = DMA_SINC_INCREMENTED;
  hdma->Init.DestInc = DMA_DINC_INCREMENTED;
  hdma->Init.SrcDataWidth = DMA_SRC_DATAWIDTH_WORD;
  hdma->Init.DestDataWidth = DMA_DEST_DATAWIDTH_WORD;
  hdma->Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  hdma->Init.SrcBurstLength = 2;
  hdma->Init.DestBurstLength = 2;
  hdma->Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  hdma->Init.TransferEventMode = DMA_TCEM_REPEATED_BLOCK_TRANSFER;
  hdma->Init.Mode = DMA_NORMAL;
  HAL_DMA_Init(hdma);
  HAL_DMA_ConfigChannelAttributes(hdma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC |
                                            DMA_CHANNEL_SRC_SEC |
                                            DMA_CHANNEL_DEST_SEC);

  DMA_RepeatBlockConfTypeDef rep = {0};

  rep.DestAddrOffset = dst_stride - 8;
  rep.RepeatCount = 1;
  HAL_DMAEx_ConfigRepeatBlock(hdma, &rep);
}

// Initiate a fast copy of an 8x8 block from 'src' to 'dst'
//
// `src` is expected to be a pointer to the start of an 8x8 block.
// `dst` is expected to be a pointer to destination bitmap buffer
static inline void fast_copy_block(DMA_HandleTypeDef *hdma, uint8_t *dst,
                                   uint8_t *src) {
  while ((hdma->Instance->CSR & DMA_FLAG_IDLE) == 0)
    ;

  hdma->Lock = 0;
  hdma->State = HAL_DMA_STATE_READY;

  HAL_DMA_Start(hdma, (uint32_t)src, (uint32_t)dst, 64);
}

// Deinitialize the DMA base copy
static inline void fast_copy_deinit(DMA_HandleTypeDef *hdma) {
  while ((hdma->Instance->CSR & DMA_FLAG_IDLE) == 0)
    ;

  hdma->Lock = 0;
  hdma->State = HAL_DMA_STATE_READY;

  HAL_DMA_DeInit(hdma);
}

bool jpegdec_get_slice_mono8(uint32_t *mono8, jpegdec_slice_t *slice) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return false;
  }

  if (dec->state != JPEGDEC_STATE_SLICE_READY) {
    return false;
  }

  if (!IS_ALIGNED((uint32_t)mono8, 4)) {
    return false;
  }

  slice->width = dec->slice_width;
  slice->height = dec->slice_height;
  slice->x = dec->slice_x;
  slice->y = dec->slice_y;

  bool result = false;

  switch (dec->image.format) {
    case JPEGDEC_IMAGE_YCBCR420:
      // Not implemented
      break;
    case JPEGDEC_IMAGE_YCBCR422:
      // Not implemented
      break;
    case JPEGDEC_IMAGE_YCBCR444:
      // Not implemented
      break;
    case JPEGDEC_IMAGE_GRAYSCALE: {
      static DMA_HandleTypeDef hdma = {0};
      fast_copy_init(&hdma, dec->slice_width);
      uint8_t *src = (uint8_t *)dec->ycbcr_buffer;
      for (int y = 0; y < dec->slice_height; y += 8) {
        for (int x = 0; x < dec->slice_width; x += 8) {
          uint8_t *dst = (uint8_t *)mono8 + y * dec->slice_width + x;
          fast_copy_block(&hdma, dst, src);
          src += 64;
        }
      }

      fast_copy_deinit(&hdma);
      result = true;
    } break;

    default:
      result = false;
      break;
  }

  return result;
}

#endif  // KERNEL_MODE
