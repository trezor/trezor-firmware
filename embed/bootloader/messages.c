#include <string.h>

#include <pb.h>
#include <pb_decode.h>
#include <pb_encode.h>
#include "messages.pb.h"

#include "common.h"
#include "display.h"
#include "flash.h"
#include "image.h"
#include "secbool.h"
#include "usb.h"
#include "version.h"

#include "messages.h"
#include "style.h"

#define MSG_HEADER1_LEN 9
#define MSG_HEADER2_LEN 1

secbool msg_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size)
{
    if (buf[0] != '?' || buf[1] != '#' || buf[2] != '#') {
        return secfalse;
    }
    *msg_id = (buf[3] << 8) + buf[4];
    *msg_size = (buf[5] << 24) + (buf[6] << 16) + (buf[7] << 8) + buf[8];
    return sectrue;
}

typedef struct {
    uint8_t iface_num;
    uint8_t packet_index;
    uint8_t packet_pos;
    uint8_t buf[USB_PACKET_SIZE];
} usb_write_state;

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
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
            usb_hid_write_blocking(state->iface_num, state->buf, USB_PACKET_SIZE, 100);
            // prepare new packet
            state->packet_index++;
            memset(state->buf, 0, USB_PACKET_SIZE);
            state->buf[0] = '?';
            state->packet_pos = MSG_HEADER2_LEN;
        }
    }

    return true;
}

static void _usb_write_flush(usb_write_state *state)
{
    // if packet is not filled up completely
    if (state->packet_pos < USB_PACKET_SIZE) {
        // pad it with zeroes
        memset(state->buf + state->packet_pos, 0, USB_PACKET_SIZE - state->packet_pos);
    }
    // send packet
    usb_hid_write_blocking(state->iface_num, state->buf, USB_PACKET_SIZE, 100);
}

static secbool _send_msg(uint8_t iface_num, uint16_t msg_id, const pb_field_t fields[], const void *msg)
{
    // determine message size by serializing it into a dummy stream
    pb_ostream_t sizestream = {
        .callback = NULL,
        .state = NULL,
        .max_size = SIZE_MAX,
        .bytes_written = 0,
        .errmsg = NULL};
    if (!pb_encode(&sizestream, fields, msg)) {
        return secfalse;
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
        return secfalse;
    }

    _usb_write_flush(&state);

    return sectrue;
}

#define MSG_SEND_INIT(TYPE) TYPE msg_send = TYPE##_init_default
#define MSG_SEND_ASSIGN_VALUE(FIELD, VALUE) do { msg_send.has_##FIELD = true; msg_send.FIELD = VALUE; } while (0)
// FIXME: strcpy -> strncpy
#define MSG_SEND_ASSIGN_STRING(FIELD, VALUE) do { msg_send.has_##FIELD = true; strcpy(msg_send.FIELD, VALUE); } while (0)
#define MSG_SEND(TYPE) do { _send_msg(iface_num, MessageType_MessageType_##TYPE, TYPE##_fields, &msg_send); } while (0)

typedef struct {
    uint8_t iface_num;
    uint8_t packet_index;
    uint8_t packet_pos;
    uint8_t *buf;
} usb_read_state;

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _usb_read(pb_istream_t *stream, uint8_t *buf, size_t count)
{
    usb_read_state *state = (usb_read_state *)(stream->state);

    size_t read = 0;
    // while we have data left
    while (read < count) {
        size_t remaining = count - read;
        // if all remaining data fit into our packet
        if (state->packet_pos + remaining <= USB_PACKET_SIZE) {
            // append data from buf to state->buf
            memcpy(buf + read, state->buf + state->packet_pos, remaining);
            // advance position
            state->packet_pos += remaining;
            // and return
            return true;
        } else {
            // append data that fits
            memcpy(buf + read, state->buf + state->packet_pos, USB_PACKET_SIZE - state->packet_pos);
            read += USB_PACKET_SIZE - state->packet_pos;
            // read next packet
            usb_hid_read_blocking(state->iface_num, state->buf, USB_PACKET_SIZE, 100);
            // prepare next packet
            state->packet_index++;
            state->packet_pos = MSG_HEADER2_LEN;
        }
    }

    return true;
}

