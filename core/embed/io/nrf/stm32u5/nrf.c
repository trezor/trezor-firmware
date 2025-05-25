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

#include <io/nrf.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/power_manager.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <util/tsqueue.h>

#include "../crc8.h"
#include "../nrf_internal.h"

#define MAX_SPI_DATA_SIZE (244)

typedef struct {
  uint8_t service_id;
  uint8_t msg_len;
  uint8_t data[MAX_SPI_DATA_SIZE];
  uint8_t crc;
} spi_packet_t;

#define SPI_OVERHEAD_SIZE (sizeof(spi_packet_t) - MAX_SPI_DATA_SIZE)
#define SPI_HEADER_SIZE (SPI_OVERHEAD_SIZE - 1)

#define TX_QUEUE_SIZE (8)

#define START_BYTE (0xA0)

#define CTS_PULSE_RESEND_PERIOD_US 2000

typedef struct {
  spi_packet_t packet;
  nrf_tx_callback_t callback;
  void *context;
} nrf_tx_request_t;

typedef struct {
  UART_HandleTypeDef urt;
  DMA_HandleTypeDef urt_tx_dma;

  uint8_t tx_buffers[TX_QUEUE_SIZE][sizeof(nrf_tx_request_t)];
  tsqueue_entry_t tx_queue_entries[TX_QUEUE_SIZE];
  tsqueue_t tx_queue;
  nrf_tx_request_t tx_request;
  int32_t tx_request_id;

  uint8_t urt_rx_byte;
  uint8_t urt_tx_byte;
  bool urt_tx_complete;
  bool urt_rx_complete;

  SPI_HandleTypeDef spi;
  DMA_HandleTypeDef spi_rx_dma;
  DMA_HandleTypeDef spi_tx_dma;
  spi_packet_t long_rx_buffer;

  EXTI_HandleTypeDef exti;

  bool comm_running;
  bool initialized;
  bool wakeup;

  nrf_rx_callback_t service_listeners[NRF_SERVICE_CNT];

  bool info_valid;
  nrf_info_t info;

  systimer_t *timer;
  bool pending_spi_transaction;

} nrf_driver_t;

static nrf_driver_t g_nrf_driver = {0};

static void nrf_prepare_spi_data(nrf_driver_t *drv);

void nrf_start(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  tsqueue_reset(&drv->tx_queue);

  drv->comm_running = true;

  if (HAL_GPIO_ReadPin(NRF_IN_SPI_REQUEST_PORT, NRF_IN_SPI_REQUEST_PIN) ==
      GPIO_PIN_SET) {
    nrf_prepare_spi_data(drv);
  }
}

static void nrf_complete_current_request(nrf_driver_t *drv,
                                         nrf_status_t status) {
  if (drv->tx_request_id >= 0) {
    if (drv->tx_request.callback != NULL) {
      drv->tx_request.callback(status, drv->tx_request.context);
    }
    drv->tx_request_id = -1;
    memset(&drv->tx_request, 0, sizeof(nrf_tx_request_t));
  }
}

static void nrf_abort_comm(nrf_driver_t *drv) {
  HAL_SPI_Abort(&drv->spi);
  drv->pending_spi_transaction = false;

  nrf_complete_current_request(drv, NRF_STATUS_ERROR);

  while (tsqueue_dequeue(&drv->tx_queue, (uint8_t *)&drv->tx_request,
                         sizeof(nrf_tx_request_t), NULL, NULL)) {
    if (drv->tx_request.callback != NULL) {
      drv->tx_request.callback(NRF_STATUS_ERROR, drv->tx_request.context);
    }
  }

  memset(&drv->tx_request, 0, sizeof(nrf_tx_request_t));

  tsqueue_reset(&drv->tx_queue);
}

void nrf_stop(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  // nrf_signal_off();
  irq_key_t key = irq_lock();
  drv->comm_running = false;
  nrf_abort_comm(drv);
  irq_unlock(key);
}

void nrf_management_rx_cb(const uint8_t *data, uint32_t len) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  switch (data[0]) {
    case MGMT_RESP_INFO:
      drv->info_valid = true;
      memcpy(&drv->info, &data[1], sizeof(drv->info));
      break;
    default:
      break;
  }
}

