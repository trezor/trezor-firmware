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

/*
 * Reference manual:
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/Infineon_I2C_Protocol_v2.03.pdf
 */

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/i2c_bus.h>
#include <sec/optiga_hal.h>
#include <sec/optiga_transport.h>
#include <sys/systick.h>
#include "aes/aesccm.h"
#include "memzero.h"
#include "tls_prf.h"

#ifdef KERNEL_MODE

// Maximum possible packet size that can be transmitted.
#define OPTIGA_MAX_PACKET_SIZE (OPTIGA_DATA_REG_LEN - 5)

// Register address of the data register.
static const uint8_t REG_DATA = 0x80;

// Register address of the register holding the maximum data register length (2
// bytes).
static const uint8_t REG_DATA_LEN = 0x81;

// Register address of the I2C state register (4 bytes).
static const uint8_t REG_I2C_STATE = 0x82;

// Register address of the register that triggers a warm device reset.
static const uint8_t REG_SOFT_RESET = 0x88;

// I2C state register - Device is busy executing a command.
static const uint8_t I2C_STATE_BYTE1_BUSY = 0x80;

// I2C state register - Device is ready to return a response.
static const uint8_t I2C_STATE_BYTE1_RESP_RDY = 0x40;

// I2C base address of Optiga.
static const uint8_t BASE_ADDR = 0x30;

// Constants for our I2C HAL.
static const uint32_t I2C_TIMEOUT_MS = 25;
static const int I2C_MAX_RETRY_COUNT = 10;

// Maximum time in millisecods to retry reading Optiga's response to a command.
// If the SEC is high, then the throttling down delay can be as high as
// t_max = 5000 ms. The maximum time to execute a non-RSA operation is 130 ms.
// We round the total up to the nearest second.
static const int MAX_RETRY_READ_MS = 6000;

// Maximum number of times to retry reading Optiga's response to a command when
// it claims it's not busy executing a command.
static const int MAX_RETRY_READ_NOT_BUSY = 10;

// Maximum number of packets per response. Used for flushing old reponses.
static const int MAX_RESPONSE_PACKET_COUNT = 15;

// Frame control byte - Type.
static const uint8_t FTYPE_MASK = 0x80;
static const uint8_t FTYPE_DATA = 0x00;
static const uint8_t FTYPE_CONTROL = 0x80;

// Frame control byte - Sequence.
static const uint8_t SEQCTR_ACK = 0x00;    // Acknowledge received frame ACKNR.
static const uint8_t SEQCTR_RESET = 0x40;  // Reset frame counter for sync.
static const uint8_t SEQCTR_MASK = 0x60;   // Mask of SEQCTR bits.

// Frame control byte - Frame number.
static const uint8_t FRNR_MASK = 0x0C;
static const uint8_t FRNR_SHIFT = 2;
static const uint8_t ACKNR_MASK = 0x03;

// Packet control byte.
enum {
  PCTR_PRESENTATION_LAYER = 0x08,  // Presentation layer present.
  PCTR_CHAIN_NONE = 0x00,          // No chaining. Single frame.
  PCTR_CHAIN_FIRST = 0x01,         // First packet of a chain.
  PCTR_CHAIN_MIDDLE = 0x02,        // Intermediate packet(s) of a chain.
  PCTR_CHAIN_LAST = 0x04,          // Last packet of a chain.
  PCTR_CHAIN_MASK = 0x07,          // Mask of chain field.
};

// Security control byte.
enum {
  SCTR_HELLO = 0x00,      // Handshake hello message.
  SCTR_FINISHED = 0x08,   // Handshake finished message.
  SCTR_PROTECTED = 0x23,  // Record exchange message. Fully protected.
};

static i2c_bus_t *i2c_bus = NULL;

static uint8_t frame_num_out = 0xff;
static uint8_t frame_num_in = 0xff;
static uint8_t frame_buffer[1 + OPTIGA_DATA_REG_LEN];
static size_t frame_size = 0;  // Set by optiga_read().
static optiga_ui_progress_t ui_progress = NULL;

