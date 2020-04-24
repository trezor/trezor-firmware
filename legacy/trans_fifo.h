#ifndef __TRANS_FIFO_H__
#define __TRANS_FIFO_H__

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

typedef struct _trans_fifo {
  uint8_t *p_buf;    /**< Pointer to FIFO buffer memory.                      */
  uint32_t buf_size; /**< Read/write index mask. Also used for size checking. */
  bool over_pre;
  volatile uint32_t read_pos;  /**< Next read position in the FIFO buffer.  */
  volatile uint32_t write_pos; /**< Next write position in the FIFO buffer. */
  volatile uint32_t lock_pos;  /**< One packet received,remember the position */
} trans_fifo;

void fifo_init(trans_fifo *p_fifo, uint8_t *buf, uint32_t buf_size);
uint32_t fifo_data_len(trans_fifo *p_fifo);
uint32_t fifo_lockdata_len(trans_fifo *p_fifo);
void fifo_lockpos_set(trans_fifo *p_fifo);
void fifo_lockpos_set_align(trans_fifo *p_fifo, uint32_t align);
bool fifo_put_no_overflow(trans_fifo *p_fifo, uint8_t onebyte);
void fifo_put_overflow(trans_fifo *p_fifo, uint8_t onebyte);
uint32_t fifo_read_lock(trans_fifo *p_fifo, uint8_t *buf, uint32_t request_len);
uint32_t fifo_read_peek(trans_fifo *p_fifo, uint8_t *buf, uint32_t request_len);
void fifo_flush(trans_fifo *p_fifo);
bool fifo_write_no_overflow(trans_fifo *p_fifo, uint8_t *buf,
                            uint32_t buf_size);

#endif
