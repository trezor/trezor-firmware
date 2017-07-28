#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdint.h>
#include <stdbool.h>

#include <pb.h>

#define MSG_HEADER1_LEN 9
#define MSG_HEADER2_LEN 1

#define USB_PACKET_SIZE   64
#define USB_IFACE_NUM     0

#define FIRMWARE_CHUNK_SIZE (128*1024)

bool msg_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size);

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);

#endif