static void _usb_read_flush(usb_read_state *state)
{
    (void)state;
}

static secbool _recv_msg(uint8_t iface_num, uint32_t msg_size, uint8_t *buf, const pb_field_t fields[], void *msg)
{
    usb_read_state state = {
        .iface_num = iface_num,
        .packet_index = 0,
        .packet_pos = MSG_HEADER1_LEN,
        .buf = buf
    };

    pb_istream_t stream = {
        .callback = &_usb_read,
        .state = &state,
        .bytes_left = msg_size,
        .errmsg = NULL
    };

    if (!pb_decode_noinit(&stream, fields, msg)) {
        return secfalse;
    }

    _usb_read_flush(&state);

    return sectrue;
}

#define MSG_RECV_INIT(TYPE) TYPE msg_recv = TYPE##_init_default
#define MSG_RECV_CALLBACK(FIELD, CALLBACK) do { msg_recv.FIELD.funcs.decode = &CALLBACK; } while (0)
#define MSG_RECV(TYPE) do { _recv_msg(iface_num, msg_size, buf, TYPE##_fields, &msg_recv); } while(0)

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf, secbool firmware_present)
{
    MSG_RECV_INIT(Initialize);
    MSG_RECV(Initialize);

    MSG_SEND_INIT(Features);
    MSG_SEND_ASSIGN_STRING(vendor, "trezor.io");
    MSG_SEND_ASSIGN_VALUE(major_version, VERSION_MAJOR);
    MSG_SEND_ASSIGN_VALUE(minor_version, VERSION_MINOR);
    MSG_SEND_ASSIGN_VALUE(patch_version, VERSION_PATCH);
    MSG_SEND_ASSIGN_VALUE(bootloader_mode, true);
    MSG_SEND_ASSIGN_VALUE(firmware_present, firmware_present);
    MSG_SEND(Features);
}

void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    MSG_RECV_INIT(Ping);
    MSG_RECV(Ping);

    MSG_SEND_INIT(Success);
    MSG_SEND_ASSIGN_STRING(message, msg_recv.message);
    MSG_SEND(Success);
}

static uint32_t firmware_remaining, firmware_flashed, chunk_requested;

static void progress_erase(int pos, int len)
{
    display_loader(250 * pos / len, 0, COLOR_BL_BLUE, COLOR_BLACK, 0, 0, 0);
}

void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    firmware_remaining = 0;
    firmware_flashed = 0;
    chunk_requested = 0;

    MSG_RECV_INIT(FirmwareErase);
    MSG_RECV(FirmwareErase);

    firmware_remaining = msg_recv.has_length ? msg_recv.length : 0;
    if (firmware_remaining > 0 && firmware_remaining % 4 == 0) {
        // erase flash
        uint8_t sectors[] = {
            FLASH_SECTOR_FIRMWARE_START,
            7,
            8,
            9,
            10,
            FLASH_SECTOR_FIRMWARE_END,
            FLASH_SECTOR_FIRMWARE_EXTRA_START,
            18,
            19,
            20,
            21,
            22,
            FLASH_SECTOR_FIRMWARE_EXTRA_END,
        };
        if (!flash_erase_sectors(sectors, 6 + 7, progress_erase)) {
            MSG_SEND_INIT(Failure);
            MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
            MSG_SEND_ASSIGN_STRING(message, "Could not erase flash");
            MSG_SEND(Failure);
            return;
        }
        // request new firmware
        chunk_requested = (firmware_remaining > IMAGE_CHUNK_SIZE) ? IMAGE_CHUNK_SIZE : firmware_remaining;
        MSG_SEND_INIT(FirmwareRequest);
        MSG_SEND_ASSIGN_VALUE(offset, 0);
        MSG_SEND_ASSIGN_VALUE(length, chunk_requested);
        MSG_SEND(FirmwareRequest);
    } else {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_DataError);
        MSG_SEND_ASSIGN_STRING(message, "Wrong firmware size");
        MSG_SEND(Failure);
    }
}

