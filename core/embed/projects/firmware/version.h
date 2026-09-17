#pragma once

#include "model_version.h"

#define VERSION_MAJOR 2
#define VERSION_MINOR 13
#define VERSION_PATCH 0
#define VERSION_BUILD 0

#define FIX_VERSION_MAJOR 2
#define FIX_VERSION_MINOR 10
#define FIX_VERSION_PATCH 0
#define FIX_VERSION_BUILD 0

// Minimum installed release a pq_secure_boot release may be installed over;
// 0.0.0.0 = no floor. Read by the release signer (boot header
// min_prev_version), not compiled into the firmware.
#define MIN_PREV_VERSION_MAJOR 0
#define MIN_PREV_VERSION_MINOR 0
#define MIN_PREV_VERSION_PATCH 0
#define MIN_PREV_VERSION_BUILD 0
