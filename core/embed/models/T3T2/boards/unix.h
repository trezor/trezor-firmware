#pragma once

#define WINDOW_WIDTH 400
#define WINDOW_HEIGHT 600
#define TOUCH_OFFSET_X 80
#define TOUCH_OFFSET_Y 102

#define ORIENTATION_NSEW 1

#define BACKGROUND_FILE "T3T1/background_T3T1.h"
#define BACKGROUND_NAME background_T3T1_jpg

// Power-management tunables consumed by the power-manager policy (the emulator
// runs the device's policy core). No charger and no RTC on this model.
#define BATTERY_LOW_SOC_PERCENT 15
#define PM_POWER_SAVE_BACKLIGHT_LIMIT 130
