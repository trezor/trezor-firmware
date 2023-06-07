#ifndef __PEER_MANAGER__
#define __PEER_MANAGER__

#include "peer_manager.h"

pm_peer_id_t get_peer_id(void);

void whitelist_set(pm_peer_id_list_skip_t skip);

void identities_set(pm_peer_id_list_skip_t skip);

/**@brief Function for the Peer Manager initialization.
 */
void peer_manager_init(void);

void delete_bonds(void);

#endif