static uint32_t chunk_size = 0;

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _read_payload(pb_istream_t *stream, const pb_field_t *field, void **arg)
{
#define BUFSIZE 4096
    uint32_t buf[BUFSIZE / sizeof(uint32_t)];
    uint32_t chunk_written = 0;
    chunk_size = stream->bytes_left;
    while (stream->bytes_left) {
        // print loader
        display_loader(250 + 750 * (firmware_flashed + chunk_written) / (firmware_flashed + firmware_remaining), 0, COLOR_BL_BLUE, COLOR_BLACK, 0, 0, 0);
        memset(buf, 0xFF, sizeof(buf));
        // read data
        if (!pb_read(stream, (pb_byte_t *)buf, (stream->bytes_left > BUFSIZE) ? BUFSIZE : stream->bytes_left)) {
            return false;
        }
        // write data
        for (int i = 0; i < BUFSIZE / sizeof(uint32_t); i++) {
            if (!flash_write_word(FIRMWARE_START + firmware_flashed + chunk_written + i * sizeof(uint32_t), buf[i])) {
                return false;
            }
        }
        chunk_written += BUFSIZE;
    }
    return true;
}

int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    if (!flash_unlock()) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Could not unlock flash");
        MSG_SEND(Failure);
        return -1;
    }

    MSG_RECV_INIT(FirmwareUpload);
    MSG_RECV_CALLBACK(payload, _read_payload);
    MSG_RECV(FirmwareUpload);
    flash_lock();

    if (chunk_size != chunk_requested) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_DataError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid chunk size");
        MSG_SEND(Failure);
    }

    firmware_remaining -= chunk_requested;
    firmware_flashed += chunk_requested;

    if (firmware_remaining > 0) {
        chunk_requested = (firmware_remaining > IMAGE_CHUNK_SIZE) ? IMAGE_CHUNK_SIZE : firmware_remaining;
        MSG_SEND_INIT(FirmwareRequest);
        MSG_SEND_ASSIGN_VALUE(offset, firmware_flashed);
        MSG_SEND_ASSIGN_VALUE(length, chunk_requested);
        MSG_SEND(FirmwareRequest);
    } else {
        MSG_SEND_INIT(Success);
        MSG_SEND(Success);
    }
    return (int)firmware_remaining;
}

static void progress_wipe(int pos, int len)
{
    display_loader(1000 * pos / len, 0, COLOR_BL_BLUE, COLOR_BLACK, 0, 0, 0);
}

int process_msg_WipeDevice(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    uint8_t sectors[] = {
        FLASH_SECTOR_STORAGE_1,
        FLASH_SECTOR_STORAGE_2,
        FLASH_SECTOR_FIRMWARE_START,
        7,
        8,
        9,
        10,
        FLASH_SECTOR_FIRMWARE_END,
        FLASH_SECTOR_UNUSED_START,
        13,
        14,
        FLASH_SECTOR_UNUSED_END,
        FLASH_SECTOR_FIRMWARE_EXTRA_START,
        18,
        19,
        20,
        21,
        22,
        FLASH_SECTOR_FIRMWARE_EXTRA_END,
        FLASH_SECTOR_PIN_AREA,
    };
    if (!flash_erase_sectors(sectors, 2 + 6 + 4 + 7 + 1, progress_wipe)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Could not erase flash");
        MSG_SEND(Failure);
        return -1;
    } else {
        MSG_SEND_INIT(Success);
        MSG_SEND(Success);
        return 0;
    }
}

void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    // consume remaining message
    int remaining_chunks = (msg_size - (USB_PACKET_SIZE - MSG_HEADER1_LEN)) / (USB_PACKET_SIZE - MSG_HEADER2_LEN);
    for (int i = 0; i < remaining_chunks; i++) {
        int r = usb_hid_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE, 100);
        if (r != USB_PACKET_SIZE) {
            break;
        }
    }

    MSG_SEND_INIT(Failure);
    MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_UnexpectedMessage);
    MSG_SEND_ASSIGN_STRING(message, "Unexpected message");
    MSG_SEND(Failure);
}
