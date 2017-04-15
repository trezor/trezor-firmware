#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdbool.h>
#include <stdint.h>

void send_msg_Success(int iface);
void send_msg_Failure(int iface);
void send_msg_Features(int iface, bool firmware_present);
void send_msg_FirmwareRequest(int iface, uint32_t offset, uint32_t length);

#endif