void nrf_timer_callback(void *context) {
  nrf_driver_t *drv = (nrf_driver_t *)context;
  if (drv->initialized && drv->pending_spi_transaction) {
    nrf_signal_data_ready();
    systick_delay_us(1);
    nrf_signal_no_data();
    systimer_set(drv->timer, 2000);
  }
}

void nrf_init(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (drv->initialized) {
    return;
  }

  __HAL_RCC_USART3_CLK_ENABLE();
  __HAL_RCC_GPDMA1_CLK_ENABLE();
  __HAL_RCC_SPI1_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  memset(drv, 0, sizeof(*drv));
  tsqueue_init(&drv->tx_queue, drv->tx_queue_entries,
               (uint8_t *)drv->tx_buffers, sizeof(nrf_tx_request_t),
               TX_QUEUE_SIZE);

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // synchronization signals
  NRF_OUT_RESET_CLK_ENA();
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_RESET_PIN;
  HAL_GPIO_Init(NRF_OUT_RESET_PORT, &GPIO_InitStructure);

  NRF_IN_RESERVED_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_IN_RESERVED_PIN;
  HAL_GPIO_Init(NRF_IN_RESERVED_PORT, &GPIO_InitStructure);

  NRF_OUT_SPI_READY_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_SPI_READY_PIN;
  HAL_GPIO_Init(NRF_OUT_SPI_READY_PORT, &GPIO_InitStructure);

  NRF_OUT_STAY_IN_BLD_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_OUT_STAY_IN_BLD_PIN;
  HAL_GPIO_Init(NRF_OUT_STAY_IN_BLD_PORT, &GPIO_InitStructure);

  NRF_IN_SPI_REQUEST_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = NRF_IN_SPI_REQUEST_PIN;
  HAL_GPIO_Init(NRF_IN_SPI_REQUEST_PORT, &GPIO_InitStructure);

  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = NRF_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = NRF_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&drv->exti, &EXTI_Config);
  __HAL_GPIO_EXTI_CLEAR_FLAG(NRF_EXTI_INTERRUPT_PIN);

  // UART PINS
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF7_USART3;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

  GPIO_InitStructure.Pin = GPIO_PIN_10 | GPIO_PIN_1;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Pin = GPIO_PIN_11;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = GPIO_PIN_5;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  drv->urt.Init.Mode = UART_MODE_TX_RX;
  drv->urt.Init.BaudRate = 1000000;
  drv->urt.Init.HwFlowCtl = UART_HWCONTROL_RTS_CTS;
  drv->urt.Init.OverSampling = UART_OVERSAMPLING_16;
  drv->urt.Init.Parity = UART_PARITY_NONE;
  drv->urt.Init.StopBits = UART_STOPBITS_1;
  drv->urt.Init.WordLength = UART_WORDLENGTH_8B;
  drv->urt.Instance = USART3;
  HAL_UART_Init(&drv->urt);

  // SPI pins
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF5_SPI1;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_MEDIUM;
  GPIO_InitStructure.Pin = GPIO_PIN_1 | GPIO_PIN_4 | GPIO_PIN_6 | GPIO_PIN_7;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  drv->spi_rx_dma.Instance = GPDMA1_Channel2;
  drv->spi_rx_dma.Init.Direction = DMA_PERIPH_TO_MEMORY;
  drv->spi_rx_dma.Init.Mode = DMA_NORMAL;
  drv->spi_rx_dma.Init.Request = GPDMA1_REQUEST_SPI1_RX;
  drv->spi_rx_dma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  drv->spi_rx_dma.Init.SrcInc = DMA_SINC_FIXED;
  drv->spi_rx_dma.Init.DestInc = DMA_DINC_INCREMENTED;
  drv->spi_rx_dma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_BYTE;
  drv->spi_rx_dma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_BYTE;
  drv->spi_rx_dma.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->spi_rx_dma.Init.SrcBurstLength = 1;
  drv->spi_rx_dma.Init.DestBurstLength = 1;
  drv->spi_rx_dma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  drv->spi_rx_dma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  drv->spi_rx_dma.Parent = &drv->spi;

  HAL_DMA_Init(&drv->spi_rx_dma);
  HAL_DMA_ConfigChannelAttributes(
      &drv->spi_rx_dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC |
                            DMA_CHANNEL_SRC_SEC | DMA_CHANNEL_DEST_SEC);

  drv->spi_tx_dma.Init.Direction = DMA_MEMORY_TO_PERIPH;
  drv->spi_tx_dma.Init.Mode = DMA_NORMAL;
  drv->spi_tx_dma.Instance = GPDMA1_Channel1;
  drv->spi_tx_dma.Init.Request = GPDMA1_REQUEST_SPI1_TX;
  drv->spi_tx_dma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  drv->spi_tx_dma.Init.SrcInc = DMA_SINC_INCREMENTED;
  drv->spi_tx_dma.Init.DestInc = DMA_DINC_FIXED;
  drv->spi_tx_dma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_BYTE;
  drv->spi_tx_dma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_BYTE;
  drv->spi_tx_dma.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->spi_tx_dma.Init.SrcBurstLength = 1;
  drv->spi_tx_dma.Init.DestBurstLength = 1;
  drv->spi_tx_dma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  drv->spi_tx_dma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  drv->spi_tx_dma.Parent = &drv->spi;
  HAL_DMA_Init(&drv->spi_tx_dma);
  HAL_DMA_ConfigChannelAttributes(
      &drv->spi_tx_dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC |
                            DMA_CHANNEL_SRC_SEC | DMA_CHANNEL_DEST_SEC);

  drv->spi.Instance = SPI1;
  drv->spi.Init.Mode = SPI_MODE_SLAVE;
  drv->spi.Init.Direction = SPI_DIRECTION_2LINES;
  drv->spi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->spi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->spi.Init.CLKPhase = SPI_PHASE_1EDGE;
  drv->spi.Init.NSS = SPI_NSS_HARD_INPUT;
  drv->spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
  drv->spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  drv->spi.Init.TIMode = SPI_TIMODE_DISABLE;
  drv->spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  drv->spi.Init.CRCPolynomial = 0;
  drv->spi.hdmarx = &drv->spi_rx_dma;
  drv->spi.hdmatx = &drv->spi_tx_dma;

  HAL_SPI_Init(&drv->spi);

  drv->tx_request_id = -1;

  drv->initialized = true;

  nrf_register_listener(NRF_SERVICE_MANAGEMENT, nrf_management_rx_cb);

  drv->timer = systimer_create(nrf_timer_callback, drv);
  nrf_start();

  NVIC_SetPriority(USART3_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(USART3_IRQn);
  NVIC_SetPriority(GPDMA1_Channel1_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel1_IRQn);
  NVIC_SetPriority(GPDMA1_Channel2_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel2_IRQn);
  NVIC_SetPriority(SPI1_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(SPI1_IRQn);
  NVIC_SetPriority(NRF_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(NRF_EXTI_INTERRUPT_NUM);

  if (HAL_GPIO_ReadPin(NRF_IN_SPI_REQUEST_PORT, NRF_IN_SPI_REQUEST_PIN) ==
      GPIO_PIN_SET) {
    nrf_prepare_spi_data(drv);
  }
}

void nrf_suspend(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  nrf_stop();

  systimer_delete(drv->timer);

  NVIC_DisableIRQ(GPDMA1_Channel1_IRQn);
  NVIC_DisableIRQ(GPDMA1_Channel2_IRQn);
  NVIC_DisableIRQ(SPI1_IRQn);
  NVIC_DisableIRQ(USART3_IRQn);

  __HAL_RCC_SPI1_FORCE_RESET();
  __HAL_RCC_SPI1_RELEASE_RESET();

  __HAL_RCC_USART3_FORCE_RESET();
  __HAL_RCC_USART3_RELEASE_RESET();

  HAL_GPIO_DeInit(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN);
  HAL_GPIO_DeInit(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN);
  HAL_GPIO_DeInit(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN);
  HAL_GPIO_DeInit(NRF_IN_RESERVED_PORT, NRF_IN_RESERVED_PIN);

  // UART Pins

  HAL_GPIO_DeInit(GPIOB, GPIO_PIN_10);
  HAL_GPIO_DeInit(GPIOB, GPIO_PIN_1);
  HAL_GPIO_DeInit(GPIOD, GPIO_PIN_11);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_5);

  // SPI Pins
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_1);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_4);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_6);
  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_7);

  drv->initialized = false;

  drv->pending_spi_transaction = false;
  drv->wakeup = true;
}

