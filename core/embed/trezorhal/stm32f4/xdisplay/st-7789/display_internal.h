#ifndef TREZORHAL_DISPLAY_INTERNAL_H
#define TREZORHAL_DISPLAY_INTERNAL_H

#include <trezor_bsp.h>
#include <trezor_types.h>

#ifdef FRAMEBUFFER

// Number of frame buffers used (1 or 2)
// If 1 buffer is selected, some animations may not
// be so smooth but the memory usage is lower.
#define FRAME_BUFFER_COUNT 2

// Each frame buffer can be in one of the following states:
typedef enum {
  // The frame buffer is empty and can be written to
  FB_STATE_EMPTY = 0,
  // The frame buffer pass passed to application
  FB_STATE_PREPARING = 1,
  // The frame buffer was written to and is ready
  // to be copied to the display
  FB_STATE_READY = 2,
  // The frame buffer is currently being copied to
  // the display
  FB_STATE_COPYING = 3,

} frame_buffer_state_t;

typedef struct {
  // Queue entries
  volatile frame_buffer_state_t entry[FRAME_BUFFER_COUNT];
  // Read index
  // (accessed & updated in the context of the interrupt handlers
  uint8_t rix;
  // Write index
  // (accessed & updated in context of the main thread)
  uint8_t wix;

} frame_buffer_queue_t;

#endif  // FRAMEBUFFER

// Display driver state
typedef struct {
  // Set if the driver is initialized
  bool initialized;

#ifdef FRAMEBUFFER
  // Framebuffer queue
  // (accessed & updated in the context of the main thread
  // and the interrupt context)
  volatile frame_buffer_queue_t queue;
#endif

  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;

} display_driver_t;

// Display driver instance
extern display_driver_t g_display_driver;

static inline uint32_t is_mode_exception(void) {
  uint32_t isr_number = __get_IPSR() & IPSR_ISR_Msk;
  // Check if the ISR number is not 0 (thread mode) or 11 (SVCall)
  return (isr_number != 0) && (isr_number != 11);
}

#endif  // TREZORHAL_DISPLAY_INTERNAL_H
