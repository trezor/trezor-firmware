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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/mpu.h>
#include <util/board_capabilities.h>

#ifdef KERNEL_MODE

static uint32_t board_name = 0;

static struct BoardloaderVersion boardloader_version;

const uint32_t get_board_name() { return board_name; }

const boardloader_version_t *get_boardloader_version() {
  return &boardloader_version;
}

void parse_boardloader_capabilities() {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOARDCAPS);

  const uint8_t *pos = (const uint8_t *)BOARDCAPS_START;
  const uint8_t *end = (const uint8_t *)(BOARDCAPS_START + BOARDCAPS_MAXSIZE);

  if (memcmp(pos, CAPABILITIES_HEADER, 4) != 0) {
    mpu_restore(mpu_mode);
    return;
  }

  pos += 4;

  // -2 for possible tag without any data
  while (pos <= end - 2) {
    enum CapabilityTag tag = pos[0];
    uint8_t length = pos[1];
    pos += 2;

    if (pos + length > end) {
      error_shutdown("Bad capabilities format");
    }

    switch (tag) {
      case TAG_CAPABILITY:
        // not used yet, just advance pointer
        break;
      case TAG_MODEL_NAME:
        if (length != sizeof(uint32_t)) {
          break;
        }
        memcpy((uint8_t *)&board_name, pos, sizeof(uint32_t));
        break;
      case TAG_BOARDLOADER_VERSION:
        if (length != sizeof(boardloader_version)) {
          break;
        }
        memcpy(&boardloader_version, pos, length);
        break;
      case TAG_TERMINATOR:
        mpu_restore(mpu_mode);
        return;
      default:
        break;
    }

    pos += length;
  }

  mpu_restore(mpu_mode);
}

#endif  // KERNEL_MODE
