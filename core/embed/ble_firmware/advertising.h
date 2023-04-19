#ifndef __ADVERTISING__
#define __ADVERTISING__

#include <stdbool.h>

void advertising_init(void);

void advertising_start(bool whitelist);

void advertising_stop(void);

void advertising_restart_without_whitelist(void);

bool is_advertising(void);

#endif
