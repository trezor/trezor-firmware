#ifndef FLASH_COMMON_H
#define FLASH_COMMON_H

#include <stdint.h>
#include "secbool.h"

typedef struct {
  uint16_t first_sector;
  uint16_t num_sectors;
} flash_subarea_t;

typedef struct {
  flash_subarea_t subarea[4];
  uint8_t num_subareas;
} flash_area_t;

void flash_init(void);

secbool __wur flash_unlock_write(void);
secbool __wur flash_lock_write(void);

const void *flash_get_address(uint16_t sector, uint32_t offset, uint32_t size);
uint32_t flash_sector_size(uint16_t sector);
uint16_t flash_total_sectors(const flash_area_t *area);
int32_t flash_get_sector_num(const flash_area_t *area,
                             uint32_t sector_inner_num);

const void *flash_area_get_address(const flash_area_t *area, uint32_t offset,
                                   uint32_t size);
uint32_t flash_area_get_size(const flash_area_t *area);

secbool __wur flash_area_erase(const flash_area_t *area,
                               void (*progress)(int pos, int len));
secbool __wur flash_area_erase_bulk(const flash_area_t *area, int count,
                                    void (*progress)(int pos, int len));

#if defined FLASH_BYTE_ACCESS
secbool __wur flash_area_write_byte(const flash_area_t *area, uint32_t offset,
                                    uint8_t data);
secbool __wur flash_area_write_word(const flash_area_t *area, uint32_t offset,
                                    uint32_t data);
#endif
secbool __wur flash_area_write_quadword(const flash_area_t *area,
                                        uint32_t offset, const uint32_t *data);

#endif
