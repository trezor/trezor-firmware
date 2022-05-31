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

#include "board_capabilities.h"
#include <string.h>
#include "common.h"

#define handle_fault(msg) \
  (__fatal_error("Fault detected", msg, __FILE__, __LINE__, __func__))

static uint8_t board_name[MODEL_NAME_MAX_LENGTH + 1] = {0};

static struct BoardloaderVersion boardloader_version;

const uint8_t *get_board_name() { return board_name; }

const struct BoardloaderVersion *get_boardloader_version() {
  return &boardloader_version;
}

void parse_boardloader_capabilities() {
  const uint8_t *pos = (const uint8_t *)BOARD_CAPABILITIES_ADDR;
  const uint8_t *end =
      (const uint8_t *)(BOARD_CAPABILITIES_ADDR + BOARD_CAPABILITIES_SIZE);

  if (memcmp(pos, CAPABILITIES_HEADER, 4) != 0) {
    return;
  }

  pos += 4;

  // -2 for possible tag without any data
  while (pos <= end - 2) {
    enum CapabilityTag tag = pos[0];
    uint8_t length = pos[1];
    uint8_t used_length;
    pos += 2;

    if (pos + length > end) {
      handle_fault("Bad capabilities format.");
    }

    switch (tag) {
      case CAPABILITY:
        // not used yet, just advance pointer
        break;
      case MODEL_NAME:
        used_length = MIN(MODEL_NAME_MAX_LENGTH, length);
        memcpy(board_name, pos, used_length);
        board_name[MODEL_NAME_MAX_LENGTH] = 0;
        break;
      case BOARDLOADER_VERSION:
        if (length != sizeof(boardloader_version)) {
          break;
        }
        memcpy(&boardloader_version, pos, length);
        break;
      case TERMINATOR:
        return;
      default:
        break;
    }

    pos += length;
  }
}
