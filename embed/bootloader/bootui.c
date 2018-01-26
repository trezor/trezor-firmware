#include <string.h>

#include "display.h"
#include "mini_printf.h"

#include "bootui.h"
#include "touch.h"
#include "version.h"

#include "icon_cancel.h"
#include "icon_confirm.h"
#include "icon_info.h"
#include "icon_done.h"
#include "icon_fail.h"
#include "icon_install.h"
#include "icon_wipe.h"

#include "icon_logo.h"
#include "icon_safeplace.h"
#include "icon_welcome.h"

#define BACKLIGHT_NORMAL 150

#define COLOR_BL_FAIL     RGB16(0xFF, 0x00, 0x00)  // red
#define COLOR_BL_DONE     RGB16(0x00, 0xAE, 0x0B)  // green
#define COLOR_BL_PROCESS  RGB16(0x4A, 0x90, 0xE2)  // blue
#define COLOR_BL_GRAY     RGB16(0x99, 0x99, 0x99)  // gray

// common shared functions

static void ui_confirm_cancel_buttons(void)
{
    display_bar_radius(9, 184, 108, 50, COLOR_BL_FAIL, COLOR_WHITE, 4);
    display_icon(9 + (108 - 16) / 2, 184 + (50 - 16) / 2, 16, 16, toi_icon_cancel + 12, sizeof(toi_icon_cancel) - 12, COLOR_WHITE, COLOR_BL_FAIL);
    display_bar_radius(123, 184, 108, 50, COLOR_BL_DONE, COLOR_WHITE, 4);
    display_icon(123 + (108 - 19) / 2, 184 + (50 - 16) / 2, 20, 16, toi_icon_confirm + 12, sizeof(toi_icon_confirm) - 12, COLOR_WHITE, COLOR_BL_DONE);
}

static const char *format_ver(const char *format, uint32_t version)
{
    static char ver_str[64];
    mini_snprintf(ver_str, sizeof(ver_str), format,
        (int)(version & 0xFF),
        (int)((version >> 8) & 0xFF),
        (int)((version >> 16) & 0xFF),
        (int)((version >> 24) & 0xFF)
    );
    return ver_str;
}

// boot UI

void ui_screen_boot(const vendor_header *vhdr, const image_header *hdr)
{
    const uint8_t *vimg = vhdr->vimg;
    const char *vstr = ((vhdr->vtrust & VTRUST_STRING) == 0) ? vhdr->vstr : 0;
    const uint32_t vstr_len = ((vhdr->vtrust & VTRUST_STRING) == 0) ? vhdr->vstr_len : 0;
    const uint32_t fw_version = hdr->version;
    const uint16_t background = ((vhdr->vtrust & VTRUST_RED) == 0) ? RGB16(0xFF, 0x00, 0x00) : COLOR_BLACK;

    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, background);
    // check whether vendor image is 120x120
    if (memcmp(vimg, "TOIf\x78\x00\x78\x00", 4) != 0) {
        return;
    }
    uint32_t datalen = *(uint32_t *)(vimg + 8);
    display_image((DISPLAY_RESX - 120) / 2, 32, 120, 120, vimg + 12, datalen);
    if (vstr && vstr_len) {
        display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 48, vstr, vstr_len, FONT_NORMAL, COLOR_WHITE, background, 0);
    }
    const char *ver_str = format_ver("%d.%d.%d.%d", fw_version);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 25, ver_str, -1, FONT_NORMAL, COLOR_BL_GRAY, background, 0);
}

void ui_screen_boot_wait(int wait_seconds)
{
    char wait_str[16];
    mini_snprintf(wait_str, sizeof(wait_str), "waiting for %ds", wait_seconds);
    display_bar(0, DISPLAY_RESY - 2 - 18, DISPLAY_RESX, 2 + 18, COLOR_BLACK);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 2, wait_str, -1, FONT_NORMAL, COLOR_BL_GRAY, COLOR_BLACK, 0);
}

void ui_screen_boot_click(void) {
    display_bar(0, DISPLAY_RESY - 2 - 18, DISPLAY_RESX, 2 + 18, COLOR_BLACK);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 2, "click to continue ...", -1, FONT_NORMAL, COLOR_BL_GRAY, COLOR_BLACK, 0);
}

// welcome UI

