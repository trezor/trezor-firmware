#pragma once

// OTP device variant block layout
// byte 0: version (always 0x01)
#define UNIT_PROPERTIES_BYTE_COLOR 1
#define UNIT_PROPERTIES_BYTE_BTCONLY 2
#define UNIT_PROPERTIES_BYTE_PACKAGING 3
#define UNIT_PROPERTIES_BYTE_BATTERY_TYPE 4

// SD hotswap configuration
// T2T1: SD hotswap is disabled for units produced in 2018 or earlier
#define UNIT_PROPERTIES_SD_HOTSWAP_ENABLED true
#define UNIT_PROPERTIES_SD_HOTSWAP_EARLY_PRODUCTION_YEAR 18
