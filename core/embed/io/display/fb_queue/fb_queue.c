#ifdef KERNEL_MODE

#include <sys/irq.h>

#include "fb_queue.h"

int16_t fb_queue_get_for_copy(frame_buffer_queue_t *queue) {
  irq_key_t key = irq_lock();
  int16_t wix = queue->wix;
  if (queue->entry[wix] != FB_STATE_PREPARING) {
    // No refresh needed as the frame buffer is not in
    // the state to be copied to the display
    irq_unlock(key);
    return -1;
  }

  irq_unlock(key);
  return wix;
}

int16_t fb_queue_get_for_write(frame_buffer_queue_t *queue) {
  frame_buffer_state_t state;

  // We have to wait if the buffer was passed for copying
  // to the interrupt handler
  do {
    irq_key_t key = irq_lock();
    state = queue->entry[queue->wix];
    irq_unlock(key);

  } while (state == FB_STATE_READY || state == FB_STATE_COPYING);

  irq_key_t key = irq_lock();
  queue->entry[queue->wix] = FB_STATE_PREPARING;
  irq_unlock(key);

  return queue->wix;
}

int16_t fb_queue_get_for_transfer(frame_buffer_queue_t *queue) {
  irq_key_t key = irq_lock();

  if (queue->rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    irq_unlock(key);
    return -1;
  }

  switch (queue->entry[queue->rix]) {
    case FB_STATE_EMPTY:
    case FB_STATE_PREPARING:
      // No new frame queued

    case FB_STATE_COPYING:
      // Currently we are copying a data to the display.

      irq_unlock(key);
      return -1;
      break;

    case FB_STATE_READY:
      // Now it's proper time to copy the data to the display
      queue->entry[queue->rix] = FB_STATE_COPYING;
      irq_unlock(key);
      return queue->rix;

      // NOTE: when copying is done, this queue slot is marked empty
      break;

    default:
      // This is an invalid state, and we should never get here
      irq_unlock(key);
      return -1;
      break;
  }
}

bool fb_queue_set_done(frame_buffer_queue_t *queue) {
  irq_key_t key = irq_lock();
  if (queue->rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    irq_unlock(key);
    return false;
  }

  if (queue->entry[queue->rix] == FB_STATE_COPYING) {
    queue->entry[queue->rix] = FB_STATE_EMPTY;
    queue->rix = (queue->rix + 1) % FRAME_BUFFER_COUNT;
    irq_unlock(key);
    return true;
  }

  irq_unlock(key);
  return false;
}

bool fb_queue_set_switched(frame_buffer_queue_t *queue) {
  irq_key_t key = irq_lock();
  if (queue->rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    irq_unlock(key);
    return false;
  }

  if (queue->entry[queue->rix] == FB_STATE_COPYING) {
    if (queue->aix >= 0) {
      queue->entry[queue->aix] = FB_STATE_EMPTY;
    }
    queue->aix = queue->rix;
    queue->rix = (queue->rix + 1) % FRAME_BUFFER_COUNT;
    irq_unlock(key);
    return true;
  }

  irq_unlock(key);
  return false;
}

bool fb_queue_set_ready_for_transfer(frame_buffer_queue_t *queue) {
  irq_key_t key = irq_lock();
  if (queue->wix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    irq_unlock(key);
    return false;
  }

  if (queue->entry[queue->rix] == FB_STATE_PREPARING) {
    queue->entry[queue->rix] = FB_STATE_READY;
    queue->wix = (queue->wix + 1) % FRAME_BUFFER_COUNT;
    irq_unlock(key);
    return true;
  }

  irq_unlock(key);
  return false;
}

void fb_queue_reset(frame_buffer_queue_t *queue) {
  irq_key_t key = irq_lock();
  // Reset the buffer queue so we can eventually continue
  // safely in thread mode
  queue->wix = 0;
  queue->rix = 0;
  for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
    queue->entry[i] = FB_STATE_EMPTY;
  }
  irq_unlock(key);
}

bool fb_queue_is_processed(frame_buffer_queue_t *queue) {
  irq_key_t key = irq_lock();
  for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
    frame_buffer_state_t state = queue->entry[i];
    if (state == FB_STATE_READY ||
        (state == FB_STATE_COPYING && i != queue->aix)) {
      irq_unlock(key);
      return false;
    }
  }

  irq_unlock(key);
  return true;
}

#endif
