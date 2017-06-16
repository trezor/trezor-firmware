#include <pb_encode.h>
#include "messages.pb.h"

#include "usb.h"
#include "version.h"

#include "messages.h"

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

typedef struct {
    uint8_t iface_num;
    uint8_t packet_index;
    uint8_t packet_pos;
    uint8_t buf[USB_PACKET_SIZE];
} usb_write_state;

static bool _usb_write(pb_ostream_t *stream, const pb_byte_t *buf, size_t count)
{
    usb_write_state *state = (usb_write_state *)(stream->state);

    size_t written = 0;
    // while we have data left
    while (written < count) {
        size_t remaining = count - written;
        // if all remaining data fit into our packet
        if (state->packet_pos + remaining <= USB_PACKET_SIZE) {
            // append data from buf to state->buf
            memcpy(state->buf + state->packet_pos, buf + written, remaining);
            // advance position
            state->packet_pos += remaining;
            // and return
            return true;
        } else {
            // append data that fits
            memcpy(state->buf + state->packet_pos, buf + written, USB_PACKET_SIZE - state->packet_pos);
            written += USB_PACKET_SIZE - state->packet_pos;
            // send packet
            usb_hid_write_blocking(state->iface_num, state->buf, USB_PACKET_SIZE, 1);
            // prepare new packet
            state->packet_index++;
            memset(state->buf, 0, USB_PACKET_SIZE);
            state->buf[0] = '?';
            state->packet_pos = MSG_HEADER2_LEN;
        }
    }

    return true;
}

static void _usb_flush(usb_write_state *state)
{
    // if packet is not filled up completely
    if (state->packet_pos < USB_PACKET_SIZE) {
        // pad it with zeroes
        memset(state->buf + state->packet_pos, 0, USB_PACKET_SIZE - state->packet_pos);
    }
    // send packet
    usb_hid_write_blocking(state->iface_num, state->buf, USB_PACKET_SIZE, 1);
}

static bool _send_msg(uint8_t iface_num, uint16_t msg_id, const pb_field_t fields[], const void *msg)
{
    // determine message size by serializing it into a dummy stream
    pb_ostream_t sizestream = {
        .callback = NULL,
        .state = NULL,
        .max_size = SIZE_MAX,
        .bytes_written = 0,
        .errmsg = NULL};
    if (!pb_encode(&sizestream, fields, msg)) {
        return false;
    }
    const uint32_t msg_size = sizestream.bytes_written;

    usb_write_state state = {
        .iface_num = iface_num,
        .packet_index = 0,
        .packet_pos = MSG_HEADER1_LEN,
        .buf = {
            '?', '#', '#',
            (msg_id >> 8) & 0xFF, msg_id & 0xFF,
            (msg_size >> 24) & 0xFF, (msg_size >> 16) & 0xFF, (msg_size >> 8) & 0xFF, msg_size & 0xFF,
        },
    };

    pb_ostream_t stream = {
        .callback = &_usb_write,
        .state = &state,
        .max_size = SIZE_MAX,
        .bytes_written = 0,
        .errmsg = NULL
    };

    if (!pb_encode(&stream, fields, msg)) {
        return false;
    }

    _usb_flush(&state);

    return true;
}

static bool _encode_string(pb_ostream_t *stream, const pb_field_t *field, void * const *arg)
{
    if (!pb_encode_tag_for_field(stream, field)) {
        return false;
    }
    return pb_encode_string(stream, *arg, strlen(*arg));
}

#define MSG_INIT(TYPE) TYPE msg = TYPE##_init_default
#define MSG_ASSIGN_VALUE(FIELD, VALUE) do { msg.has_##FIELD = true; msg.FIELD = VALUE; } while (0)
#define MSG_ASSIGN_STRING(FIELD, VALUE) do { msg.FIELD.funcs.encode = &_encode_string; msg.FIELD.arg = VALUE; } while (0)
#define MSG_SEND(TYPE) do { _send_msg(iface_num, MessageType_MessageType_##TYPE, TYPE##_fields, &msg); } while (0)

static void consume_message(uint8_t iface_num, uint32_t msg_size, uint8_t *buf, void (* consumer)(const uint8_t *buf, uint8_t len))
{
    if (consumer) {
        consumer(buf + MSG_HEADER1_LEN, USB_PACKET_SIZE - MSG_HEADER1_LEN);
    }
    int remaining_chunks = (msg_size - (USB_PACKET_SIZE - MSG_HEADER1_LEN)) / (USB_PACKET_SIZE - MSG_HEADER2_LEN);
    for (int i = 0; i < remaining_chunks; i++) {
        int r = usb_hid_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE, 100);
        if (r != USB_PACKET_SIZE) {
            break;
        }
        if (consumer) {
            consumer(buf + MSG_HEADER2_LEN, USB_PACKET_SIZE - MSG_HEADER2_LEN);
        }
    }
}

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    consume_message(iface_num, msg_size, buf, NULL);

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

void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    consume_message(iface_num, msg_size, buf, NULL);

    MSG_INIT(Success);
    // TODO: read message from Ping
    MSG_ASSIGN_STRING(message, "PONG!");
    MSG_SEND(Success);
}

void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    consume_message(iface_num, msg_size, buf, NULL);

    // TODO: implement
    MSG_INIT(Failure);
    MSG_ASSIGN_VALUE(code, FailureType_Failure_FirmwareError);
    MSG_ASSIGN_STRING(message, "Unsupported message");
    MSG_SEND(Failure);
}

void process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    consume_message(iface_num, msg_size, buf, NULL);

    // TODO: implement
    MSG_INIT(Failure);
    MSG_ASSIGN_VALUE(code, FailureType_Failure_FirmwareError);
    MSG_ASSIGN_STRING(message, "Unsupported message");
    MSG_SEND(Failure);
}

void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    consume_message(iface_num, msg_size, buf, NULL);

    MSG_INIT(Failure);
    MSG_ASSIGN_VALUE(code, FailureType_Failure_UnexpectedMessage);
    MSG_ASSIGN_STRING(message, "Unexpected message");
    MSG_SEND(Failure);
}
