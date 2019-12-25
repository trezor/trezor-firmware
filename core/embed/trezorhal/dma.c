// clang-format off

/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2015-2019 Damien P. George
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

#include <string.h>
#include <stdint.h>

#include "dma.h"
#include "irq.h"
#include "systick.h"
#include "supervise.h"

#define DMA_IDLE_ENABLED()  (dma_idle.enabled != 0)
#define DMA_SYSTICK_LOG2    (3)
#define DMA_SYSTICK_MASK    ((1 << DMA_SYSTICK_LOG2) - 1)
#define DMA_IDLE_TICK_MAX   (8) // 8*8 = 64 msec
#define DMA_IDLE_TICK(tick) (((tick) & ~(SYSTICK_DISPATCH_NUM_SLOTS - 1) & DMA_SYSTICK_MASK) == 0)

typedef enum {
    dma_id_not_defined=-1,
    dma_id_0,
    dma_id_1,
    dma_id_2,
    dma_id_3,
    dma_id_4,
    dma_id_5,
    dma_id_6,
    dma_id_7,
    dma_id_8,
    dma_id_9,
    dma_id_10,
    dma_id_11,
    dma_id_12,
    dma_id_13,
    dma_id_14,
    dma_id_15,
} dma_id_t;

typedef union {
    uint16_t enabled; // Used to test if both counters are == 0
    uint8_t counter[2];
} dma_idle_count_t;

struct _dma_descr_t {
    DMA_Stream_TypeDef *instance;
    uint32_t sub_instance;
    dma_id_t id;
    const DMA_InitTypeDef *init;
};

// Parameters to dma_init() for SDIO tx and rx.
static const DMA_InitTypeDef dma_init_struct_sdio = {
    .Channel             = 0,
    .Direction           = 0,
    .PeriphInc           = DMA_PINC_DISABLE,
    .MemInc              = DMA_MINC_ENABLE,
    .PeriphDataAlignment = DMA_PDATAALIGN_WORD,
    .MemDataAlignment    = DMA_MDATAALIGN_WORD,
    .Mode                = DMA_PFCTRL,
    .Priority            = DMA_PRIORITY_VERY_HIGH,
    .FIFOMode            = DMA_FIFOMODE_ENABLE,
    .FIFOThreshold       = DMA_FIFO_THRESHOLD_FULL,
    .MemBurst            = DMA_MBURST_INC4,
    .PeriphBurst         = DMA_PBURST_INC4,
};

#define NCONTROLLERS            (2)
#define NSTREAMS_PER_CONTROLLER (8)
#define NSTREAM                 (NCONTROLLERS * NSTREAMS_PER_CONTROLLER)

#define DMA_SUB_INSTANCE_AS_UINT8(dma_channel) (((dma_channel) & DMA_SxCR_CHSEL) >> 25)

#define DMA1_ENABLE_MASK (0x00ff) // Bits in dma_enable_mask corresponding to DMA1
#define DMA2_ENABLE_MASK (0xff00) // Bits in dma_enable_mask corresponding to DMA2

const dma_descr_t dma_SDIO_0 = { DMA2_Stream3, DMA_CHANNEL_4, dma_id_11,  &dma_init_struct_sdio };

static const uint8_t dma_irqn[NSTREAM] = {
    DMA1_Stream0_IRQn,
    DMA1_Stream1_IRQn,
    DMA1_Stream2_IRQn,
    DMA1_Stream3_IRQn,
    DMA1_Stream4_IRQn,
    DMA1_Stream5_IRQn,
    DMA1_Stream6_IRQn,
    DMA1_Stream7_IRQn,
    DMA2_Stream0_IRQn,
    DMA2_Stream1_IRQn,
    DMA2_Stream2_IRQn,
    DMA2_Stream3_IRQn,
    DMA2_Stream4_IRQn,
    DMA2_Stream5_IRQn,
    DMA2_Stream6_IRQn,
    DMA2_Stream7_IRQn,
};

static DMA_HandleTypeDef *dma_handle[NSTREAM] = {NULL};
static uint8_t dma_last_sub_instance[NSTREAM];
static volatile uint32_t dma_enable_mask = 0;
volatile dma_idle_count_t dma_idle;

#define DMA_INVALID_CHANNEL 0xff    // Value stored in dma_last_channel which means invalid

#define DMA1_IS_CLK_ENABLED()   ((RCC->AHB1ENR & RCC_AHB1ENR_DMA1EN) != 0)
#define DMA2_IS_CLK_ENABLED()   ((RCC->AHB1ENR & RCC_AHB1ENR_DMA2EN) != 0)

