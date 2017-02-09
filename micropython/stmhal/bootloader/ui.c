#include "ui.h"
#include "display.h"

#define ui_WHITE 0xFFFF
#define ui_BLACK 0x0000

void screen_welcome(void)
{
    display_text(0, 240, "bootloader", 10, FONT_MONO, ui_WHITE, ui_BLACK);
}
