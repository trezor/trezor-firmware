#ifndef __BOOTLOADER_UI_H__
#define __BOOTLOADER_UI_H__

void screen_welcome(void);
void screen_info(void);
void screen_upload_request(void);
void screen_upload_progress(int permil);
void screen_upload_success(void);
void screen_upload_abort(void);

#endif
