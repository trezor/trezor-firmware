#include "shared_data.h"
#include "common.h"
#include "memzero.h"

uint32_t shared_data[SHARED_DATA_SIZE]
    __attribute__((section(".shared_data"))) = {0};

extern __IO uint32_t uwTick;

void shared_data_init(void) {
  memzero(shared_data, sizeof(shared_data));
  shared_data[SHARED_DATA_SYS_TICK] = (uint32_t)&uwTick;
}

void shared_data_deinit(void) { memzero(shared_data, sizeof(shared_data)); }

void shared_data_register(shared_data_idx_t idx, uint32_t value) {
  shared_data[idx] = value;
}