void nrf_deinit(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (drv->initialized) {
    NVIC_DisableIRQ(NRF_EXTI_INTERRUPT_NUM);

    HAL_GPIO_DeInit(NRF_IN_SPI_REQUEST_PORT, NRF_IN_SPI_REQUEST_PIN);
    HAL_EXTI_ClearConfigLine(&drv->exti);

    nrf_suspend();
  }
}

bool nrf_register_listener(nrf_service_id_t service,
                           nrf_rx_callback_t callback) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  if (service >= NRF_SERVICE_CNT) {
    return false;
  }

  if (drv->service_listeners[service] != NULL) {
    return false;
  }

  irq_key_t key = irq_lock();
  drv->service_listeners[service] = callback;
  irq_unlock(key);

  return true;
}

void nrf_unregister_listener(nrf_service_id_t service) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  if (service >= NRF_SERVICE_CNT) {
    return;
  }

  irq_key_t key = irq_lock();
  drv->service_listeners[service] = NULL;
  irq_unlock(key);
}

static void nrf_process_msg(nrf_driver_t *drv, const uint8_t *data,
                            uint32_t len, nrf_service_id_t service) {
  if (drv->service_listeners[service] != NULL) {
    drv->service_listeners[service](data, len);
  }
}

static void nrf_prepare_spi_data(nrf_driver_t *drv) {
  if (drv->pending_spi_transaction) {
    return;
  }
  memset(&drv->long_rx_buffer, 0, sizeof(spi_packet_t));
  if (tsqueue_dequeue(&drv->tx_queue, (uint8_t *)&drv->tx_request,
                      sizeof(nrf_tx_request_t), NULL, &drv->tx_request_id)) {
    HAL_SPI_TransmitReceive_DMA(&drv->spi, (uint8_t *)&drv->tx_request.packet,
                                (uint8_t *)&drv->long_rx_buffer,
                                sizeof(spi_packet_t));
  } else {
    memset(&drv->tx_request.packet, 0, sizeof(spi_packet_t));
    HAL_SPI_TransmitReceive_DMA(&drv->spi, (uint8_t *)&drv->tx_request.packet,
                                (uint8_t *)&drv->long_rx_buffer,
                                sizeof(spi_packet_t));
  }

  drv->pending_spi_transaction = true;
  nrf_signal_data_ready();
  systick_delay_us(1);
  nrf_signal_no_data();
  systimer_set(drv->timer, 2000);
}

