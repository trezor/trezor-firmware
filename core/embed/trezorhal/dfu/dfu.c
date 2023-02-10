//
//  main.c
//  nrf52-dfu
//
//  Sample host application to demonstrate the usage of our C library for the
//  Nordic firmware update protocol.
//
//  Created by Andreas Schweizer on 30.11.2018.
//  Copyright © 2018-2019 Classy Code GmbH
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
//

#include STM32_HAL_H
#include "dfu.h"
#include "fwu.h"

static TFwu sFwu;
static UART_HandleTypeDef urt;

static uint32_t tick_start = 0;

void txFunction(struct SFwu *fwu, uint8_t *buf, uint8_t len);
static uint8_t readData(uint8_t *data, int maxLen);

void dfu_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure;

  __HAL_RCC_USART1_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();

  GPIO_InitStructure.Pin = GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Alternate = GPIO_AF7_USART1;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  urt.Init.Mode = UART_MODE_TX_RX;
  urt.Init.BaudRate = 115200;
  urt.Init.HwFlowCtl = UART_HWCONTROL_RTS_CTS;
  urt.Init.OverSampling = UART_OVERSAMPLING_16;
  urt.Init.Parity = UART_PARITY_NONE, urt.Init.StopBits = UART_STOPBITS_1;
  urt.Init.WordLength = UART_WORDLENGTH_8B;
  urt.Instance = USART1;

  HAL_UART_Init(&urt);

  //  sFwu.commandObject = datfile;
  //  sFwu.commandObjectLen = sizeof(datfile);
  //  sFwu.dataObject = NULL;
  //  sFwu.dataObjectLen = sizeof(binfile);
  //  sFwu.txFunction = txFunction;
  //  sFwu.responseTimeoutMillisec = 5000;
}

dfu_result_t dfu_update_process(void) {
  while (1) {
    // Can send 4 chars...
    // (On a microcontroller, you'd use the TX Empty interrupt or test a
    // register.)

    fwuCanSendData(&sFwu, 4);

    // Data available? Get up to 4 bytes...
    // (On a microcontroller, you'd use the RX Available interrupt or test a
    // register.)
    uint8_t rxBuf[4];
    uint8_t rxLen = readData(rxBuf, 4);
    if (rxLen > 0) {
      fwuDidReceiveData(&sFwu, rxBuf, rxLen);
    }

    // Give the firmware update module a timeslot to continue the process.
    EFwuProcessStatus status = fwuYield(&sFwu, 0);

    if (status == FWU_STATUS_COMPLETION) {
      return DFU_SUCCESS;
    }

    if (status == FWU_STATUS_FAILURE) {
      return DFU_FAIL;
    }

    if (HAL_GetTick() - tick_start > 2000) {
      return DFU_FAIL;
    }

    if (fwuIsReadyForChunk(&sFwu)) {
      return DFU_NEXT_CHUNK;
    }
  }
}

dfu_result_t dfu_update_init(uint8_t *data, uint32_t len, uint32_t binary_len) {
  sFwu.commandObject = data;
  sFwu.commandObjectLen = len;
  sFwu.dataObject = NULL;
  sFwu.dataObjectLen = binary_len;
  sFwu.txFunction = txFunction;
  sFwu.responseTimeoutMillisec = 2000;

  tick_start = HAL_GetTick();

  // Prepare the firmware update process.
  fwuInit(&sFwu);

  // Start the firmware update process.
  fwuExec(&sFwu);

  return dfu_update_process();
}

dfu_result_t dfu_update_chunk(uint8_t *data, uint32_t len) {
  tick_start = HAL_GetTick();

  fwuSendChunk(&sFwu, data, len);

  return dfu_update_process();
}

dfu_result_t dfu_update_do(uint8_t *datfile, uint32_t datfile_len,
                           uint8_t *binfile, uint32_t binfile_len) {
  uint32_t chunk_offset = 0;
  uint32_t rem_data = binfile_len;

  dfu_result_t res = dfu_update_init(datfile, datfile_len, binfile_len);

  while (res == DFU_NEXT_CHUNK) {
    // Send the next chunk of the data object.
    uint32_t chunk_size = 4096;
    if (rem_data < 4096) {
      chunk_size = rem_data;
      rem_data = 0;
    } else {
      rem_data -= 4096;
    }
    res = dfu_update_chunk(&binfile[chunk_offset], chunk_size);
    chunk_offset += chunk_size;
  }

  return res;
}

void txFunction(struct SFwu *fwu, uint8_t *buf, uint8_t len) {
  HAL_UART_Transmit(&urt, buf, len, 10);
}

static uint8_t readData(uint8_t *data, int maxLen) {
  HAL_StatusTypeDef result = HAL_UART_Receive(&urt, data, maxLen, 0);

  if (result == HAL_OK) {
    return maxLen;
  } else {
    if (urt.RxXferCount == maxLen) {
      return 0;
    }
    return maxLen - urt.RxXferCount - 1;
  }
}