void ui_screen_first(void)
{
    display_icon(0, 0, 240, 240, toi_icon_logo + 12, sizeof(toi_icon_logo) - 12, COLOR_BLACK, COLOR_WHITE);
}

void ui_screen_second(void)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_icon((DISPLAY_RESX - 200) / 2, (DISPLAY_RESY - 60) / 2, 200, 60, toi_icon_safeplace + 12, sizeof(toi_icon_safeplace) - 12, COLOR_BLACK, COLOR_WHITE);
}

void ui_screen_third(void)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_icon((DISPLAY_RESX - 180) / 2, (DISPLAY_RESY - 30) / 2, 180, 30, toi_icon_welcome + 12, sizeof(toi_icon_welcome) - 12, COLOR_BLACK, COLOR_WHITE);
    display_text_center(120, 220, "Open trezor.io/start", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
}

// info UI

void ui_screen_info(secbool buttons, const vendor_header * const vhdr, const image_header * const hdr)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    const char *ver_str = format_ver("Bootloader %d.%d.%d.%d", VERSION_UINT32);
    display_text(16, 32, ver_str, -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BLACK);
    display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12, COLOR_BL_GRAY, COLOR_WHITE);
    if (vhdr && hdr) {
        ver_str = format_ver("Firmware %d.%d.%d.%d", (hdr->version));
        display_text(55, 70, ver_str, -1, FONT_NORMAL, COLOR_BL_GRAY, COLOR_WHITE, 0);
        display_text(55, 95, "by", -1, FONT_NORMAL, COLOR_BL_GRAY, COLOR_WHITE, 0);
        display_text(55, 120, vhdr->vstr, vhdr->vstr_len, FONT_NORMAL, COLOR_BL_GRAY, COLOR_WHITE, 0);
    } else {
        display_text(55, 70, "No Firmware", -1, FONT_NORMAL, COLOR_BL_GRAY, COLOR_WHITE, 0);
    }

    if (sectrue == buttons) {
        display_text_center(120, 170, "Connect to host?", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
        ui_confirm_cancel_buttons();
    } else {
        display_text_center(120, 220, "Open trezor.io/start", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    }
}

void ui_screen_info_fingerprint(const image_header * const hdr)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_text(16, 32, "Firmware fingerprint", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BLACK);

    static const char *hexdigits = "0123456789abcdef";
    char fingerprint_str[64];
    for (int i = 0; i < 32; i++) {
        fingerprint_str[i * 2    ] = hexdigits[(hdr->fingerprint[i] >> 4) & 0xF];
        fingerprint_str[i * 2 + 1] = hexdigits[hdr->fingerprint[i] & 0xF];
    }
    for (int i = 0; i < 4; i++) {
        display_text_center(120, 70 + i * 25, fingerprint_str + i * 16, 16, FONT_MONO, COLOR_BLACK, COLOR_WHITE, 0);
    }

    display_bar_radius(9, 184, 222, 50, COLOR_BL_DONE, COLOR_WHITE, 4);
    display_icon(9 + (222 - 19) / 2, 184 + (50 - 16) / 2, 20, 16, toi_icon_confirm + 12, sizeof(toi_icon_confirm) - 12, COLOR_WHITE, COLOR_BL_DONE);
}

// install UI