/// DFU communication
/// ----------------------------------------------------------

void nrf_dfu_comm_send(const uint8_t *data, uint32_t len) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  HAL_UART_Transmit(&drv->urt, (uint8_t *)data, len, 30);
}

uint32_t nrf_dfu_comm_receive(uint8_t *data, uint32_t len) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return 0;
  }

  if (__HAL_UART_GET_FLAG(&drv->urt, UART_FLAG_RXNE)) {
    HAL_StatusTypeDef result = HAL_UART_Receive(&drv->urt, data, len, 30);

    if (result == HAL_OK) {
      return len;
    }

    if (drv->urt.RxXferCount == len) {
      return 0;
    }

    return len - drv->urt.RxXferCount - 1;
  }

  return 0;
}

int32_t nrf_send_msg(nrf_service_id_t service, const uint8_t *data,
                     uint32_t len, nrf_tx_callback_t callback, void *context) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return -1;
  }

  if (len > NRF_MAX_TX_DATA_SIZE) {
    return -1;
  }

  if (service > NRF_SERVICE_CNT) {
    return -1;
  }

  if (!nrf_is_running()) {
    return -1;
  }

  if (!drv->comm_running) {
    return -1;
  }

  int32_t id = 0;

  nrf_tx_request_t tx_request = {0};

  tx_request.callback = callback;
  tx_request.context = context;
  tx_request.packet.service_id = 0xA0 | (uint8_t)service;
  tx_request.packet.msg_len = len;
  memcpy(&tx_request.packet.data, data, len);
  memset(&tx_request.packet.data[len], 0, sizeof(tx_request.packet.data) - len);
  tx_request.packet.crc =
      crc8((uint8_t *)&tx_request.packet, sizeof(tx_request.packet) - 1, 0x07,
           0x00, false);

  tsqueue_enqueue(&drv->tx_queue, (uint8_t *)&tx_request,
                  sizeof(nrf_tx_request_t), &id);

  irq_key_t key = irq_lock();
  if (drv->tx_request_id <= 0 && !tsqueue_empty(&drv->tx_queue)) {
    nrf_prepare_spi_data(drv);
  }
  irq_unlock(key);

  return id;
}

