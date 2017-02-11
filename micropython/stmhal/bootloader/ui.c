#include "ui.h"
#include "display.h"

void screen_stage1(void)
{
    display_clear();
    display_text(0, 240, "BL stage 1", -1, FONT_MONO, ui_WHITE, ui_BLACK);
}

void screen_stage2_jump(void)
{
    display_clear();
    display_text(0, 240, "BL stage 2 jump", -1, FONT_MONO, ui_WHITE, ui_BLACK);
}

void screen_stage2_invalid(void)
{
    display_clear();
    display_text(0, 240, "BL stage 2 invalid", -1, FONT_MONO, ui_WHITE, ui_BLACK);
}
