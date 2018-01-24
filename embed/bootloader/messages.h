#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdint.h>
#include "image.h"
#include "secbool.h"

#define USE_WEBUSB        0

#define USB_TIMEOUT       100
#define USB_PACKET_SIZE   64
#define USB_IFACE_NUM     0

#define FIRMWARE_SECTORS_COUNT 13
extern const uint8_t firmware_sectors[FIRMWARE_SECTORS_COUNT];

secbool msg_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size);

void send_user_abort(uint8_t iface_num, const char *msg);

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf, const vendor_header * const vhdr, const image_header * const hdr);
void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
int process_msg_WipeDevice(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);

#endif
