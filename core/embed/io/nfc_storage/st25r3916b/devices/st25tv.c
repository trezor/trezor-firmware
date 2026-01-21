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

#include <trezor_rtl.h>
#include <trezor_types.h>

#include <io/nfc_storage.h>

#include "nfc_device.h"
#include "rfal_nfc.h"

typedef struct {
  uint8_t uid[8];
  uint8_t dsfid;
  uint8_t afi;
  uint8_t mem_block_size;
  uint8_t mem_block_count;
  uint8_t ic_reference;
} st25tv_system_info_t;

static bool st25tv_get_system_info(st25tv_system_info_t *system_info);

bool st25tv_identify(void) {
  st25tv_system_info_t s_info = {0};
  if (!st25tv_get_system_info(&s_info)) {
    return false;
  }

  if (s_info.uid[7] != 0xE0 && s_info.uid[6] != 0x02 && s_info.uid[5] != 0x08) {
    return false;
  }

  // Implementation of identification logic
  return true;  // Placeholder return value
}

bool st25tv_check_connection(void) {
  st25tv_system_info_t s_info = {0};
  if (!st25tv_get_system_info(&s_info)) {
    return false;
  }

  return true;  // Placeholder return value
}

bool st25tv_get_mem_struct(nfc_storage_mem_struct_t *mem_struct) {
  st25tv_system_info_t s_info = {0};
  if (!st25tv_get_system_info(&s_info)) {
    return false;
  }

  mem_struct->total_size_bytes = s_info.mem_block_size * s_info.mem_block_count;
  mem_struct->start_address = 0x0000;
  mem_struct->end_address = mem_struct->total_size_bytes - 1;

  return true;  // Placeholder return value
}

bool st25tv_write(uint32_t address, const uint8_t *data, size_t length) {
  st25tv_system_info_t s_info = {0};
  if (!st25tv_get_system_info(&s_info)) {
    return false;
  }

  if (address + length > s_info.mem_block_count * s_info.mem_block_size) {
    // Out of bounds
    return false;
  }

  uint8_t tx_buf[5] = {0};
  uint8_t rx_buf[3];
  uint16_t rx_len = 0;

  int32_t remaining_bytes = length;
  uint8_t *data_p = (uint8_t *)data;
  uint32_t addr = address;

  while (remaining_bytes > 0) {
    // Number of block is encoded in first byte of transceived buffer
    tx_buf[0] = addr / s_info.mem_block_size;
    uint8_t block_offset = addr % s_info.mem_block_size;

    if (block_offset != 0) {
      // Rewritting part of the block, need to read block first and augment just
      // the part we want to write
      st25tv_read(addr - block_offset, &tx_buf[1], s_info.mem_block_size);

      memcpy(&tx_buf[1 + block_offset], data_p,
             MIN(remaining_bytes, s_info.mem_block_size - block_offset));

      rfalNfcvPollerTransceiveReq(
          RFAL_NFCV_CMD_WRITE_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
          RFAL_NFCV_PARAM_SKIP, NULL, tx_buf, sizeof(tx_buf), rx_buf,
          sizeof(rx_buf), &rx_len);

      remaining_bytes -= (s_info.mem_block_size - block_offset);
      data_p += (s_info.mem_block_size - block_offset);
      addr += (s_info.mem_block_size - block_offset);

    } else {
      if (remaining_bytes < s_info.mem_block_size) {
        // Write only part of the block
        st25tv_read(addr, &tx_buf[1], s_info.mem_block_size);
        memcpy(&tx_buf[1], data_p, remaining_bytes);
        remaining_bytes = 0;
        data_p += remaining_bytes;
        addr += remaining_bytes;

        rfalNfcvPollerTransceiveReq(
            RFAL_NFCV_CMD_WRITE_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
            RFAL_NFCV_PARAM_SKIP, NULL, tx_buf, sizeof(tx_buf), rx_buf,
            sizeof(rx_buf), &rx_len);

      } else {
        // Write full block
        memcpy(&tx_buf[1], data_p, s_info.mem_block_size);
        remaining_bytes -= s_info.mem_block_size;
        data_p += s_info.mem_block_size;
        addr += s_info.mem_block_size;

        rfalNfcvPollerTransceiveReq(
            RFAL_NFCV_CMD_WRITE_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
            RFAL_NFCV_PARAM_SKIP, NULL, tx_buf, sizeof(tx_buf), rx_buf,
            sizeof(rx_buf), &rx_len);
      }
    }

    // Check write command response
    if (rx_len != 1 || rx_buf[0] != 0x00) {
      return false;
    }
  }

  // Implementation of write logic
  return true;  // Placeholder return value
}

