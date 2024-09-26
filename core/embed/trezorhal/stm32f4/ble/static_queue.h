
#ifndef STATIC_QUEUE_H
#define STATIC_QUEUE_H

#include "irq.h"

typedef enum {
  QUEUE_ENTRY_EMPTY = 0,
  QUEUE_ENTRY_ALLOCATED = 1,
  QUEUE_ENTRY_FULL = 2,
  QUEUE_ENTRY_PROCESSING = 3,
} queue_entry_state_t;

#define CREATE_QUEUE_TYPE(name, size, qlen)                                \
  typedef struct {                                                         \
    uint8_t buffer[size];                                                  \
    queue_entry_state_t state;                                             \
    uint16_t len;                                                          \
  } name##_entry_t;                                                        \
  typedef struct {                                                         \
    name##_entry_t entry[qlen];                                            \
    int rix;                                                               \
    int fix;                                                               \
    int pix;                                                               \
    int wix;                                                               \
    bool overrun;                                                          \
    uint16_t overrun_count;                                                \
  } name##_queue_t;                                                        \
                                                                           \
  void name##_queue_init(name##_queue_t *queue) {                          \
    irq_key_t key = irq_lock();                                            \
    memset(queue, 0, sizeof(*queue));                                      \
    irq_unlock(key);                                                       \
  }                                                                        \
                                                                           \
  uint8_t *name##_queue_allocate(name##_queue_t *queue) {                  \
    irq_key_t key = irq_lock();                                            \
                                                                           \
    if (queue->entry[queue->wix].state != QUEUE_ENTRY_EMPTY) {             \
      queue->overrun = true;                                               \
      queue->overrun_count++;                                              \
      irq_unlock(key);                                                     \
      return NULL;                                                         \
    }                                                                      \
                                                                           \
    queue->entry[queue->wix].state = QUEUE_ENTRY_ALLOCATED;                \
                                                                           \
    uint8_t *buffer = queue->entry[queue->wix].buffer;                     \
    queue->fix = queue->wix;                                               \
    queue->wix = (queue->wix + 1) % (qlen);                                \
                                                                           \
    irq_unlock(key);                                                       \
                                                                           \
    return buffer;                                                         \
  }                                                                        \
                                                                           \
  bool name##_queue_finalize(name##_queue_t *queue, const uint8_t *buffer, \
                             uint16_t len) {                               \
    irq_key_t key = irq_lock();                                            \
                                                                           \
    if (queue->entry[queue->fix].state != QUEUE_ENTRY_ALLOCATED) {         \
      irq_unlock(key);                                                     \
      return false;                                                        \
    }                                                                      \
    if (queue->entry[queue->fix].buffer != buffer) {                       \
      irq_unlock(key);                                                     \
      return false;                                                        \
    }                                                                      \
                                                                           \
    queue->entry[queue->fix].len = len;                                    \
    queue->entry[queue->fix].state = QUEUE_ENTRY_FULL;                     \
    queue->fix = (queue->fix + 1) % (qlen);                                \
    irq_unlock(key);                                                       \
    return true;                                                           \
  }                                                                        \
                                                                           \
  bool name##_queue_read(name##_queue_t *queue, uint8_t *data,             \
                         uint16_t max_len, uint16_t *len) {                \
    irq_key_t key = irq_lock();                                            \
    if (queue->entry[queue->rix].state != QUEUE_ENTRY_FULL) {              \
      irq_unlock(key);                                                     \
      return false;                                                        \
    }                                                                      \
                                                                           \
    if ((max_len) < (size)) {                                              \
      irq_unlock(key);                                                     \
      return false;                                                        \
    }                                                                      \
    *len = queue->entry[queue->rix].len;                                   \
    memcpy(data, queue->entry[queue->rix].buffer, (size));                 \
    queue->entry[queue->rix].state = QUEUE_ENTRY_EMPTY;                    \
    queue->rix = (queue->rix + 1) % (qlen);                                \
    irq_unlock(key);                                                       \
    return true;                                                           \
  }                                                                        \
  bool name##_queue_full(name##_queue_t *queue) {                          \
    irq_key_t key = irq_lock();                                            \
    bool full = queue->entry[queue->wix].state != QUEUE_ENTRY_EMPTY;       \
    irq_unlock(key);                                                       \
    return full;                                                           \
  }                                                                        \
  bool name##_queue_insert(name##_queue_t *queue, const uint8_t *data,     \
                           uint32_t len) {                                 \
    irq_key_t key = irq_lock();                                            \
    if (queue->entry[queue->wix].state != QUEUE_ENTRY_EMPTY) {             \
      irq_unlock(key);                                                     \
      return false;                                                        \
    }                                                                      \
                                                                           \
    if ((len) > (size)) {                                                  \
      irq_unlock(key);                                                     \
      return false;                                                        \
    }                                                                      \
                                                                           \
    memcpy(queue->entry[queue->wix].buffer, data, (size));                 \
    queue->entry[queue->wix].state = QUEUE_ENTRY_FULL;                     \
    queue->entry[queue->wix].len = len;                                    \
    queue->wix = (queue->wix + 1) % (qlen);                                \
    irq_unlock(key);                                                       \
    return true;                                                           \
  }                                                                        \
  bool name##_queue_empty(name##_queue_t *queue) {                         \
    irq_key_t key = irq_lock();                                            \
    bool empty = queue->entry[queue->rix].state == QUEUE_ENTRY_EMPTY;      \
    empty &= queue->entry[queue->pix].state != QUEUE_ENTRY_PROCESSING;     \
    irq_unlock(key);                                                       \
    return empty;                                                          \
  }                                                                        \
  uint8_t *name##_queue_process(name##_queue_t *queue, uint16_t *len) {    \
    irq_key_t key = irq_lock();                                            \
    if (queue->entry[queue->rix].state == QUEUE_ENTRY_FULL) {              \
      queue->entry[queue->rix].state = QUEUE_ENTRY_PROCESSING;             \
    } else {                                                               \
      irq_unlock(key);                                                     \
      return NULL;                                                         \
    }                                                                      \
    queue->pix = queue->rix;                                               \
    queue->rix = (queue->rix + 1) % (qlen);                                \
    *len = queue->entry[queue->pix].len;                                   \
    irq_unlock(key);                                                       \
    return queue->entry[queue->pix].buffer;                                \
  }                                                                        \
  void name##_queue_process_done(name##_queue_t *queue) {                  \
    irq_key_t key = irq_lock();                                            \
    queue->entry[queue->pix].state = QUEUE_ENTRY_EMPTY;                    \
    irq_unlock(key);                                                       \
  }

#endif
