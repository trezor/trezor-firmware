
#ifndef __HAPTIC_H__
#define __HAPTIC_H__

typedef enum {
  HAPTIC_BUTTON_PRESS = 0,
  HAPTIC_ALERT = 1,
  HAPTIC_HOLD_TO_CONFIRM = 2,
} haptic_effect_t;

// Initialize haptic driver
void haptic_init(void);

// Calibrate haptic driver
void haptic_calibrate(void);

// Play haptic effect
void haptic_play(haptic_effect_t effect);

#endif
