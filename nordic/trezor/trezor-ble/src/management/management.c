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

#include <stdbool.h>
#include <stdint.h>

#include <zephyr/kernel.h>
#include <zephyr/types.h>

#include <app_version.h>
#include <zephyr/logging/log.h>
#include <zephyr/storage/flash_map.h>
#include <zephyr/sys/crc.h>
#include <zephyr/sys/poweroff.h>

#include <errno.h>

#include <signals/signals.h>
#include <trz_comm/trz_comm.h>

#define LOG_MODULE_NAME manangement
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(management_ok, 0, 1);

typedef enum {
  MGMT_CMD_SYSTEM_OFF = 0x00,
  MGMT_CMD_INFO = 0x01,
  MGMT_CMD_START_UART = 0x02,
  MGMT_CMD_STOP_UART = 0x03,
  MGMT_CMD_SUSPEND = 0x04,
  MGMT_CMD_RESUME = 0x05,
} management_cmd_t;

typedef enum {
  MGMT_RESP_INFO = 0,
} management_resp_t;

void management_init(void) { k_sem_give(&management_ok); }

#define IMAGE_HASH_LEN 32
#define IMAGE_TLV_SHA256 0x10

struct image_version {
  uint8_t iv_major;
  uint8_t iv_minor;
  uint16_t iv_revision;
  uint32_t iv_build_num;
} __packed;

struct image_header {
  uint32_t ih_magic;
  uint32_t ih_load_addr;
  uint16_t ih_hdr_size;         /* Size of image header (bytes). */
  uint16_t ih_protect_tlv_size; /* Size of protected TLV area (bytes). */
  uint32_t ih_img_size;         /* Does not include header. */
  uint32_t ih_flags;            /* IMAGE_F_[...]. */
  struct image_version ih_ver;
  uint32_t _pad1;
} __packed;

/**
 * Read the SHA-256 image hash from the TLV trailer of the given flash slot.
 *
 * @param area_id    FLASH_AREA_ID(image_0) or FLASH_AREA_ID(image_1)
 * @param out_hash   Buffer of at least IMAGE_HASH_LEN bytes to receive the hash
 * @return 0 on success, or a negative errno on failure
 */
static int read_image_sha256(uint8_t area_id,
                             uint8_t out_hash[IMAGE_HASH_LEN]) {
  const struct flash_area *fa;
  int rc;

  /* Open the flash area (slot) */
  rc = flash_area_open(area_id, &fa);
  if (rc < 0) {
    return rc;
  }

  /* Read header to get image_size and hdr_size */
  struct image_header hdr;
  rc = flash_area_read(fa, 0, &hdr, sizeof(hdr));
  if (rc < 0) {
    flash_area_close(fa);
    return rc;
  }
  uint32_t img_size = hdr.ih_img_size;
  uint32_t hdr_size = hdr.ih_hdr_size;
  uint32_t tvl1_size = hdr.ih_protect_tlv_size;

  /* Compute start of TLV trailer */
  off_t off = 0 + hdr_size + img_size + tvl1_size + 4;

  /* Scan TLVs until we find the SHA-256 entry */
  while (true) {
    uint16_t tlv_hdr[2];
    rc = flash_area_read(fa, off, tlv_hdr, sizeof(tlv_hdr));
    if (rc < 0) {
      break;
    }
    uint16_t type = tlv_hdr[0];
    uint16_t len = tlv_hdr[1];

    if (type == IMAGE_TLV_SHA256) {
      if (len != IMAGE_HASH_LEN) {
        rc = -EINVAL;
      } else {
        rc = flash_area_read(fa, off + sizeof(tlv_hdr), out_hash,
                             IMAGE_HASH_LEN);
      }
      break;
    }

    off += sizeof(tlv_hdr) + len;
  }

  flash_area_close(fa);
  return rc;
}

static void send_info(void) {
  uint8_t data[9 + IMAGE_HASH_LEN] = {0};

  data[0] = MGMT_RESP_INFO;
  data[1] = APP_VERSION_MAJOR;
  data[2] = APP_VERSION_MINOR;
  data[3] = APP_PATCHLEVEL;
  data[4] = APP_TWEAK;
  data[5] = 0;
  data[6] = signals_is_stay_in_bootloader();
  data[7] = 0;
  data[8] = signals_out_get_reserved();

  read_image_sha256(FLASH_AREA_ID(image_0), &data[9]);

  trz_comm_send_msg(NRF_SERVICE_MANAGEMENT, data, sizeof(data));
}

static void process_command(uint8_t *data, uint16_t len) {
  uint8_t cmd = data[0];
  switch (cmd) {
    case MGMT_CMD_SYSTEM_OFF:
      LOG_INF("System off");
      sys_poweroff();
      break;
    case MGMT_CMD_INFO:
      LOG_INF("Info command");
      send_info();
      break;
    case MGMT_CMD_START_UART:
      LOG_INF("Start UART");
      trz_comm_start_uart();
      break;
    case MGMT_CMD_STOP_UART:
      LOG_INF("Stop UART");
      trz_comm_stop_uart();
      break;
    case MGMT_CMD_SUSPEND:
      LOG_INF("Suspend");
      trz_comm_suspend();
      break;
    case MGMT_CMD_RESUME:
      LOG_INF("Resume");
      trz_comm_resume();
      break;
    default:
      break;
  }
}

void management_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&management_ok, K_FOREVER);

  for (;;) {
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_MANAGEMENT);
    process_command(buf->data, buf->len);
    k_free(buf);
  }
}

K_THREAD_DEFINE(management_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                management_thread, NULL, NULL, NULL, 7, 0, 0);
