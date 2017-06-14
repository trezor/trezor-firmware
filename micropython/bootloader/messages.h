#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdint.h>
#include <stdbool.h>

#include <pb.h>

#define MSG_HEADER_LEN 9

bool msg_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size);

void process_msg_Initialize(uint8_t iface_num);
void process_msg_Ping(uint8_t iface_num);
void process_msg_FirmwareErase(uint8_t iface_num);
void process_msg_FirmwareUpload(uint8_t iface_num);
void process_msg_unknown(uint8_t iface_num);

#endif
