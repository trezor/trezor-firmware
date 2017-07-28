#ifndef __TREZORHAL_TOUCH_H__
#define __TREZORHAL_TOUCH_H__

#define TOUCH_START 0x00010000
#define TOUCH_MOVE  0x00020000
#define TOUCH_END   0x00040000

int touch_init(void);
uint32_t touch_read(void);

#endif
