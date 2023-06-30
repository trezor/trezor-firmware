#include "flash.h"

static uint32_t flash_subarea_get_size(const flash_subarea_t *subarea) {
  uint32_t size = 0;
  for (int s = 0; s < subarea->num_sectors; s++) {
    size += flash_sector_size(subarea->first_sector + s);
  }
  return size;
}

static secbool subarea_get_sector_and_offset(const flash_subarea_t *subarea,
                                             uint32_t offset,
                                             uint16_t *sector_out,
                                             uint32_t *offset_out) {
  uint32_t tmp_offset = offset;
  uint16_t sector = subarea->first_sector;

  // in correct subarea
  for (int s = 0; s < subarea->num_sectors; s++) {
    const uint32_t sector_size = flash_sector_size(sector);
    if (tmp_offset < sector_size) {
      *sector_out = sector;
      *offset_out = tmp_offset;
      return sectrue;
    }
    tmp_offset -= sector_size;
    sector++;
  }
  return secfalse;
}

uint32_t flash_area_get_size(const flash_area_t *area) {
  uint32_t size = 0;
  for (int i = 0; i < area->num_subareas; i++) {
    size += flash_subarea_get_size(&area->subarea[i]);
  }
  return size;
}

uint16_t flash_total_sectors(const flash_area_t *area) {
  uint16_t total = 0;
  for (int i = 0; i < area->num_subareas; i++) {
    total += area->subarea[i].num_sectors;
  }
  return total;
}

int32_t flash_get_sector_num(const flash_area_t *area,
                             uint32_t sector_inner_num) {
  uint16_t sector = 0;
  uint16_t remaining = sector_inner_num;
  for (int i = 0; i < area->num_subareas; i++) {
    if (remaining < area->subarea[i].num_sectors) {
      sector = area->subarea[i].first_sector + remaining;
      return sector;
    } else {
      remaining -= area->subarea[i].num_sectors;
    }
  }

  return -1;
}

static secbool get_sector_and_offset(const flash_area_t *area, uint32_t offset,
                                     uint16_t *sector_out,
                                     uint32_t *offset_out) {
  uint32_t tmp_offset = offset;
  for (int i = 0; i < area->num_subareas; i++) {
    uint32_t sub_size = flash_subarea_get_size(&area->subarea[i]);
    if (tmp_offset >= sub_size) {
      tmp_offset -= sub_size;
      continue;
    }

    return subarea_get_sector_and_offset(&area->subarea[i], tmp_offset,
                                         sector_out, offset_out);
  }
  return secfalse;
}

const void *flash_area_get_address(const flash_area_t *area, uint32_t offset,
                                   uint32_t size) {
  uint16_t sector;
  uint32_t sector_offset;

  if (!get_sector_and_offset(area, offset, &sector, &sector_offset)) {
    return NULL;
  }

  return flash_get_address(sector, sector_offset, size);
}

secbool flash_area_erase(const flash_area_t *area,
                         void (*progress)(int pos, int len)) {
  return flash_area_erase_bulk(area, 1, progress);
}

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

secbool flash_area_write_quadword(const flash_area_t *area, uint32_t offset,
                                  const uint32_t *data) {
  for (int i = 0; i < 4; i++) {
    if (sectrue !=
        flash_area_write_word(area, offset + i * sizeof(uint32_t), data[i])) {
      return secfalse;
    }
  }
  return sectrue;
}
