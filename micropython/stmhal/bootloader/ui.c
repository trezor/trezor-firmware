#include "ui.h"

#include "display.h"

#include "toi_trezor.h"

#define ui_WHITE 0xFFFF
#define ui_BLACK 0x0000
#define ui_BLUE  0x24BE

void screen_welcome(void)
{
    display_icon(0, 0, 240, 240, toi_trezor, sizeof(toi_trezor), ui_WHITE, ui_BLACK);
    display_text(0, 240, "bootloader", 10, FONT_MONO, ui_WHITE, ui_BLACK);
}

void screen_info(void)
{
}

void screen_upload_request(void)
{
}


void screen_upload_progress(int permil)
{
    char label[5] = "100%";
    char *plabel = label;
    // TODO: convert permil -> plabel
    display_text_center(120, 192 + 32, "Uploading firmware", -1, FONT_NORMAL, ui_WHITE, ui_BLACK);
    display_loader(permil, 0, ui_BLUE, ui_BLACK, 0, 0, 0);
    display_text_center(120, 192 / 2 + 14 / 2, plabel, -1, FONT_BOLD, ui_WHITE, ui_BLACK);
    display_refresh();
}

void screen_upload_success(void)
{
}

void screen_upload_abort(void)
{
}
