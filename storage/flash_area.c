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

#include "flash_area.h"
#include <stddef.h>

uint32_t flash_area_get_size(const flash_area_t *area) {
  uint32_t size = 0;
  for (int i = 0; i < area->num_subareas; i++) {
    size += flash_sector_size(area->subarea[i].first_sector,
                              area->subarea[i].num_sectors);
  }
  return size;
}

uint16_t flash_area_total_sectors(const flash_area_t *area) {
  uint16_t total = 0;
  for (int i = 0; i < area->num_subareas; i++) {
    total += area->subarea[i].num_sectors;
  }
  return total;
}

static secbool get_sector_and_offset(const flash_area_t *area, uint32_t offset,
                                     uint16_t *sector_out,
                                     uint32_t *offset_out) {
  for (int i = 0; i < area->num_subareas; i++) {
    // Get the sub-area parameters
    uint16_t first_sector = area->subarea[i].first_sector;
    uint16_t num_sectors = area->subarea[i].num_sectors;
    uint32_t subarea_size = flash_sector_size(first_sector, num_sectors);
    // Does the requested offset start in the sub-area?
    if (offset < subarea_size) {
      uint16_t found_sector = flash_sector_find(first_sector, offset);
      *sector_out = found_sector;
      *offset_out =
          offset - flash_sector_size(first_sector, found_sector - first_sector);
      return sectrue;
    }
    offset -= subarea_size;
  }

  return secfalse;
}

const void *flash_area_get_address(const flash_area_t *area, uint32_t offset,
                                   uint32_t size) {
  for (int i = 0; i < area->num_subareas; i++) {
    // Get sub-area parameters
    uint16_t first_sector = area->subarea[i].first_sector;
    uint16_t num_sectors = area->subarea[i].num_sectors;
    uint32_t subarea_size = flash_sector_size(first_sector, num_sectors);
    // Does the requested block start in the sub-area?
    if (offset < subarea_size) {
      // Does the requested block fit in the sub-area?
      if (offset + size <= subarea_size) {
        const uint8_t *ptr =
            (const uint8_t *)flash_get_address(first_sector, 0, 0);
        // We expect that all sectors/pages in the sub-area make
        // a continuous block of adresses with the same security atributes
        return ptr + offset;
      } else {
        return NULL;
      }
    }
    offset -= subarea_size;
  }
  return NULL;
}

#if defined FLASH_BIT_ACCESS

secbool flash_area_write_byte(const flash_area_t *area, uint32_t offset,
                              uint8_t data) {
  uint16_t sector;
  uint32_t sector_offset;
  if (get_sector_and_offset(area, offset, &sector, &sector_offset) != sectrue) {
    return secfalse;
  }
  return flash_write_byte(sector, sector_offset, data);
}

secbool flash_area_write_word(const flash_area_t *area, uint32_t offset,
                              uint32_t data) {
  uint16_t sector;
  uint32_t sector_offset;
  if (get_sector_and_offset(area, offset, &sector, &sector_offset) != sectrue) {
    return secfalse;
  }
  return flash_write_word(sector, sector_offset, data);
}

secbool flash_area_write_burst(const flash_area_t *area, uint32_t offset,
                               const uint32_t *data) {
  if (offset % (8 * 16) != 0) {
    return secfalse;
  }
  for (int i = 0; i < (8 * 4); i++) {
    if (sectrue !=
        flash_area_write_word(area, offset + i * sizeof(uint32_t), data[i])) {
      return secfalse;
    }
  }
  return sectrue;
}

#else  // not defined FLASH_BIT_ACCESS

secbool flash_area_write_quadword(const flash_area_t *area, uint32_t offset,
                                  const uint32_t *data) {
  uint16_t sector;
  uint32_t sector_offset;
  if (get_sector_and_offset(area, offset, &sector, &sector_offset) != sectrue) {
    return secfalse;
  }
  return flash_write_quadword(sector, sector_offset, data);
}

secbool flash_area_write_burst(const flash_area_t *area, uint32_t offset,
                               const uint32_t *data) {
  uint16_t sector;
  uint32_t sector_offset;
  if (get_sector_and_offset(area, offset, &sector, &sector_offset) != sectrue) {
    return secfalse;
  }
  return flash_write_burst(sector, sector_offset, data);
}

#endif  // not defined FLASH_BIT_ACCESS

secbool flash_area_write_block(const flash_area_t *area, uint32_t offset,
                               const flash_block_t block) {
  if (!FLASH_IS_ALIGNED(offset)) {
    return secfalse;
  }

  uint16_t sector;
  uint32_t sector_offset;
  if (sectrue != get_sector_and_offset(area, offset, &sector, &sector_offset)) {
    return secfalse;
  }

  return flash_write_block(sector, sector_offset, block);
}

secbool flash_area_erase(const flash_area_t *area,
                         void (*progress)(int pos, int len)) {
  return flash_area_erase_bulk(area, 1, progress);
}

static secbool erase_sector(uint16_t sector) {
  secbool result = secfalse;

  if (sectrue != flash_unlock_write()) {
    return secfalse;
  }

  result = flash_sector_erase(sector);

  if (sectrue != flash_lock_write()) {
    return secfalse;
  }

  return result;
}

secbool flash_area_erase_bulk(const flash_area_t *area, int count,
                              void (*progress)(int pos, int len)) {
  int total_sectors = 0;
  int done_sectors = 0;
  for (int a = 0; a < count; a++) {
    for (int i = 0; i < area[a].num_subareas; i++) {
      total_sectors += area[a].subarea[i].num_sectors;
    }
  }
  if (progress) {
    progress(0, total_sectors);
  }

  for (int a = 0; a < count; a++) {
    for (int s = 0; s < area[a].num_subareas; s++) {
      for (int i = 0; i < area[a].subarea[s].num_sectors; i++) {
        int sector = area[a].subarea[s].first_sector + i;

        if (sectrue != erase_sector(sector)) {
          return secfalse;
        }

        done_sectors++;
        if (progress) {
          progress(done_sectors, total_sectors);
        }
      }
    }
  }

  return sectrue;
}

secbool flash_area_erase_partial(const flash_area_t *area, uint32_t offset,
                                 uint32_t *bytes_erased) {
  uint32_t sector_offset = 0;
  *bytes_erased = 0;

  for (int s = 0; s < area->num_subareas; s++) {
    for (int i = 0; i < area->subarea[s].num_sectors; i++) {
      uint32_t sector = area->subarea[s].first_sector + i;
      uint32_t sector_size = flash_sector_size(sector, 1);

      if (offset == sector_offset) {
        if (sectrue != erase_sector(sector)) {
          return secfalse;
        }

        *bytes_erased = sector_size;
        return sectrue;
      }

      sector_offset += sector_size;
    }
  }

  if (offset == sector_offset) {
    return sectrue;
  }

  return secfalse;
}
