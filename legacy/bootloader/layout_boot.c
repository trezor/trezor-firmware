#include "layout_boot.h"

void layoutBootHome(void) {
  uint8_t *ble_name;
  if (layoutNeedRefresh()) {
    oledClear();
    oledDrawBitmap(35, 15, &bmp_BiXin_logo32);
    oledDrawStringCenter(90, 20, "BiXin", FONT_STANDARD);
    oledDrawStringCenter(90, 30, "Bootloader", FONT_STANDARD);
    oledDrawStringCenter(90, 40,
                         VERSTR(VERSION_MAJOR) "." VERSTR(
                             VERSION_MINOR) "." VERSTR(VERSION_PATCH),
                         FONT_STANDARD);
    if (ble_name_state() == true) {
      ble_name = ble_get_name();
      oledDrawStringCenter(64, 50, (char *)ble_name, FONT_STANDARD);
    } else {
      //   ble_request_name();
    }
    oledRefresh();
  }
}
