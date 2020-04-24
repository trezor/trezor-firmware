#include "trans_fifo.h"

#include "./segger_rtt/rtt_log.h"

#define min(a, b) ((a) < (b) ? (a) : (b))

void fifo_init(trans_fifo *p_fifo, uint8_t *buf, uint32_t buf_size) {
  p_fifo->p_buf = buf;
  p_fifo->buf_size = buf_size;
  p_fifo->over_pre = false;
  p_fifo->read_pos = p_fifo->write_pos = p_fifo->lock_pos = 0;
}

uint32_t fifo_data_len(trans_fifo *p_fifo) {
  uint32_t len;
  if (p_fifo->read_pos > p_fifo->write_pos) {
    len = p_fifo->buf_size - p_fifo->read_pos + p_fifo->write_pos;
  } else {
    len = p_fifo->write_pos - p_fifo->read_pos;
  }
  return len;
}
uint32_t fifo_lockdata_len(trans_fifo *p_fifo) {
  uint32_t len = 0;
  if (p_fifo->over_pre && (p_fifo->read_pos == p_fifo->lock_pos)) {
    len = p_fifo->buf_size;
  } else if (p_fifo->read_pos > p_fifo->lock_pos) {
    len = p_fifo->buf_size - p_fifo->read_pos + p_fifo->lock_pos;
  } else {
    len = p_fifo->lock_pos - p_fifo->read_pos;
  }
  return len;
}

void fifo_lockpos_set(trans_fifo *p_fifo) {
  p_fifo->lock_pos = p_fifo->write_pos;
}

void fifo_lockpos_set_align(trans_fifo *p_fifo, uint32_t align) {
  uint32_t len;
  len = fifo_data_len(p_fifo);
  if (len / align) len -= (len % align);
  p_fifo->lock_pos = (p_fifo->lock_pos + len) % p_fifo->buf_size;
}

bool fifo_put_no_overflow(trans_fifo *p_fifo, uint8_t onebyte) {
  if (p_fifo->over_pre) {
    return false;
  }
  if ((p_fifo->write_pos + 1) % p_fifo->buf_size == p_fifo->read_pos) {
    p_fifo->over_pre = true;
  }
  p_fifo->p_buf[p_fifo->write_pos] = onebyte;
  p_fifo->write_pos = (p_fifo->write_pos + 1) % p_fifo->buf_size;
  return true;
}

void fifo_put_overflow(trans_fifo *p_fifo, uint8_t onebyte) {
  if ((p_fifo->write_pos + 1) % p_fifo->buf_size == p_fifo->read_pos) {
    p_fifo->over_pre = true;
  }
  p_fifo->p_buf[p_fifo->write_pos] = onebyte;
  p_fifo->write_pos = (p_fifo->write_pos + 1) % p_fifo->buf_size;
}

uint32_t fifo_read_lock(trans_fifo *p_fifo, uint8_t *buf,
                        uint32_t request_len) {
  uint32_t len, len1;
  uint32_t avaliable_len = fifo_lockdata_len(p_fifo);
  if (request_len == 0) return 0;
  if (p_fifo->over_pre) p_fifo->over_pre = false;
  len = min(request_len, avaliable_len);
  if ((p_fifo->read_pos + len) > p_fifo->buf_size) {
    len1 = p_fifo->buf_size - p_fifo->read_pos;
    memcpy(buf, p_fifo->p_buf + p_fifo->read_pos, len1);
    memcpy(buf + len1, p_fifo->p_buf, len - len1);
  } else {
    memcpy(buf, p_fifo->p_buf + p_fifo->read_pos, len);
  }
  p_fifo->read_pos = (p_fifo->read_pos + len) % p_fifo->buf_size;
  return len;
}

// read data but don't update len
uint32_t fifo_read_peek(trans_fifo *p_fifo, uint8_t *buf,
                        uint32_t request_len) {
  uint32_t len, len1;
  uint32_t avaliable_len = fifo_lockdata_len(p_fifo);
  if (request_len == 0) return 0;
  if (p_fifo->over_pre) p_fifo->over_pre = false;
  len = min(request_len, avaliable_len);
  if ((p_fifo->read_pos + len) > p_fifo->buf_size) {
    len1 = p_fifo->buf_size - p_fifo->read_pos;
    memcpy(buf, p_fifo->p_buf + p_fifo->read_pos, len1);
    memcpy(buf + len1, p_fifo->p_buf, len - len1);
  } else {
    memcpy(buf, p_fifo->p_buf + p_fifo->read_pos, len);
  }
  return len;
}

void fifo_flush(trans_fifo *p_fifo) {
  p_fifo->write_pos = p_fifo->lock_pos = p_fifo->read_pos = 0;
  p_fifo->over_pre = false;
}

bool fifo_write_no_overflow(trans_fifo *p_fifo, uint8_t *buf,
                            uint32_t buf_size) {
  uint32_t i;
  for (i = 0; i < buf_size; i++) {
    while (buf_size--) {
      if (!fifo_put_no_overflow(p_fifo, buf[i])) return false;
    }
  }
  fifo_lockpos_set(p_fifo);
  return true;
}
