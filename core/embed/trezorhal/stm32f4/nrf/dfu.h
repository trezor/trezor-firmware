
#ifndef __DFU_H__
#define __DFU_H__

#include <trezor_types.h>

typedef enum {
  DFU_NEXT_CHUNK,
  DFU_SUCCESS,
  DFU_FAIL,
} dfu_result_t;

void dfu_init(void);
dfu_result_t dfu_update_init(uint8_t *data, uint32_t len, uint32_t binary_len);
dfu_result_t dfu_update_chunk(uint8_t *data, uint32_t len);
dfu_result_t dfu_update_do(uint8_t *datfile, uint32_t datfile_len,
                           uint8_t *binfile, uint32_t binfile_len);

#endif