// Secure channel constants.
#define SEC_CHAN_SCTR_SIZE 1
#define SEC_CHAN_RND_SIZE 32
#define SEC_CHAN_SEQ_SIZE 4
#define SEC_CHAN_TAG_SIZE 8
#define SEC_CHAN_PROTOCOL 1
#define SEC_CHAN_HANDSHAKE_SIZE (SEC_CHAN_RND_SIZE + SEC_CHAN_SEQ_SIZE)
#define SEC_CHAN_CIPHERTEXT_OFFSET (SEC_CHAN_SCTR_SIZE + SEC_CHAN_SEQ_SIZE)
#define SEC_CHAN_OVERHEAD_SIZE \
  (SEC_CHAN_SCTR_SIZE + SEC_CHAN_SEQ_SIZE + SEC_CHAN_TAG_SIZE)
#define SEC_CHAN_SEQ_OFFSET SEC_CHAN_SCTR_SIZE

// Secure channel status.
static bool sec_chan_established = false;
static aes_encrypt_ctx sec_chan_encr_ctx = {0};
static aes_encrypt_ctx sec_chan_decr_ctx = {0};
static uint8_t sec_chan_encr_nonce[8] = {0};
static uint8_t sec_chan_decr_nonce[8] = {0};
static uint8_t *const sec_chan_mseq = &sec_chan_encr_nonce[4];
static uint8_t *const sec_chan_sseq = &sec_chan_decr_nonce[4];

// Static buffer for encrypted commands and responses.
static uint8_t sec_chan_buffer[OPTIGA_MAX_APDU_SIZE + SEC_CHAN_OVERHEAD_SIZE] =
    {0};
static size_t sec_chan_size = 0;

#if PRODUCTION
#define OPTIGA_LOG(prefix, data, data_size)
#else
static optiga_log_hex_t log_hex = NULL;
void optiga_transport_set_log_hex(optiga_log_hex_t f) { log_hex = f; }
#define OPTIGA_LOG(prefix, data, data_size)                                  \
  if (log_hex != NULL) {                                                     \
    static uint8_t prev_data[4];                                             \
    static size_t prev_size = 0;                                             \
    static bool repeated = false;                                            \
    if (prev_size == data_size && memcmp(data, prev_data, data_size) == 0) { \
      if (!repeated) {                                                       \
        repeated = true;                                                     \
        log_hex(prefix "(REPEATED) ", data, data_size);                      \
      }                                                                      \
    } else {                                                                 \
      repeated = false;                                                      \
      if (data_size <= sizeof(prev_data)) {                                  \
        memcpy(prev_data, data, data_size);                                  \
        prev_size = data_size;                                               \
      } else {                                                               \
        prev_size = 0;                                                       \
      }                                                                      \
      log_hex(prefix, data, data_size);                                      \
    }                                                                        \
  }
#endif

void optiga_set_ui_progress(optiga_ui_progress_t f) { ui_progress = f; }

static uint16_t calc_crc_byte(uint16_t seed, uint8_t c) {
  uint16_t h1 = (seed ^ c) & 0xFF;
  uint16_t h2 = h1 & 0x0F;
  uint16_t h3 = (h2 << 4) ^ h1;
  uint16_t h4 = h3 >> 4;
  return (((((h3 << 1) ^ h4) << 4) ^ h2) << 3) ^ h4 ^ (seed >> 8);
}

static uint16_t calc_crc(uint8_t *data, size_t data_size) {
  uint16_t crc = 0;
  for (size_t i = 0; i < data_size; ++i) {
    crc = calc_crc_byte(crc, data[i]);
  }
  return crc;
}

optiga_result optiga_init(void) {
  optiga_hal_init();

  i2c_bus = i2c_bus_open(OPTIGA_I2C_INSTANCE);
  if (i2c_bus == NULL) {
    return OPTIGA_ERR_I2C_OPEN;
  }

  return optiga_set_data_reg_len(OPTIGA_DATA_REG_LEN);
}

