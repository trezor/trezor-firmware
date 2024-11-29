#ifdef KERNEL_MODE
#include "fb_queue.h"

int16_t fb_queue_get_for_copy(volatile frame_buffer_queue_t *queue) {
  if (queue->entry[queue->wix] != FB_STATE_PREPARING) {
    // No refresh needed as the frame buffer is not in
    // the state to be copied to the display
    return -1;
  }

  return queue->wix;
}

int16_t fb_queue_get_for_write(volatile frame_buffer_queue_t *queue) {
  frame_buffer_state_t state;

  // We have to wait if the buffer was passed for copying
  // to the interrupt handler
  do {
    state = queue->entry[queue->wix];
  } while (state == FB_STATE_READY || state == FB_STATE_COPYING);

  queue->entry[queue->wix] = FB_STATE_PREPARING;

  return queue->wix;
}

int16_t fb_queue_get_for_transfer(volatile frame_buffer_queue_t *queue) {
  if (queue->rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    return -1;
  }

  switch (queue->entry[queue->rix]) {
    case FB_STATE_EMPTY:
    case FB_STATE_PREPARING:
      // No new frame queued

    case FB_STATE_COPYING:
      // Currently we are copying a data to the display.
      return -1;
      break;

    case FB_STATE_READY:
      // Now it's proper time to copy the data to the display
      queue->entry[queue->rix] = FB_STATE_COPYING;
      return queue->rix;

      // NOTE: when copying is done, this queue slot is marked empty
      break;

    default:
      // This is an invalid state, and we should never get here
      return -1;
      break;
  }
}

bool fb_queue_set_done(volatile frame_buffer_queue_t *queue) {
  if (queue->rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    return false;
  }

  if (queue->entry[queue->rix] == FB_STATE_COPYING) {
    queue->entry[queue->rix] = FB_STATE_EMPTY;
    queue->rix = (queue->rix + 1) % FRAME_BUFFER_COUNT;
    return true;
  }

  return false;
}

bool fb_queue_set_switched(volatile frame_buffer_queue_t *queue) {
  if (queue->rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    return false;
  }

  if (queue->entry[queue->rix] == FB_STATE_COPYING) {
    if (queue->aix >= 0) {
      queue->entry[queue->aix] = FB_STATE_EMPTY;
    }
    queue->aix = queue->rix;
    queue->rix = (queue->rix + 1) % FRAME_BUFFER_COUNT;
    return true;
  }

  return false;
}

bool fb_queue_set_ready_for_transfer(volatile frame_buffer_queue_t *queue) {
  if (queue->wix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state, and we should never get here
    return false;
  }

  if (queue->entry[queue->rix] == FB_STATE_PREPARING) {
    queue->entry[queue->rix] = FB_STATE_READY;
    queue->wix = (queue->wix + 1) % FRAME_BUFFER_COUNT;
    return true;
  }

  return false;
}

void fb_queue_reset(volatile frame_buffer_queue_t *queue) {
  // Reset the buffer queue so we can eventually continue
  // safely in thread mode
  queue->wix = 0;
  queue->rix = 0;
  for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
    queue->entry[i] = FB_STATE_EMPTY;
  }
}

bool fb_queue_is_processed(volatile frame_buffer_queue_t *queue) {
  for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
    frame_buffer_state_t state = queue->entry[i];
    if (state == FB_STATE_READY ||
        (state == FB_STATE_COPYING && i != queue->aix)) {
      return false;
    }
  }

  return true;
}

#endif