void ui_screen_install_confirm_upgrade(const vendor_header * const vhdr, const image_header * const hdr)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_text(16, 32, "Firmware update", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BLACK);
    display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12, COLOR_BLACK, COLOR_WHITE);
    display_text(55, 70, "Update firmware by", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_text(55, 95, vhdr->vstr, vhdr->vstr_len, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    const char *ver_str = format_ver("to version %d.%d.%d.%d?", hdr->version);
    display_text(55, 120, ver_str, -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    ui_confirm_cancel_buttons();
}

void ui_screen_install_confirm_newvendor(const vendor_header * const vhdr, const image_header * const hdr)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_text(16, 32, "Vendor change", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BLACK);
    display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12, COLOR_BLACK, COLOR_WHITE);
    display_text(55, 70, "Install firmware by", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_text(55, 95, vhdr->vstr, vhdr->vstr_len, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    const char *ver_str = format_ver("(version %d.%d.%d.%d)?", hdr->version);
    display_text(55, 120, ver_str, -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_text_center(120, 170, "Seed will be erased!", -1, FONT_NORMAL, COLOR_BL_FAIL, COLOR_WHITE, 0);
    ui_confirm_cancel_buttons();
}

void ui_screen_install(void)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_loader(0, -20, COLOR_BL_PROCESS, COLOR_WHITE, toi_icon_install, sizeof(toi_icon_install), COLOR_BLACK);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24, "Installing firmware", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
}

void ui_screen_install_progress_erase(int pos, int len)
{
    display_loader(250 * pos / len, -20, COLOR_BL_PROCESS, COLOR_WHITE, toi_icon_install, sizeof(toi_icon_install), COLOR_BLACK);
}

void ui_screen_install_progress_upload(int pos)
{
    display_loader(pos, -20, COLOR_BL_PROCESS, COLOR_WHITE, toi_icon_install, sizeof(toi_icon_install), COLOR_BLACK);
}

// wipe UI

void ui_screen_wipe_confirm(void)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_text(16, 32, "Wipe device", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_bar(16, 44, DISPLAY_RESX - 14 * 2, 1, COLOR_BLACK);
    display_icon(16, 54, 32, 32, toi_icon_info + 12, sizeof(toi_icon_info) - 12, COLOR_BLACK, COLOR_WHITE);
    display_text(55, 70, "Do you want to", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
    display_text(55, 95, "wipe the device?", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);

    display_text_center(120, 170, "Seed will be erased!", -1, FONT_NORMAL, COLOR_BL_FAIL, COLOR_WHITE, 0);
    ui_confirm_cancel_buttons();
}

void ui_screen_wipe(void)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_loader(0, -20, COLOR_BL_PROCESS, COLOR_WHITE, toi_icon_wipe, sizeof(toi_icon_wipe), COLOR_BLACK);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24, "Wiping device", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
}

void ui_screen_wipe_progress(int pos, int len)
{
    display_loader(1000 * pos / len, -20, COLOR_BL_PROCESS, COLOR_WHITE, toi_icon_wipe, sizeof(toi_icon_wipe), COLOR_BLACK);
}

// done UI

void ui_screen_done(int restart_seconds, secbool full_redraw)
{
    const char *str;
    char count_str[24];
    if (restart_seconds >= 1) {
        mini_snprintf(count_str, sizeof(count_str), "Done! Restarting in %d s", restart_seconds);
        str = count_str;
    } else {
        str = "Done! Unplug the device.";
    }
    if (sectrue == full_redraw) {
        display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    }
    display_loader(1000, -20, COLOR_BL_DONE, COLOR_WHITE, toi_icon_done, sizeof(toi_icon_done), COLOR_BLACK);
    if (secfalse == full_redraw) {
        display_bar(0, DISPLAY_RESY - 24 - 18, 240, 23, COLOR_WHITE);
    }
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24, str, -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
}

// error UI

void ui_screen_fail(void)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_WHITE);
    display_loader(1000, -20, COLOR_BL_FAIL, COLOR_WHITE, toi_icon_fail, sizeof(toi_icon_fail), COLOR_BLACK);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 24, "Failed! Please, reconnect.", -1, FONT_NORMAL, COLOR_BLACK, COLOR_WHITE, 0);
}

// general functions

void ui_fadein(void)
{
    display_fade(0, BACKLIGHT_NORMAL, 1000);
}

void ui_fadeout(void)
{
    display_fade(BACKLIGHT_NORMAL, 0, 500);
    display_clear();
}

int ui_user_input(int zones)
{
    for (;;) {
        uint32_t evt = touch_click();
        uint16_t x = touch_get_x(evt);
        uint16_t y = touch_get_y(evt);
        // clicked on Cancel button
        if ((zones & INPUT_CANCEL) && x >= 9 && x < 9 + 108 && y > 184 && y < 184 + 50) {
            return INPUT_CANCEL;
        }
        // clicked on Confirm button
        if ((zones & INPUT_CONFIRM) && x >= 123 && x < 123 + 108 && y > 184 && y < 184 + 50) {
            return INPUT_CONFIRM;
        }
        // clicked on Long Confirm button
        if ((zones & INPUT_LONG_CONFIRM) && x >= 9 && x < 9 + 222 && y > 184 && y < 184 + 50) {
            return INPUT_LONG_CONFIRM;
        }
        // clicked on Info icon
        if ((zones & INPUT_INFO) && x >= 16 && x < 16 + 32 && y > 54 && y < 54 + 32) {
            return INPUT_INFO;
        }
    }
}