static optiga_result optiga_i2c_write(const uint8_t *data, uint16_t data_size) {
  OPTIGA_LOG(">>>", data, data_size)

  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX,
          .size = data_size,
          .ptr = (void *)data,
      },
  };

  i2c_packet_t pkt = {
      .address = BASE_ADDR,
      .timeout = I2C_TIMEOUT_MS,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  for (int try_count = 0; try_count <= I2C_MAX_RETRY_COUNT; ++try_count) {
    if (try_count != 0) {
      systick_delay_ms(1);
    }

    if (I2C_STATUS_OK == i2c_bus_submit_and_wait(i2c_bus, &pkt)) {
      systick_delay_ms(1);
      return OPTIGA_SUCCESS;
    }

    systick_delay_ms(1);
  }
  return OPTIGA_ERR_I2C_WRITE;
}

static optiga_result optiga_i2c_read(uint8_t *buffer, uint16_t buffer_size) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_RX,
          .size = buffer_size,
          .ptr = buffer,
      },
  };

  i2c_packet_t pkt = {
      .address = BASE_ADDR,
      .timeout = I2C_TIMEOUT_MS,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  for (int try_count = 0; try_count <= I2C_MAX_RETRY_COUNT; ++try_count) {
    systick_delay_ms(1);

    if (I2C_STATUS_OK == i2c_bus_submit_and_wait(i2c_bus, &pkt)) {
      OPTIGA_LOG("<<<", buffer, buffer_size)
      return OPTIGA_SUCCESS;
    }
  }

  return OPTIGA_ERR_I2C_READ;
}

optiga_result optiga_resync(void) {
  frame_num_out = 0xff;
  frame_num_in = 0xff;
  uint8_t data[6] = {REG_DATA, FTYPE_CONTROL | SEQCTR_RESET, 0, 0};
  uint16_t crc = calc_crc(&data[1], 3);
  data[4] = crc >> 8;
  data[5] = crc & 0xff;
  return optiga_i2c_write(data, sizeof(data));
}

optiga_result optiga_soft_reset(void) {
  uint8_t data[3] = {REG_SOFT_RESET, 0xff, 0xff};
  optiga_result ret = optiga_i2c_write(data, sizeof(data));
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  frame_num_out = 0xff;
  frame_num_in = 0xff;

  return OPTIGA_SUCCESS;
}

static optiga_result optiga_send_ack(void) {
  // Set up frame control information.
  uint8_t fctr = FTYPE_CONTROL | SEQCTR_ACK;
  fctr |= (frame_num_in & ACKNR_MASK);

  // Compile frame.
  frame_buffer[0] = REG_DATA;
  frame_buffer[1] = fctr;
  frame_buffer[2] = 0;
  frame_buffer[3] = 0;
  uint16_t crc = calc_crc(&frame_buffer[1], 3);
  frame_buffer[4] = crc >> 8;
  frame_buffer[5] = crc & 0xff;

  return optiga_i2c_write(frame_buffer, 6);
}

static optiga_result optiga_check_ack(void) {
  // Expected frame control information byte.
  uint8_t fctr = FTYPE_CONTROL | SEQCTR_ACK;
  fctr |= (frame_num_out & ACKNR_MASK);

  optiga_result ret = OPTIGA_SUCCESS;
  if (frame_size != 3 || frame_buffer[0] != fctr || frame_buffer[1] != 0 ||
      frame_buffer[2] != 0) {
    ret = OPTIGA_ERR_UNEXPECTED;
  }

  frame_size = 0;
  return ret;
}

