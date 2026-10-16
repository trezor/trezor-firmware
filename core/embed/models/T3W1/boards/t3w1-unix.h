#ifndef BOARDS_T3W1_UNIX_H
#define BOARDS_T3W1_UNIX_H

#define WINDOW_WIDTH 600
#define WINDOW_HEIGHT 800
#define TOUCH_OFFSET_X 107
#define TOUCH_OFFSET_Y 53

#define BTN_POWER_KEY SDLK_P

#define ORIENTATION_NS 1

#define LED_OFFSET_Y -8

#define FOREGROUND_FILE "T3W1/foreground_T3W1.h"
#define FOREGROUND_NAME foreground_T3W1_png

// Power-management tunables consumed by the power-manager policy; the
// emulator runs the same policy core as the device over an emulated PMIC, so
// it needs the same board figures. Values match the hardware revisions.
#define BATTERY_CHARGING_CURRENT_MAX_MA 180
#define BATTERY_CHARGE_TEMP_BANDS \
  {{39.0f, 1.0f}, {43.0f, 0.7f}, {45.0f, 0.5f}, {47.0f, 0.3f}}
#define BATTERY_LOW_SOC_PERCENT 15
#define PM_SUSPEND_CURRENT_MA 0.032f
#define PM_HIBERNATION_CURRENT_MA 0.004f
#define PM_POWER_SAVE_BACKLIGHT_LIMIT 130

#endif  // BOARDS_T3W1_UNIX_H
