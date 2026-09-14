#pragma once

#include "model_version.h"

#define VERSION_MAJOR 2
#define VERSION_MINOR 1
#define VERSION_PATCH 18
#define VERSION_BUILD 0
#define VERSION_UINT32                                            \
  (VERSION_MAJOR | (VERSION_MINOR << 8) | (VERSION_PATCH << 16) | \
   (VERSION_BUILD << 24))

#define FIX_VERSION_MAJOR 2
#define FIX_VERSION_MINOR 0
#define FIX_VERSION_PATCH 0
#define FIX_VERSION_BUILD 0

// Minimum bootloader version a device must ALREADY be running for this one to
// install over it. 0.0.0.0 means no floor.
#define MIN_PREV_VERSION_MAJOR 0
#define MIN_PREV_VERSION_MINOR 0
#define MIN_PREV_VERSION_PATCH 0
#define MIN_PREV_VERSION_BUILD 0
