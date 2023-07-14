#include "common.h"

#define SHARED_DATA_SIZE 16

typedef enum {
  SHARED_DATA_SYS_TICK = 0,
  SHARED_DATA_USB_HANDLE = 1,
  SHARED_DATA_RDI_DATA = 2,
} shared_data_idx_t;

extern uint32_t shared_data[SHARED_DATA_SIZE];
void shared_data_init(void);
void shared_data_deinit(void);
void shared_data_register(shared_data_idx_t idx, uint32_t value);