void DMA1_Stream0_IRQHandler(void) { IRQ_ENTER(DMA1_Stream0_IRQn); if (dma_handle[dma_id_0] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_0]); } IRQ_EXIT(DMA1_Stream0_IRQn); }
void DMA1_Stream1_IRQHandler(void) { IRQ_ENTER(DMA1_Stream1_IRQn); if (dma_handle[dma_id_1] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_1]); } IRQ_EXIT(DMA1_Stream1_IRQn); }
void DMA1_Stream2_IRQHandler(void) { IRQ_ENTER(DMA1_Stream2_IRQn); if (dma_handle[dma_id_2] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_2]); } IRQ_EXIT(DMA1_Stream2_IRQn); }
void DMA1_Stream3_IRQHandler(void) { IRQ_ENTER(DMA1_Stream3_IRQn); if (dma_handle[dma_id_3] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_3]); } IRQ_EXIT(DMA1_Stream3_IRQn); }
void DMA1_Stream4_IRQHandler(void) { IRQ_ENTER(DMA1_Stream4_IRQn); if (dma_handle[dma_id_4] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_4]); } IRQ_EXIT(DMA1_Stream4_IRQn); }
void DMA1_Stream5_IRQHandler(void) { IRQ_ENTER(DMA1_Stream5_IRQn); if (dma_handle[dma_id_5] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_5]); } IRQ_EXIT(DMA1_Stream5_IRQn); }
void DMA1_Stream6_IRQHandler(void) { IRQ_ENTER(DMA1_Stream6_IRQn); if (dma_handle[dma_id_6] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_6]); } IRQ_EXIT(DMA1_Stream6_IRQn); }
void DMA1_Stream7_IRQHandler(void) { IRQ_ENTER(DMA1_Stream7_IRQn); if (dma_handle[dma_id_7] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_7]); } IRQ_EXIT(DMA1_Stream7_IRQn); }
void DMA2_Stream0_IRQHandler(void) { IRQ_ENTER(DMA2_Stream0_IRQn); if (dma_handle[dma_id_8] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_8]); } IRQ_EXIT(DMA2_Stream0_IRQn); }
void DMA2_Stream1_IRQHandler(void) { IRQ_ENTER(DMA2_Stream1_IRQn); if (dma_handle[dma_id_9] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_9]); } IRQ_EXIT(DMA2_Stream1_IRQn); }
void DMA2_Stream2_IRQHandler(void) { IRQ_ENTER(DMA2_Stream2_IRQn); if (dma_handle[dma_id_10] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_10]); } IRQ_EXIT(DMA2_Stream2_IRQn); }
void DMA2_Stream3_IRQHandler(void) { IRQ_ENTER(DMA2_Stream3_IRQn); if (dma_handle[dma_id_11] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_11]); } IRQ_EXIT(DMA2_Stream3_IRQn); }
void DMA2_Stream4_IRQHandler(void) { IRQ_ENTER(DMA2_Stream4_IRQn); if (dma_handle[dma_id_12] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_12]); } IRQ_EXIT(DMA2_Stream4_IRQn); }
void DMA2_Stream5_IRQHandler(void) { IRQ_ENTER(DMA2_Stream5_IRQn); if (dma_handle[dma_id_13] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_13]); } IRQ_EXIT(DMA2_Stream5_IRQn); }
void DMA2_Stream6_IRQHandler(void) { IRQ_ENTER(DMA2_Stream6_IRQn); if (dma_handle[dma_id_14] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_14]); } IRQ_EXIT(DMA2_Stream6_IRQn); }
void DMA2_Stream7_IRQHandler(void) { IRQ_ENTER(DMA2_Stream7_IRQn); if (dma_handle[dma_id_15] != NULL) { HAL_DMA_IRQHandler(dma_handle[dma_id_15]); } IRQ_EXIT(DMA2_Stream7_IRQn); }

static void dma_idle_handler(uint32_t tick);

// Resets the idle counter for the DMA controller associated with dma_id.
static void dma_tickle(dma_id_t dma_id) {
    dma_idle.counter[(dma_id < NSTREAMS_PER_CONTROLLER) ? 0 : 1] = 1;
    systick_enable_dispatch(SYSTICK_DISPATCH_DMA, dma_idle_handler);
}

static void dma_enable_clock(dma_id_t dma_id) {
    // We don't want dma_tick_handler() to turn off the clock right after we
    // enable it, so we need to mark the channel in use in an atomic fashion.
    uint32_t irq_state = disable_irq();
    uint32_t old_enable_mask = dma_enable_mask;
    dma_enable_mask |= (1 << dma_id);
    enable_irq(irq_state);

    if (dma_id < NSTREAMS_PER_CONTROLLER) {
        if (((old_enable_mask & DMA1_ENABLE_MASK) == 0) && !DMA1_IS_CLK_ENABLED()) {
            __HAL_RCC_DMA1_CLK_ENABLE();

            // We just turned on the clock. This means that anything stored
            // in dma_last_channel (for DMA1) needs to be invalidated.

            for (int channel = 0; channel < NSTREAMS_PER_CONTROLLER; channel++) {
                dma_last_sub_instance[channel] = DMA_INVALID_CHANNEL;
            }
        }
    }
    #if defined(DMA2)
    else {
        if (((old_enable_mask & DMA2_ENABLE_MASK) == 0) && !DMA2_IS_CLK_ENABLED()) {
            __HAL_RCC_DMA2_CLK_ENABLE();

            // We just turned on the clock. This means that anything stored
            // in dma_last_channel (for DMA2) needs to be invalidated.

            for (int channel = NSTREAMS_PER_CONTROLLER; channel < NSTREAM; channel++) {
                dma_last_sub_instance[channel] = DMA_INVALID_CHANNEL;
            }
        }
    }
    #endif
}