bool nrf_abort_msg(int32_t id) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  bool aborted = tsqueue_abort(&drv->tx_queue, id, NULL, 0, NULL);

  if (aborted) {
    return true;
  }

  irq_key_t key = irq_lock();
  if (drv->tx_request_id == id) {
    drv->tx_request_id = -1;
    irq_unlock(key);
    return true;
  }

  irq_unlock(key);
  return false;
}

static bool nrf_is_valid_startbyte(uint8_t val) {
  if ((val & 0xF0) != 0xA0) {
    return false;
  }

  if ((val & 0x0F) >= NRF_SERVICE_CNT) {
    return false;
  }

  return true;
}

/// UART communication
/// ---------------------------------------------------------

void nrf_uart_send(uint8_t data) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return;
  }

  drv->urt_rx_complete = false;
  drv->urt_tx_complete = false;
  drv->urt_rx_byte = false;
  drv->urt_tx_byte = data;

  drv->urt_tx_byte = data;
  HAL_UART_Transmit(&drv->urt, (uint8_t *)&drv->urt_tx_byte, 1, 30);

  // receive the rest of the message, or new message in any case.
  HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
}

uint8_t nrf_uart_get_received(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return 0;
  }

  if (!drv->urt_rx_complete) {
    return 0;
  }

  return drv->urt_rx_byte;
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    drv->urt_rx_complete = true;
  }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    HAL_UART_Receive_IT(&drv->urt, &drv->urt_rx_byte, 1);
  }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *urt) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized && urt == &drv->urt) {
    drv->urt_tx_complete = true;
  }
}

void USART3_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_UART_IRQHandler(&drv->urt);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

/// SPI communication
/// ----------------------------------------------------------

void GPDMA1_Channel1_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->spi_tx_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

void GPDMA1_Channel2_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_DMA_IRQHandler(&drv->spi_rx_dma);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

void SPI1_IRQHandler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;
  if (drv->initialized) {
    HAL_SPI_IRQHandler(&drv->spi);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

void nrf_spi_transfer_complete(SPI_HandleTypeDef *hspi) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  if (hspi != &drv->spi) {
    return;
  }

  if (!drv->comm_running) {
    return;
  }

  spi_packet_t packet;
  memcpy(&packet, &drv->long_rx_buffer, sizeof(spi_packet_t));

  drv->pending_spi_transaction = false;

  // tx was completed
  nrf_complete_current_request(drv, NRF_STATUS_OK);

  // something to send?
  if (!tsqueue_empty(&drv->tx_queue)) {
    nrf_prepare_spi_data(drv);
  }

  // process received data
  uint8_t crc = crc8((uint8_t *)&packet, MAX_SPI_DATA_SIZE + SPI_HEADER_SIZE,
                     0x07, 0x00, false);

  if (nrf_is_valid_startbyte(packet.service_id) && packet.crc == crc) {
    nrf_process_msg(drv, packet.data, packet.msg_len, packet.service_id & 0x0F);
  }
}

void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
  nrf_spi_transfer_complete(hspi);
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi) {
  nrf_spi_transfer_complete(hspi);
}

