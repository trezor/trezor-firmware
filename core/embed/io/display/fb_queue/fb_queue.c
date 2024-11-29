#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include <sys/irq.h>

#include "fb_queue.h"

// Initializes the queue and make it empty
// Clear peeked flag
void fb_queue_reset(fb_queue_t* queue) {
  memset(queue, 0, sizeof(fb_queue_t));
  for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
    queue->entries[i].index = -1;
  }
}

// Inserts a new element to the tail of the queue
bool fb_queue_put(fb_queue_t* queue, int16_t index) {
  irq_key_t irq_key = irq_lock();

  // check if the queue is full
  if (queue->entries[queue->wix].index != -1) {
    irq_unlock(irq_key);
    return false;
  }

  queue->entries[queue->wix].index = index;
  queue->wix = (queue->wix + 1) % FRAME_BUFFER_COUNT;

  irq_unlock(irq_key);

  return true;
}

// Removes an element from the queue head, returns -1 if the queue is empty
// Clear peeked flag
int16_t fb_queue_take(fb_queue_t* queue) {
  irq_key_t irq_key = irq_lock();

  if (queue->entries[queue->rix].index == -1) {
    irq_unlock(irq_key);
    return -1;
  }

  queue->peaked = false;
  int16_t index = queue->entries[queue->rix].index;
  queue->entries[queue->rix].index = -1;
  queue->rix = (queue->rix + 1) % FRAME_BUFFER_COUNT;

  irq_unlock(irq_key);
  return index;
}
// Returns true if the queue is empty
bool fb_queue_empty(fb_queue_t* queue) {
  irq_key_t irq_key = irq_lock();

  if (queue->entries[queue->rix].index == -1) {
    irq_unlock(irq_key);
    return true;
  }

  irq_unlock(irq_key);
  return false;
}

// Waits until the queue is not empty
void fb_queue_wait(fb_queue_t* queue) {
  while (fb_queue_empty(queue))
    ;
}

// Returns the head of the queue (or -1 if the queue is empty)
// Set peeked flag if the queue is not empty
int16_t fb_queue_peek(fb_queue_t* queue) {
  irq_key_t irq_key = irq_lock();

  if (queue->entries[queue->rix].index == -1) {
    irq_unlock(irq_key);
    return -1;
  }

  int16_t index = queue->entries[queue->rix].index;
  queue->peaked = true;

  irq_unlock(irq_key);

  return index;
}

// Return if the head was already peeked
bool fb_queue_peeked(fb_queue_t* queue) {
  irq_key_t key = irq_lock();
  bool peeked = queue->peaked;
  irq_unlock(key);
  return peeked;
}

#endif