static optiga_result optiga_ensure_ready(void) {
  optiga_result ret = OPTIGA_SUCCESS;
  for (int i = 0; i < MAX_RESPONSE_PACKET_COUNT; ++i) {
    uint32_t deadline = hal_ticks_ms() + MAX_RETRY_READ_MS;
    do {
      ret = optiga_i2c_write(&REG_I2C_STATE, 1);
      if (OPTIGA_SUCCESS != ret) {
        return ret;
      }

      ret = optiga_i2c_read(frame_buffer, 4);
      if (OPTIGA_SUCCESS != ret) {
        return ret;
      }

      if ((frame_buffer[0] & I2C_STATE_BYTE1_RESP_RDY) != 0) {
        // There is a response that needs to be flushed out.
        break;
      }

      if ((frame_buffer[0] & I2C_STATE_BYTE1_BUSY) == 0) {
        // Not busy and no response that would need to be flushed out.
        return OPTIGA_SUCCESS;
      }
      ret = OPTIGA_ERR_BUSY;
    } while (hal_ticks_ms() < deadline);

    if (ret != OPTIGA_SUCCESS) {
      // Optiga is busy even after maximum retries at reading the I2C state.
      return ret;
    }

    // Flush out the previous response.

    uint16_t size = (frame_buffer[2] << 8) + frame_buffer[3];
    if (size > sizeof(frame_buffer)) {
      return OPTIGA_ERR_SIZE;
    }

    ret = optiga_i2c_write(&REG_DATA, 1);
    if (OPTIGA_SUCCESS != ret) {
      return ret;
    }

    ret = optiga_i2c_read(frame_buffer, size);
    if (OPTIGA_SUCCESS != ret) {
      return ret;
    }

    if (size < 3) {
      return OPTIGA_ERR_UNEXPECTED;
    }

    // Ignore CRC.
    frame_size = size - 2;

    if ((frame_buffer[0] & FTYPE_MASK) == FTYPE_DATA) {
      // Sync frame numbers with Optiga.
      frame_num_in = (frame_buffer[0] & FRNR_MASK) >> FRNR_SHIFT;
      frame_num_out = frame_buffer[0] & ACKNR_MASK;
      ret = optiga_send_ack();
      if (OPTIGA_SUCCESS != ret) {
        return ret;
      }
    } else {
      if ((frame_buffer[0] & SEQCTR_MASK) == SEQCTR_RESET) {
        frame_num_out = 0xff;
        frame_num_in = 0xff;
      }
    }
  }

  return OPTIGA_ERR_TIMEOUT;
}

optiga_result optiga_set_data_reg_len(size_t size) {
  if (size > 0xffff) {
    return OPTIGA_ERR_SIZE;
  }

  // Set the new data register length.
  uint8_t data[3] = {REG_DATA_LEN, size >> 8, size & 0xff};
  optiga_result ret = optiga_i2c_write(data, sizeof(data));
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  // Check that the length was set correctly.
  ret = optiga_i2c_write(&REG_DATA_LEN, 1);
  if (OPTIGA_SUCCESS != ret) {
    return ret;
  }

  ret = optiga_i2c_read(frame_buffer, 2);
  if (OPTIGA_SUCCESS != ret) {
    return ret;
  }

  if ((frame_buffer[0] << 8) + frame_buffer[1] != size) {
    return OPTIGA_ERR_SIZE;
  }
  return OPTIGA_SUCCESS;
}

static optiga_result optiga_read(void) {
  // The number of times we tried reading Optiga's response to a command while
  // it claimed it's not busy executing a command.
  int not_busy_count = 0;

  uint32_t deadline = hal_ticks_ms() + MAX_RETRY_READ_MS;
  do {
    optiga_result ret = optiga_i2c_write(&REG_I2C_STATE, 1);
    if (OPTIGA_SUCCESS != ret) {
      return ret;
    }

    ret = optiga_i2c_read(frame_buffer, 4);
    if (OPTIGA_SUCCESS != ret) {
      return ret;
    }

    if (frame_buffer[0] & I2C_STATE_BYTE1_RESP_RDY) {
      uint16_t size = (frame_buffer[2] << 8) + frame_buffer[3];
      if (size > sizeof(frame_buffer)) {
        return OPTIGA_ERR_SIZE;
      }

      ret = optiga_i2c_write(&REG_DATA, 1);
      if (OPTIGA_SUCCESS != ret) {
        return ret;
      }

      ret = optiga_i2c_read(frame_buffer, size);
      if (OPTIGA_SUCCESS != ret) {
        return ret;
      }

      if (calc_crc(frame_buffer, size - 2) !=
          (frame_buffer[size - 2] << 8) + frame_buffer[size - 1]) {
        return OPTIGA_ERR_CRC;
      }

      frame_size = size - 2;

      return OPTIGA_SUCCESS;
    }

    if ((frame_buffer[0] & I2C_STATE_BYTE1_BUSY) == 0) {
      // Optiga has no response ready and is not busy. This shouldn't happen if
      // we are expecting to read a response. However, we have observed that if
      // we retry reading, then Optiga may return a response.
      if (not_busy_count >= MAX_RETRY_READ_NOT_BUSY) {
        return OPTIGA_ERR_UNEXPECTED;
      }
      not_busy_count += 1;
    }

    if (ui_progress != NULL) {
      ui_progress();
    }
  } while (hal_ticks_ms() < deadline);

  return OPTIGA_ERR_TIMEOUT;
}

