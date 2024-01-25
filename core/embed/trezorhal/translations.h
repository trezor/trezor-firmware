#include <stdbool.h>
#include <stdint.h>

bool translations_write(const uint8_t* data, uint32_t offset, uint32_t len);

const uint8_t* translations_read(uint32_t* len, uint32_t offset);

void translations_erase(void);

uint32_t translations_area_bytesize(void);
