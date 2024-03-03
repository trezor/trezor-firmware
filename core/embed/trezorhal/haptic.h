
#ifndef TREZORHAL_HAPTIC_H
#define TREZORHAL_HAPTIC_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
  HAPTIC_BUTTON_PRESS = 0,
  HAPTIC_ALERT = 1,
  HAPTIC_HOLD_TO_CONFIRM = 2,
} haptic_effect_t;

// Initialize haptic driver
void haptic_init(void);

// Calibrate haptic driver
void haptic_calibrate(void);

// Test haptic driver, plays a maximum amplitude for the given duration
bool haptic_test(uint16_t duration_ms);

// Play haptic effect
void haptic_play(haptic_effect_t effect);

#endif