bool st25tv_read(uint32_t address, uint8_t *data, size_t length) {
  st25tv_system_info_t s_info = {0};
  if (!st25tv_get_system_info(&s_info)) {
    return false;
  }

  if (address + length > s_info.mem_block_count * s_info.mem_block_size) {
    // Out of bounds
    return false;
  }

  uint8_t tx_buf[1] = {0};
  uint8_t rx_buf[7] = {0};
  uint16_t rx_len = 0;

  int32_t remaining_bytes = length;
  uint8_t *data_p = data;
  uint32_t addr = address;

  while (remaining_bytes > 0) {
    uint8_t block_number = addr / s_info.mem_block_size;
    tx_buf[0] = block_number;

    rfalNfcvPollerTransceiveReq(
        RFAL_NFCV_CMD_READ_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
        RFAL_NFCV_PARAM_SKIP, NULL, tx_buf, sizeof(tx_buf), rx_buf,
        sizeof(rx_buf), &rx_len);

    if (rx_len != 5 || rx_buf[0] != 0x00) {
      return false;
    }

    uint8_t copied_bytes;

    if (addr % s_info.mem_block_size != 0) {
      uint8_t block_offset = addr % s_info.mem_block_size;
      memcpy(data_p, &rx_buf[block_offset + 1],
             s_info.mem_block_size - block_offset);
      copied_bytes = s_info.mem_block_size - block_offset;
    } else {
      memcpy(data_p, &rx_buf[1], s_info.mem_block_size);
      copied_bytes = s_info.mem_block_size;
    }

    data_p += copied_bytes;
    addr += copied_bytes;
    remaining_bytes -= copied_bytes;
  }

  return true;  // Placeholder return value
}

bool st25tv_wipe(void) {
  st25tv_system_info_t s_info = {0};
  if (!st25tv_get_system_info(&s_info)) {
    return false;
  }

  uint8_t tx_buf[5] = {0};
  uint8_t rx_buf[3];
  uint16_t rx_bytes = 0;

  for (uint16_t block = 0; block < s_info.mem_block_count; block++) {
    tx_buf[0] = block;

    rfalNfcvPollerTransceiveReq(
        RFAL_NFCV_CMD_WRITE_SINGLE_BLOCK, RFAL_NFCV_REQ_FLAG_DEFAULT,
        RFAL_NFCV_PARAM_SKIP, NULL, tx_buf, sizeof(tx_buf), rx_buf,
        sizeof(rx_buf), &rx_bytes);

    if (rx_bytes != 1 || rx_buf[0] != 0x00) {
      return false;
    }
  }

  return true;
}

bool st25tv_get_system_info(st25tv_system_info_t *system_info) {
  uint8_t response[16] = {0};
  uint16_t received_length = 0;

  rfalNfcvPollerTransceiveReq(0x2BU, RFAL_NFCV_REQ_FLAG_DEFAULT,
                              RFAL_NFCV_PARAM_SKIP, NULL, NULL, 0x0, response,
                              sizeof(response), &received_length);

  if (response[0] == 0x0 && response[1] == 0x0F && received_length == 0xe) {
    // Parse system info
    system_info->dsfid = response[10];
    system_info->afi = response[11];
    system_info->mem_block_count = response[12] + 1;  // Block size in bytes
    system_info->mem_block_size = response[13] + 1;   // Number of blocks
    system_info->ic_reference = response[14];
  } else {
    return false;
  }

  // Read UID from the configuration register directly to be sure it reads out
  // even if the TAG is in silent mode.
  uint8_t data[2] = {
      0xFE,  // FID
      0x01,  // PID
  };

  rfalNfcvPollerTransceiveReq(
      0xA0U, RFAL_NFCV_REQ_FLAG_DEFAULT, RFAL_NFCV_ST_IC_MFG_CODE, NULL, data,
      sizeof(data), response, sizeof(response), &received_length);

  if (response[0] == 0x0 && received_length == 9) {
    memcpy(system_info->uid, &response[1], 8);
    return true;
  }

  return false;
}

#endif