void HAL_SPI_ErrorCallback(SPI_HandleTypeDef *hspi) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  if (hspi != &drv->spi) {
    return;
  }

  if (!drv->comm_running) {
    return;
  }

  drv->pending_spi_transaction = false;
  nrf_complete_current_request(drv, NRF_STATUS_ERROR);

  if (!tsqueue_empty(&drv->tx_queue)) {
    nrf_prepare_spi_data(drv);
  }
}

void NRF_EXTI_INTERRUPT_HANDLER(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  nrf_driver_t *drv = &g_nrf_driver;

#ifdef USE_POWER_MANAGER
  if (drv->wakeup) {
    // Inform the power manager module about nrf/ble wakeup
    pm_wakeup_flags_set(PM_WAKEUP_FLAG_BLE);
    drv->wakeup = false;
  }
#endif

  if (drv->initialized && drv->comm_running) {
    if (HAL_GPIO_ReadPin(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN) == 0) {
      nrf_prepare_spi_data(drv);
    }
  }
  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(NRF_EXTI_INTERRUPT_PIN);

  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}

/// GPIO communication
/// ---------------------------------------------------------
bool nrf_force_reset(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);
  return true;
}

bool nrf_reboot_to_bootloader(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);

  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_SET);

  systick_delay_ms(50);

  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);

  systick_delay_ms(100);

  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_RESET);

  return true;
}

void nrf_stay_in_bootloader(bool set) {
  if (set) {
    HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                      GPIO_PIN_SET);
  } else {
    HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                      GPIO_PIN_RESET);
  }
}

bool nrf_in_reserved(void) {
  return HAL_GPIO_ReadPin(NRF_IN_RESERVED_PORT, NRF_IN_RESERVED_PIN) != 0;
}

void nrf_reboot(void) {
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(NRF_OUT_STAY_IN_BLD_PORT, NRF_OUT_STAY_IN_BLD_PIN,
                    GPIO_PIN_RESET);
  systick_delay_ms(50);
  HAL_GPIO_WritePin(NRF_OUT_RESET_PORT, NRF_OUT_RESET_PIN, GPIO_PIN_SET);
}

void nrf_signal_data_ready(void) {
  HAL_GPIO_WritePin(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN,
                    GPIO_PIN_SET);
}

void nrf_signal_no_data(void) {
  HAL_GPIO_WritePin(NRF_OUT_SPI_READY_PORT, NRF_OUT_SPI_READY_PIN,
                    GPIO_PIN_RESET);
}

bool nrf_is_running(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  // todo

  return drv->comm_running;
}

bool nrf_get_info(nrf_info_t *info) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  drv->info_valid = false;

  uint8_t data[1] = {MGMT_CMD_INFO};
  if (!nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL)) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    if (drv->info_valid) {
      memcpy(info, &drv->info, sizeof(nrf_info_t));
      return true;
    }
  }

  return false;
}

bool nrf_system_off(void) {
  nrf_driver_t *drv = &g_nrf_driver;
  if (!drv->initialized) {
    return false;
  }

  uint8_t data[1] = {MGMT_CMD_SYSTEM_OFF};
  if (!nrf_send_msg(NRF_SERVICE_MANAGEMENT, data, 1, NULL, NULL)) {
    return false;
  }

  uint32_t timeout = ticks_timeout(100);

  bool finished = false;

  while (!ticks_expired(timeout) && !finished) {
    irq_key_t key = irq_lock();
    finished = tsqueue_empty(&drv->tx_queue) && !drv->pending_spi_transaction;
    irq_unlock(key);
    __WFI();
  }

  return true;
}

void nrf_set_dfu_mode(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return;
  }

  // TODO
  //  if (nrf_reboot_to_bootloader()) {
  //    drv->mode_current = BLE_MODE_DFU;
  //  } else {
  //    drv->status_valid = false;
  //  }
}

bool nrf_is_dfu_mode(void) {
  nrf_driver_t *drv = &g_nrf_driver;

  if (!drv->initialized) {
    return false;
  }

  return true;
  // TODO
}

#endif
