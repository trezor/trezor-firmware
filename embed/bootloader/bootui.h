#ifndef __BOOTUI_H__
#define __BOOTUI_H__

#include "secbool.h"
#include "image.h"

void ui_screen_boot(const vendor_header * const vhdr, const image_header * const hdr);
void ui_screen_boot_wait(int delay);
void ui_screen_boot_click(void);

void ui_screen_info(secbool buttons, const vendor_header * const vhdr, const image_header * const hdr);

void ui_screen_install(void);
void ui_screen_install_progress_erase(int pos, int len);
void ui_screen_install_progress_upload(int pos);

void ui_screen_wipe(void);
void ui_screen_wipe_progress(int pos, int len);

void ui_screen_done(int restart);

void ui_screen_fail(void);

void ui_fadein(void);
void ui_fadeout(void);

#endif
