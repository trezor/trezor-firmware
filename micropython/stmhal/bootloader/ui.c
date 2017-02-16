#include "ui.h"
#include "display.h"

void screen_stage1(void)
{
    display_print("BL stage 1\n", -1);
}

void screen_stage2_jump(void)
{
    display_print("BL stage 2 jump\n", -1);
}

void screen_stage2_invalid(void)
{
    display_print("BL stage 2 invalid\n", -1);
}
