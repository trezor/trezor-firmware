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

#include "dfu.h"
#include "common.h"
#include "fwu.h"
#include "nrf.h"
#include "nrf_internal.h"

static TFwu sFwu;

static uint32_t tick_start = 0;

void txFunction(struct SFwu *fwu, uint8_t *buf, uint8_t len);
static uint8_t readData(uint8_t *data, int maxLen);

void dfu_init(void) {}

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
      nrf_reboot();
      return DFU_SUCCESS;
    }

    if (status == FWU_STATUS_FAILURE) {
      return DFU_FAIL;
    }

    if (hal_ticks_ms() - tick_start > 2000) {
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

  if (!nrf_reboot_to_bootloader()) {
    return DFU_FAIL;
  }

  tick_start = hal_ticks_ms();

  // Prepare the firmware update process.
  fwuInit(&sFwu);

  // Start the firmware update process.
  fwuExec(&sFwu);

  return dfu_update_process();
}

dfu_result_t dfu_update_chunk(uint8_t *data, uint32_t len) {
  tick_start = hal_ticks_ms();

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
  nrf_dfu_comm_send(buf, len);
}

static uint8_t readData(uint8_t *data, int maxLen) {
  return nrf_dfu_comm_receive(data, maxLen);
}

#endif
