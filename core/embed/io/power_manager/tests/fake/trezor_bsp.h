// Stand-in for the board header on the host: only the power-manager tunables
// the charger leaf reads. Values match the T3W1 revC board header.
#pragma once

#define BATTERY_CHARGING_CURRENT_MAX_MA 180
#define BATTERY_CHARGE_TEMP_BANDS \
  {{39.0f, 1.0f}, {43.0f, 0.7f}, {45.0f, 0.5f}, {47.0f, 0.3f}}
