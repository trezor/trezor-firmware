

#include <trezor_model.h>

#include <gfx/gfx_bitblt.h>
#include <io/display.h>
#include <io/usb.h>
#include <rtl/secbool.h>
#include <sec/entropy.h>
#include <sys/systick.h>
#include <util/flash.h>
#include <util/translations.h>
#include "storage.h"

#ifdef USE_HW_JPEG_DECODER
#include <gfx/jpegdec.h>
#endif

#ifdef USE_BLE
#include <io/ble.h>
#endif

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#include "bip39.h"
#include "rand.h"
#include "slip39.h"

#include "uzlib.h"

// force bindgen to include these constants
const uint32_t DISPLAY_RESX_ = DISPLAY_RESX;
const uint32_t DISPLAY_RESY_ = DISPLAY_RESY;
