#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdint.h>
#include <stdbool.h>

#define USB_PACKET_SIZE   64
#define USB_IFACE_NUM     0

bool msg_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size);

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf, bool firmware_present);
void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
int process_msg_WipeDevice(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);

#endif