static optiga_result optiga_send_packet(uint8_t packet_control_byte,
                                        const uint8_t *packet_data,
                                        size_t packet_data_size) {
  _Static_assert(sizeof(frame_buffer) - 7 >= OPTIGA_MAX_PACKET_SIZE - 1);

  if (packet_data_size > sizeof(frame_buffer) - 7) {
    return OPTIGA_ERR_SIZE;
  }

  // Set up frame control information.
  uint8_t fctr = FTYPE_DATA | SEQCTR_ACK;
  fctr |= (frame_num_out << FRNR_SHIFT) & FRNR_MASK;
  fctr |= (frame_num_in & ACKNR_MASK);

  // Compile frame.
  frame_buffer[0] = REG_DATA;
  frame_buffer[1] = fctr;
  frame_buffer[2] = (packet_data_size + 1) >> 8;
  frame_buffer[3] = (packet_data_size + 1) & 0xff;
  frame_buffer[4] = packet_control_byte;
  memcpy(&frame_buffer[5], packet_data, packet_data_size);
  uint16_t crc = calc_crc(&frame_buffer[1], packet_data_size + 4);
  frame_buffer[packet_data_size + 5] = crc >> 8;
  frame_buffer[packet_data_size + 6] = crc & 0xff;

  return optiga_i2c_write(frame_buffer, packet_data_size + 7);
}

static optiga_result optiga_receive_packet(uint8_t *packet_control_byte,
                                           uint8_t *packet_data,
                                           size_t max_packet_data_size,
                                           size_t *packet_data_size) {
  // Expected frame control information byte.
  uint8_t fctr = FTYPE_DATA | SEQCTR_ACK;
  fctr |= (frame_num_in << FRNR_SHIFT) & FRNR_MASK;
  fctr |= (frame_num_out & ACKNR_MASK);
  *packet_data_size = (frame_buffer[1] << 8) + frame_buffer[2] - 1;
  if (frame_size < 3 || frame_buffer[0] != fctr ||
      *packet_data_size + 4 != frame_size) {
    frame_size = 0;
    return OPTIGA_ERR_UNEXPECTED;
  }
  frame_size = 0;

  if (*packet_data_size > max_packet_data_size) {
    return OPTIGA_ERR_SIZE;
  }

  *packet_control_byte = frame_buffer[3];
  memcpy(packet_data, &frame_buffer[4], *packet_data_size);
  return OPTIGA_SUCCESS;
}

