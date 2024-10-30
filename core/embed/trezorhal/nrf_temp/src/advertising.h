


#include <stdbool.h>


void advertising_start(bool wl);
void advertising_stop(void);
bool is_advertising(void);
bool is_advertising_whitelist(void);
void advertising_init(void);
void advertising_setup_wl(void);
int advertising_get_bond_count(void);
void erase_bonds(void);
