#ifndef __BOOTLOADER_UI_H__
#define __BOOTLOADER_UI_H__

#define ui_WHITE 0xFFFF
#define ui_BLACK 0x0000

void screen_stage1(void);
void screen_stage2_jump(void);
void screen_stage2_invalid(void);

#endif
