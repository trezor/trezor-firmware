#include <pb_encode.h>
#include "messages.pb.h"

#include "usb.h"
#include "version.h"

#include "messages.h"

#define UPLOAD_CHUNK_SIZE (128*1024)

// DECODE

bool msg_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size)
{
        if (buf[0] != '?' || buf[1] != '#' || buf[2] != '#') {
            return false;
        }
        *msg_id = (buf[3] << 8) + buf[4];
        *msg_size = (buf[5] << 24) + (buf[6] << 16) + (buf[7] << 8) + buf[8];
        return true;
}

// ENCODE

bool _encode_string(pb_ostream_t *stream, const pb_field_t *field, void * const *arg)
{
    if (!pb_encode_tag_for_field(stream, field)) {
        return false;
    }
    return pb_encode_string(stream, *arg, strlen(*arg));
}

bool _send_msg(uint8_t iface_num, uint16_t msg_id, const pb_field_t fields[], const void *msg)
{
    // determine message size by serializing it into dummy stream
    pb_ostream_t sizestream = {0, 0, SIZE_MAX, 0, 0};
    if (!pb_encode(&sizestream, fields, msg)) {
        return false;
    }

    // TODO: properly send

    uint8_t buf[64];

    buf[0] = '?';
    buf[1] = '#';
    buf[2] = '#';
    buf[3] = (msg_id >> 8) & 0xFF;
    buf[4] = msg_id & 0xFF;
    buf[5] = (sizestream.bytes_written >> 24) & 0xFF;
    buf[6] = (sizestream.bytes_written >> 16) & 0xFF;
    buf[7] = (sizestream.bytes_written >> 8) & 0xFF;
    buf[8] = sizestream.bytes_written & 0xFF;

    pb_ostream_t stream = pb_ostream_from_buffer(buf + MSG_HEADER_LEN, sizeof(buf) - MSG_HEADER_LEN);
    if (!pb_encode(&stream, fields, msg)) {
        return false;
    }

    usb_hid_write_blocking(iface_num, buf, 64, 1);

    return true;
}

#define MSG_INIT(TYPE) TYPE msg = TYPE##_init_default
#define MSG_ASSIGN_VALUE(FIELD, VALUE) do { msg.has_##FIELD = true; msg.FIELD = VALUE; } while (0)
#define MSG_ASSIGN_STRING(FIELD, VALUE) do { msg.FIELD.funcs.encode = &_encode_string; msg.FIELD.arg = VALUE; } while (0)
#define MSG_SEND(TYPE) do { _send_msg(iface_num, MessageType_MessageType_##TYPE, TYPE##_fields, &msg); } while (0)

void process_msg_Initialize(uint8_t iface_num)
{
    MSG_INIT(Features);
    MSG_ASSIGN_STRING(vendor, "trezor.io");
    MSG_ASSIGN_VALUE(major_version, VERSION_MAJOR);
    MSG_ASSIGN_VALUE(minor_version, VERSION_MINOR);
    MSG_ASSIGN_VALUE(patch_version, VERSION_PATCH);
    MSG_ASSIGN_VALUE(bootloader_mode, true);
    // TODO: properly detect firmware
    MSG_ASSIGN_VALUE(firmware_present, false);
    MSG_SEND(Features);
}

void process_msg_Ping(uint8_t iface_num)
{
    MSG_INIT(Success);
    // TODO: read message from Ping
    MSG_ASSIGN_STRING(message, "PONG!");
    MSG_SEND(Success);
}

void process_msg_FirmwareErase(uint8_t iface_num)
{
    // TODO: implement
    MSG_INIT(Failure);
    MSG_ASSIGN_VALUE(code, FailureType_Failure_FirmwareError);
    MSG_ASSIGN_STRING(message, "Unsupported message");
    MSG_SEND(Failure);
}

void process_msg_FirmwareUpload(uint8_t iface_num)
{
    // TODO: implement
    MSG_INIT(Failure);
    MSG_ASSIGN_VALUE(code, FailureType_Failure_FirmwareError);
    MSG_ASSIGN_STRING(message, "Unsupported message");
    MSG_SEND(Failure);
}

void process_msg_unknown(uint8_t iface_num)
{
    MSG_INIT(Failure);
    MSG_ASSIGN_VALUE(code, FailureType_Failure_UnexpectedMessage);
    MSG_ASSIGN_STRING(message, "Unexpected message");
    MSG_SEND(Failure);
}
