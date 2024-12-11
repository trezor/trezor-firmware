#ifndef TREZORHAL_DISPLAY_INTERNAL_H
#define TREZORHAL_DISPLAY_INTERNAL_H

#include <trezor_bsp.h>
#include <trezor_types.h>

#ifdef FRAMEBUFFER

#include "../fb_queue/fb_queue.h"

#endif  // FRAMEBUFFER

// Display driver state
typedef struct {
  // Set if the driver is initialized
  bool initialized;

#ifdef FRAMEBUFFER
  // Framebuffer queue
  // (accessed & updated in the context of the main thread
  // and the interrupt context)
  fb_queue_t empty_frames;
  fb_queue_t ready_frames;
#endif

  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
  int update_pending;

} display_driver_t;

// Display driver instance
extern display_driver_t g_display_driver;

static inline uint32_t is_mode_exception(void) {
  uint32_t isr_number = __get_IPSR() & IPSR_ISR_Msk;
  // Check if the ISR number is not 0 (thread mode) or 11 (SVCall)
  return (isr_number != 0) && (isr_number != 11);
}

#endif  // TREZORHAL_DISPLAY_INTERNAL_H
