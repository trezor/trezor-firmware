#pragma once

#include "model_version.h"

#define VERSION_MAJOR 2
#define VERSION_MINOR 1
// TEMPORARY TEST BUMP -- DO NOT COMMIT. 18 -> 19 so the new boot header no
// longer matches the installed bootloader code, forcing phase 1 down the
// full-bootloader path (served["code"] > 0) instead of header-only.
#define VERSION_PATCH 20
#define VERSION_BUILD 0
#define VERSION_UINT32                                            \
  (VERSION_MAJOR | (VERSION_MINOR << 8) | (VERSION_PATCH << 16) | \
   (VERSION_BUILD << 24))

#define FIX_VERSION_MAJOR 2
#define FIX_VERSION_MINOR 0
#define FIX_VERSION_PATCH 0
#define FIX_VERSION_BUILD 0
