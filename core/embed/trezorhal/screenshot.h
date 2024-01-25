
#include <stdbool.h>
#include <stdint.h>

void screenshot_init(void);

bool screenshot(void);

void screenshot_clear(void);

void screenshot_prepare(uint32_t refresh_index, const char *target_directory);
