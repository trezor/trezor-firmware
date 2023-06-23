
#ifndef CORE_BACKLIGHT_H
#define CORE_BACKLIGHT_H

#include "common.h"

int backlight_pwm_set(int val);

int backlight_pwm_get(void);

void backlight_pwm_init(void);

void backlight_pwm_reinit(void);

void backlight_pwm_set_slow(void);

#endif  // CORE_BACKLIGHT_H