static optiga_result optiga_transceive(
    bool presentation_layer, const uint8_t *request_data, size_t request_size,
    uint8_t *response_data, size_t max_response_size, size_t *response_size) {
  *response_size = 0;
  optiga_result ret = optiga_ensure_ready();
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  uint8_t pctr = 0;
  if (presentation_layer) {
    pctr |= PCTR_PRESENTATION_LAYER;
  }

  // Transmit command packets to OPTIGA.
  uint8_t chain = PCTR_CHAIN_NONE;
  do {
    size_t packet_data_size = 0;
    // The first byte of each packet is the packet control byte pctr, so each
    // packet contains at most OPTIGA_MAX_PACKET_SIZE - 1 bytes of data.
    if (request_size > OPTIGA_MAX_PACKET_SIZE - 1) {
      packet_data_size = OPTIGA_MAX_PACKET_SIZE - 1;
      if (chain == PCTR_CHAIN_NONE) {
        chain = PCTR_CHAIN_FIRST;
      } else {
        chain = PCTR_CHAIN_MIDDLE;
      }
    } else {
      packet_data_size = request_size;
      if (chain != PCTR_CHAIN_NONE) {
        chain = PCTR_CHAIN_LAST;
      }
    }

    frame_num_out += 1;

    ret = optiga_send_packet(pctr | chain, request_data, packet_data_size);
    if (ret != OPTIGA_SUCCESS) {
      return ret;
    }

    request_data += packet_data_size;
    request_size -= packet_data_size;

    ret = optiga_read();
    if (ret != OPTIGA_SUCCESS) {
      return ret;
    }

    if ((frame_buffer[0] & FTYPE_MASK) == FTYPE_DATA) {
      // OPTIGA sometimes doesn't send a separate control frame to ACK receipt,
      // but responds directly with data. It may also respond with data instead
      // of an ACK if there is an error in a multi-packet transmission.
      break;
    }

    ret = optiga_check_ack();
    if (ret != OPTIGA_SUCCESS) {
      return ret;
    }
  } while (request_size != 0);

  // Receive response packets from OPTIGA.
  do {
    frame_num_in += 1;

    // Read only if there is no pending data in the frame buffer. (There will
    // already be data if OPTIGA didn't send a separate control frame in the
    // previous loop.)
    if (frame_size == 0) {
      ret = optiga_read();
      if (ret != OPTIGA_SUCCESS) {
        return ret;
      }
    }

    size_t packet_data_size = 0;
    ret = optiga_receive_packet(&pctr, response_data, max_response_size,
                                &packet_data_size);
    if (ret != OPTIGA_SUCCESS) {
      *response_size = 0;
      return ret;
    }
    *response_size += packet_data_size;
    response_data += packet_data_size;
    max_response_size -= packet_data_size;

    ret = optiga_send_ack();
    if (ret != OPTIGA_SUCCESS) {
      *response_size = 0;
      return ret;
    }

    pctr &= PCTR_CHAIN_MASK;
  } while (pctr == PCTR_CHAIN_FIRST || pctr == PCTR_CHAIN_MIDDLE);

  return request_size == 0 ? OPTIGA_SUCCESS : OPTIGA_ERR_CMD;
}

static void increment_seq(uint8_t seq[SEC_CHAN_SEQ_SIZE]) {
  for (int i = 3; i >= 0; --i) {
    seq[i]++;
    if (seq[i] != 0x00) {
      return;
    }
  }

  sec_chan_established = false;
  memzero(&sec_chan_encr_ctx, sizeof(sec_chan_encr_ctx));
  memzero(&sec_chan_decr_ctx, sizeof(sec_chan_decr_ctx));
  memzero(sec_chan_encr_nonce, sizeof(sec_chan_encr_nonce));
  memzero(sec_chan_decr_nonce, sizeof(sec_chan_decr_nonce));
}

