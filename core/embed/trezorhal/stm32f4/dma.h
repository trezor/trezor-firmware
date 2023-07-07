// clang-format off

/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2015 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
#ifndef MICROPY_INCLUDED_STM32_DMA_H
#define MICROPY_INCLUDED_STM32_DMA_H

#include STM32_HAL_H

typedef struct _dma_descr_t dma_descr_t;

extern const dma_descr_t dma_SDIO_0;

void dma_init(DMA_HandleTypeDef *dma, const dma_descr_t *dma_descr, uint32_t dir, void *data);
void dma_init_handle(DMA_HandleTypeDef *dma, const dma_descr_t *dma_descr, uint32_t dir, void *data);
void dma_deinit(const dma_descr_t *dma_descr);
void dma_invalidate_channel(const dma_descr_t *dma_descr);

void dma_nohal_init(const dma_descr_t *descr, uint32_t config);
void dma_nohal_deinit(const dma_descr_t *descr);
void dma_nohal_start(const dma_descr_t *descr, uint32_t src_addr, uint32_t dst_addr, uint16_t len);

#endif // MICROPY_INCLUDED_STM32_DMA_H