static void dma_disable_clock(dma_id_t dma_id) {
    // We just mark the clock as disabled here, but we don't actually disable it.
    // We wait for the timer to expire first, which means that back-to-back
    // transfers don't have to initialize as much.
    dma_tickle(dma_id);
    dma_enable_mask &= ~(1 << dma_id);
}

void dma_init_handle(DMA_HandleTypeDef *dma, const dma_descr_t *dma_descr, uint32_t dir, void *data) {
    // initialise parameters
    dma->Instance = dma_descr->instance;
    dma->Init = *dma_descr->init;
    dma->Init.Direction = dir;
    dma->Init.Channel = dma_descr->sub_instance;
    // half of __HAL_LINKDMA(data, xxx, *dma)
    // caller must implement other half by doing: data->xxx = dma
    dma->Parent = data;
}

void dma_init(DMA_HandleTypeDef *dma, const dma_descr_t *dma_descr, uint32_t dir, void *data){
    // Some drivers allocate the DMA_HandleTypeDef from the stack
    // (i.e. dac, i2c, spi) and for those cases we need to clear the
    // structure so we don't get random values from the stack)
    memset(dma, 0, sizeof(*dma));

    if (dma_descr != NULL) {
        dma_id_t dma_id  = dma_descr->id;

        dma_init_handle(dma, dma_descr, dir, data);
        // set global pointer for IRQ handler
        dma_handle[dma_id] = dma;

        dma_enable_clock(dma_id);

        // if this stream was previously configured for this channel/request and direction then we
        // can skip most of the initialisation
        uint8_t sub_inst = DMA_SUB_INSTANCE_AS_UINT8(dma_descr->sub_instance) | (dir == DMA_PERIPH_TO_MEMORY) << 7;
        if (dma_last_sub_instance[dma_id] != sub_inst) {
            dma_last_sub_instance[dma_id] = sub_inst;

            // reset and configure DMA peripheral
            // (dma->State is set to HAL_DMA_STATE_RESET by memset above)
            HAL_DMA_DeInit(dma);
            HAL_DMA_Init(dma);
            svc_setpriority(IRQn_NONNEG(dma_irqn[dma_id]), IRQ_PRI_DMA);
        } else {
            // only necessary initialization
            dma->State = HAL_DMA_STATE_READY;
            // calculate DMA base address and bitshift to be used in IRQ handler
            extern uint32_t DMA_CalcBaseAndBitshift(DMA_HandleTypeDef *hdma);
            DMA_CalcBaseAndBitshift(dma);
        }

        svc_enableIRQ(dma_irqn[dma_id]);
    }
}

void dma_deinit(const dma_descr_t *dma_descr) {
    if (dma_descr != NULL) {
        svc_disableIRQ(dma_irqn[dma_descr->id]);
        dma_handle[dma_descr->id] = NULL;

        dma_disable_clock(dma_descr->id);
    }
}

void dma_invalidate_channel(const dma_descr_t *dma_descr) {
    if (dma_descr != NULL) {
        dma_id_t dma_id = dma_descr->id;
        // Only compare the sub-instance, not the direction bit (MSB)
        if ((dma_last_sub_instance[dma_id] & 0x7f) == DMA_SUB_INSTANCE_AS_UINT8(dma_descr->sub_instance) ) {
            dma_last_sub_instance[dma_id] = DMA_INVALID_CHANNEL;
        }
    }
}
// Called from the SysTick handler
// We use LSB of tick to select which controller to process
static void dma_idle_handler(uint32_t tick) {
    if (!DMA_IDLE_ENABLED() || !DMA_IDLE_TICK(tick)) {
        return;
    }

    static const uint32_t   controller_mask[] = {
        DMA1_ENABLE_MASK,
        #if defined(DMA2)
        DMA2_ENABLE_MASK,
        #endif
    };
    {
        int controller = (tick >> DMA_SYSTICK_LOG2) & 1;
        if (dma_idle.counter[controller] == 0) {
            return;
        }
        if (++dma_idle.counter[controller] > DMA_IDLE_TICK_MAX) {
            if ((dma_enable_mask & controller_mask[controller]) == 0) {
                // Nothing is active and we've reached our idle timeout,
                // Now we'll really disable the clock.
                dma_idle.counter[controller] = 0;
                if (controller == 0) {
                    __HAL_RCC_DMA1_CLK_DISABLE();
                }
                #if defined(DMA2)
                else {
                    __HAL_RCC_DMA2_CLK_DISABLE();
                }
                #endif
            } else {
                // Something is still active, but the counter never got
                // reset, so we'll reset the counter here.
                dma_idle.counter[controller] = 1;
            }
        }
    }
}
