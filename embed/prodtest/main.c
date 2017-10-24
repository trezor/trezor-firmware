#include <string.h>
#include <sys/types.h>

#include "common.h"
#include "display.h"
#include "flash.h"
#include "rng.h"
#include "sdcard.h"
#include "touch.h"
#include "usb.h"

int main(void)
{
    display_orientation(0);
    sdcard_init();
    touch_init();

    display_text_center(120, 215, "prodtest", -1, FONT_BOLD, COLOR_GRAY128, COLOR_BLACK);

    for (;;) {

    }

    return 0;
}
