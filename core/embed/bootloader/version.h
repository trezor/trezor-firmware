#define VERSION_MAJOR 2
#define VERSION_MINOR 1
#define VERSION_PATCH 8
#define VERSION_BUILD 0
#define VERSION_UINT32                                            \
  (VERSION_MAJOR | (VERSION_MINOR << 8) | (VERSION_PATCH << 16) | \
   (VERSION_BUILD << 24))

#define FIX_VERSION_MAJOR 2
#define FIX_VERSION_MINOR 0
#define FIX_VERSION_PATCH 0
#define FIX_VERSION_BUILD 0

#ifdef TREZOR_MODEL_R
#define VERSION_MONOTONIC 2
#else
#define VERSION_MONOTONIC 1
#endif
