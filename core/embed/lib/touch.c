
#ifdef USE_TOUCH
#include "touch.h"

uint32_t touch_click(void) {
  uint32_t r = 0;
  // flush touch events if any
  while (touch_read()) {
  }
  // wait for TOUCH_START
  while ((touch_read() & TOUCH_START) == 0) {
  }
  // wait for TOUCH_END
  while (((r = touch_read()) & TOUCH_END) == 0) {
  }
  // flush touch events if any
  while (touch_read()) {
  }
  // return last touch coordinate
  return r;
}
#endif
