#ifndef __BOOTUI_H__
#define __BOOTUI_H__

#include "secbool.h"
#include "image.h"

void ui_screen_boot(const vendor_header * const vhdr, const image_header * const hdr);
void ui_screen_boot_wait(int wait_seconds);
void ui_screen_boot_click(void);

void ui_screen_first(void);
void ui_screen_second(void);
void ui_screen_third(void);

void ui_screen_info(secbool buttons, const vendor_header * const vhdr, const image_header * const hdr);
void ui_screen_info_fingerprint(const image_header * const hdr);

void ui_screen_install_confirm_upgrade(const vendor_header * const vhdr, const image_header * const hdr);
void ui_screen_install_confirm_newvendor(const vendor_header * const vhdr, const image_header * const hdr);
void ui_screen_install(void);
void ui_screen_install_progress_erase(int pos, int len);
void ui_screen_install_progress_upload(int pos);

void ui_screen_wipe_confirm(void);
void ui_screen_wipe(void);
void ui_screen_wipe_progress(int pos, int len);

void ui_screen_done(int restart_seconds, secbool full_redraw);

void ui_screen_fail(void);

void ui_fadein(void);
void ui_fadeout(void);

#define INPUT_CANCEL        0x01    // Cancel button
#define INPUT_CONFIRM       0x02    // Confirm button
#define INPUT_LONG_CONFIRM  0x04    // Long Confirm button
#define INPUT_INFO          0x08    // Info icon
int ui_user_input(int zones);

#endif
