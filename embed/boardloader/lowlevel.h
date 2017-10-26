#ifndef __BOARDLOADER_LOWLEVEL_H__
#define __BOARDLOADER_LOWLEVEL_H__

#include "secbool.h"

void flash_set_option_bytes(void);
secbool flash_check_option_bytes(void);
void periph_init(void);
secbool reset_flags_init(void);

#endif
