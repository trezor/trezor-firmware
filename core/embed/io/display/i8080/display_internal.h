#ifndef TREZORHAL_DISPLAY_INTERNAL_H
#define TREZORHAL_DISPLAY_INTERNAL_H

#include <trezor_bsp.h>
#include <trezor_types.h>

#include "display_io.h"
#include "display_panel.h"

#ifdef FRAMEBUFFER

#include "../fb_queue/fb_queue.h"

#endif  // FRAMEBUFFER

#define GAMMA_EXP_DEFAULT 1.0f

#ifndef GAMMA_EXP
#define GAMMA_EXP GAMMA_EXP_DEFAULT
#endif

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

  // Byte order of pixel data expected by the panel
  display_pixel_endian_t pixel_endian;

} display_driver_t;

// Display driver instance
extern display_driver_t g_display_driver;

// Writes one RGB565 pixel in the given byte order. The byte order only
// matters on the 8-bit bus; on the 16-bit bus the pixel is written in a
// single bus cycle.
#ifdef DISPLAY_I8080_16BIT_DW
#define ISSUE_PIXEL_DATA(E, X) ((void)(E), ISSUE_DATA_BYTE(X))
#elif defined(DISPLAY_I8080_8BIT_DW)
#define ISSUE_PIXEL_DATA(E, X)             \
  do {                                     \
    uint16_t _px = (X);                    \
    if ((E) == DISPLAY_PIXEL_BIG_ENDIAN) { \
      ISSUE_DATA_BYTE(_px >> 8);           \
      ISSUE_DATA_BYTE(_px & 0xFF);         \
    } else {                               \
      ISSUE_DATA_BYTE(_px & 0xFF);         \
      ISSUE_DATA_BYTE(_px >> 8);           \
    }                                      \
  } while (0)
#endif  // DISPLAY_I8080_16BIT_DW

static inline uint32_t is_mode_exception(void) {
  uint32_t isr_number = __get_IPSR() & IPSR_ISR_Msk;
  // Check if the ISR number is not 0 (thread mode) or 11 (SVCall)
  return (isr_number != 0) && (isr_number != 11);
}

void display_ensure_refreshed(void);

#endif  // TREZORHAL_DISPLAY_INTERNAL_H
