#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdbool.h>

void send_msg_success(int iface);
void send_msg_failure(int iface);
void send_msg_features(int iface, bool firmware_present);

#endif