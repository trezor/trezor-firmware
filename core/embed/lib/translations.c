#include "translations.h"
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include "common.h"
#include "flash.h"
#include "model.h"

bool translations_write(const uint8_t* data, uint32_t offset, uint32_t len) {
  uint32_t size = translations_area_bytesize();
  if (offset > size || size - offset < len) {
    return false;
  }

  ensure(flash_unlock_write(), "translations_write unlock");
  for (int i = 0; i < (len / FLASH_BLOCK_SIZE); i++) {
    // todo consider alignment
    ensure(flash_area_write_block(&TRANSLATIONS_AREA,
                                  offset + (i * FLASH_BLOCK_SIZE),
                                  (const uint32_t*)&data[i * FLASH_BLOCK_SIZE]),
           "translations_write write");
  }

  if (len % FLASH_BLOCK_SIZE) {
    flash_block_t block = {0};
    memset(block, 0xFF, FLASH_BLOCK_SIZE);
    memcpy(block, data + (len / FLASH_BLOCK_SIZE) * FLASH_BLOCK_SIZE,
           len % FLASH_BLOCK_SIZE);
    ensure(flash_area_write_block(
               &TRANSLATIONS_AREA,
               offset + (len / FLASH_BLOCK_SIZE) * FLASH_BLOCK_SIZE, block),
           "translations_write write rest");
  }
  ensure(flash_lock_write(), "translations_write lock");
  return true;
}

const uint8_t* translations_read(uint32_t* len, uint32_t offset) {
  // TODO: _Static_assert was not happy with TRANSLATIONS_AREA.num_subareas == 1
  // error: expression in static assertion is not constant
  assert(TRANSLATIONS_AREA.num_subareas == 1);
  *len = flash_area_get_size(&TRANSLATIONS_AREA) - offset;
  return flash_area_get_address(&TRANSLATIONS_AREA, offset, 0);
}

void translations_erase(void) {
  ensure(flash_area_erase(&TRANSLATIONS_AREA, NULL), "translations erase");
}

uint32_t translations_area_bytesize(void) {
  return flash_area_get_size(&TRANSLATIONS_AREA);
}