optiga_result optiga_execute_command(const uint8_t *command_data,
                                     size_t command_size,
                                     uint8_t *response_data,
                                     size_t max_response_size,
                                     size_t *response_size) {
  if (!sec_chan_established) {
    return optiga_transceive(false, command_data, command_size, response_data,
                             max_response_size, response_size);
  }
  sec_chan_size = command_size + SEC_CHAN_OVERHEAD_SIZE;
  if (sec_chan_size > sizeof(sec_chan_buffer)) {
    return OPTIGA_ERR_SIZE;
  }

  increment_seq(sec_chan_mseq);

  // Encrypt command.
  sec_chan_buffer[0] = SCTR_PROTECTED;
  memcpy(&sec_chan_buffer[SEC_CHAN_SEQ_OFFSET], sec_chan_mseq,
         SEC_CHAN_SEQ_SIZE);
  uint8_t *ciphertext = &sec_chan_buffer[SEC_CHAN_CIPHERTEXT_OFFSET];
  uint8_t associated_data[8] = {SCTR_PROTECTED, 0, 0, 0, 0, SEC_CHAN_PROTOCOL};
  memcpy(&associated_data[SEC_CHAN_SEQ_OFFSET], sec_chan_mseq,
         SEC_CHAN_SEQ_SIZE);
  associated_data[6] = command_size >> 8;
  associated_data[7] = command_size & 0xff;
  if (EXIT_SUCCESS != aes_ccm_encrypt(&sec_chan_encr_ctx, sec_chan_encr_nonce,
                                      sizeof(sec_chan_encr_nonce),
                                      associated_data, sizeof(associated_data),
                                      command_data, command_size,
                                      SEC_CHAN_TAG_SIZE, ciphertext)) {
    return OPTIGA_ERR_PROCESS;
  }

  // Transmit encrypted command and receive response.
  optiga_result ret =
      optiga_transceive(true, sec_chan_buffer, sec_chan_size, sec_chan_buffer,
                        sizeof(sec_chan_buffer), &sec_chan_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  increment_seq(sec_chan_sseq);

  if (sec_chan_size < SEC_CHAN_OVERHEAD_SIZE ||
      sec_chan_buffer[0] != SCTR_PROTECTED ||
      memcmp(&sec_chan_buffer[SEC_CHAN_SEQ_OFFSET], sec_chan_sseq,
             SEC_CHAN_SEQ_SIZE) != 0) {
    return OPTIGA_ERR_UNEXPECTED;
  }

  *response_size = sec_chan_size - SEC_CHAN_OVERHEAD_SIZE;
  if (*response_size > max_response_size) {
    *response_size = 0;
    return OPTIGA_ERR_SIZE;
  }

  // Decrypt response.
  memcpy(&associated_data[SEC_CHAN_SEQ_OFFSET], sec_chan_sseq,
         SEC_CHAN_SEQ_SIZE);
  associated_data[6] = *response_size >> 8;
  associated_data[7] = *response_size & 0xff;
  if (EXIT_SUCCESS != aes_ccm_decrypt(&sec_chan_decr_ctx, sec_chan_decr_nonce,
                                      sizeof(sec_chan_decr_nonce),
                                      associated_data, sizeof(associated_data),
                                      ciphertext,
                                      *response_size + SEC_CHAN_TAG_SIZE,
                                      SEC_CHAN_TAG_SIZE, response_data)) {
    return OPTIGA_ERR_PROCESS;
  }

  return OPTIGA_SUCCESS;
}

optiga_result optiga_sec_chan_handshake(const uint8_t *secret,
                                        size_t secret_size) {
  static const uint8_t HANDSHAKE_HELLO[] = {SCTR_HELLO, SEC_CHAN_PROTOCOL};

  // Send Handshake Hello.
  optiga_result ret = optiga_transceive(
      true, HANDSHAKE_HELLO, sizeof(HANDSHAKE_HELLO), sec_chan_buffer,
      sizeof(sec_chan_buffer), &sec_chan_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  // Process Handshake Hello response (sctr[1], pver[1], rnd[32], sseq[4]).
  if (sec_chan_size != 2 + SEC_CHAN_RND_SIZE + SEC_CHAN_SEQ_SIZE ||
      sec_chan_buffer[0] != SCTR_HELLO ||
      sec_chan_buffer[1] != SEC_CHAN_PROTOCOL) {
    return OPTIGA_ERR_UNEXPECTED;
  }

  uint8_t payload[SEC_CHAN_HANDSHAKE_SIZE] = {0};
  memcpy(payload, &sec_chan_buffer[2], sizeof(payload));
  uint8_t *rnd = &payload[0];
  uint8_t *sseq = &payload[SEC_CHAN_RND_SIZE];

  // Compute encryption and decryption keys.
  uint8_t encryption_keys[40] = {0};
  tls_prf_sha256(secret, secret_size, (const uint8_t *)"Platform Binding", 16,
                 rnd, SEC_CHAN_RND_SIZE, encryption_keys,
                 sizeof(encryption_keys));
  aes_encrypt_key128(&encryption_keys[0], &sec_chan_encr_ctx);
  aes_encrypt_key128(&encryption_keys[16], &sec_chan_decr_ctx);
  memcpy(&sec_chan_encr_nonce[0], &encryption_keys[32], 4);
  memcpy(&sec_chan_decr_nonce[0], &encryption_keys[36], 4);
  memzero(encryption_keys, sizeof(encryption_keys));

  // Prepare Handshake Finished message (sctr[1], sseq[4], ciphertext[44]).
  uint8_t handshake_finished[SEC_CHAN_HANDSHAKE_SIZE + SEC_CHAN_OVERHEAD_SIZE] =
      {SCTR_FINISHED};
  memcpy(&handshake_finished[SEC_CHAN_SEQ_OFFSET], sseq, SEC_CHAN_SEQ_SIZE);
  uint8_t *ciphertext = &handshake_finished[SEC_CHAN_CIPHERTEXT_OFFSET];
  uint8_t associated_data[8] = {
      SCTR_FINISHED, 0, 0, 0, 0, SEC_CHAN_PROTOCOL, 0, SEC_CHAN_HANDSHAKE_SIZE};
  memcpy(&associated_data[SEC_CHAN_SEQ_OFFSET], sseq, SEC_CHAN_SEQ_SIZE);
  memcpy(sec_chan_mseq, sseq, SEC_CHAN_SEQ_SIZE);
  if (EXIT_SUCCESS != aes_ccm_encrypt(&sec_chan_encr_ctx, sec_chan_encr_nonce,
                                      sizeof(sec_chan_encr_nonce),
                                      associated_data, sizeof(associated_data),
                                      payload, SEC_CHAN_HANDSHAKE_SIZE,
                                      SEC_CHAN_TAG_SIZE, ciphertext)) {
    return OPTIGA_ERR_PROCESS;
  }

  // Send Handshake Finished message.
  ret = optiga_transceive(true, handshake_finished, sizeof(handshake_finished),
                          sec_chan_buffer, sizeof(sec_chan_buffer),
                          &sec_chan_size);
  if (ret != OPTIGA_SUCCESS) {
    return ret;
  }

  // Process response (sctr[1], mseq[4], ciphertext[44]).
  if (sec_chan_size != SEC_CHAN_HANDSHAKE_SIZE + SEC_CHAN_OVERHEAD_SIZE ||
      sec_chan_buffer[0] != SCTR_FINISHED) {
    return OPTIGA_ERR_UNEXPECTED;
  }
  uint8_t *mseq = &sec_chan_buffer[SEC_CHAN_SEQ_OFFSET];
  ciphertext = &sec_chan_buffer[SEC_CHAN_CIPHERTEXT_OFFSET];

  // Verify payload.
  memcpy(sec_chan_sseq, mseq, SEC_CHAN_SEQ_SIZE);
  memcpy(&associated_data[SEC_CHAN_SEQ_OFFSET], mseq, SEC_CHAN_SEQ_SIZE);
  uint8_t response_payload[SEC_CHAN_HANDSHAKE_SIZE] = {0};
  if (EXIT_SUCCESS !=
      aes_ccm_decrypt(&sec_chan_decr_ctx, sec_chan_decr_nonce,
                      sizeof(sec_chan_decr_nonce), associated_data,
                      sizeof(associated_data), ciphertext,
                      SEC_CHAN_HANDSHAKE_SIZE + SEC_CHAN_TAG_SIZE,
                      SEC_CHAN_TAG_SIZE, response_payload)) {
    return OPTIGA_ERR_UNEXPECTED;
  }

  if (memcmp(response_payload, rnd, SEC_CHAN_RND_SIZE) != 0 ||
      memcmp(response_payload + SEC_CHAN_RND_SIZE, mseq, SEC_CHAN_SEQ_SIZE) !=
          0) {
    return OPTIGA_ERR_UNEXPECTED;
  }

  memcpy(sec_chan_mseq, mseq, SEC_CHAN_SEQ_SIZE);
  memcpy(sec_chan_sseq, sseq, SEC_CHAN_SEQ_SIZE);
  sec_chan_established = true;
  return OPTIGA_SUCCESS;
}

#endif  // KERNEL_MODE
