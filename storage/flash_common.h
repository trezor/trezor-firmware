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

#define FLASH_BLOCK_SIZE (sizeof(uint32_t) * FLASH_BLOCK_WORDS)

typedef uint32_t flash_block_t[FLASH_BLOCK_WORDS];

#if FLASH_BLOCK_WORDS == 1
#define FLASH_ALIGN(X) (((X) + 3) & ~3)
#define FLASH_IS_ALIGNED(X) (((X)&3) == 0)
#elif FLASH_BLOCK_WORDS == 4
#define FLASH_ALIGN(X) (((X) + 0xF) & ~0xF)
#define FLASH_IS_ALIGNED(X) (((X)&0xF) == 0)
#else
#error Unsupported number of FLASH_BLOCK_WORDS.
#endif

void flash_init(void);

secbool __wur flash_unlock_write(void);
secbool __wur flash_lock_write(void);

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

#if defined FLASH_BIT_ACCESS
secbool __wur flash_area_write_byte(const flash_area_t *area, uint32_t offset,
                                    uint8_t data);
secbool __wur flash_area_write_word(const flash_area_t *area, uint32_t offset,
                                    uint32_t data);
#endif
secbool __wur flash_area_write_block(const flash_area_t *area, uint32_t offset,
                                     const flash_block_t block);

secbool flash_write_block(uint16_t sector, uint32_t offset,
                          const flash_block_t block);

#endif
