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
    if (false == pb_encode(&sizestream, fields, msg)) {
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

    if (false == pb_encode(&stream, fields, msg)) {
        return secfalse;
    }

    _usb_write_flush(&state);

    return sectrue;
}

#define MSG_SEND_INIT(TYPE) TYPE msg_send = TYPE##_init_default
#define MSG_SEND_ASSIGN_VALUE(FIELD, VALUE) { msg_send.has_##FIELD = true; msg_send.FIELD = VALUE; }
#define MSG_SEND_ASSIGN_STRING(FIELD, VALUE) { msg_send.has_##FIELD = true; memset(msg_send.FIELD, 0, sizeof(msg_send.FIELD)); strncpy(msg_send.FIELD, VALUE, sizeof(msg_send.FIELD) - 1); }
#define MSG_SEND(TYPE) _send_msg(iface_num, MessageType_MessageType_##TYPE, TYPE##_fields, &msg_send)

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

    if (false == pb_decode_noinit(&stream, fields, msg)) {
        return secfalse;
    }

    _usb_read_flush(&state);

    return sectrue;
}

#define MSG_RECV_INIT(TYPE) TYPE msg_recv = TYPE##_init_default
#define MSG_RECV_CALLBACK(FIELD, CALLBACK) { msg_recv.FIELD.funcs.decode = &CALLBACK; }
#define MSG_RECV(TYPE) _recv_msg(iface_num, msg_size, buf, TYPE##_fields, &msg_recv)

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

static uint32_t firmware_remaining, firmware_block, chunk_requested;

static void progress_erase(int pos, int len)
{
    display_loader(250 * pos / len, 0, COLOR_BL_BLUE, COLOR_BLACK, 0, 0, 0);
}

void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    firmware_remaining = 0;
    firmware_block = 0;
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
        if (sectrue != flash_erase_sectors(sectors, 6 + 7, progress_erase)) {
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
// SRAM is unused, so we can use it for chunk buffer
uint8_t * const chunk_buffer = (uint8_t * const)0x20000000;

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool _read_payload(pb_istream_t *stream, const pb_field_t *field, void **arg)
{
#define BUFSIZE 32768

    if (stream->bytes_left > IMAGE_CHUNK_SIZE) {
        chunk_size = 0;
        return false;
    }

    // clear chunk buffer
    memset(chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);

    uint32_t chunk_written = 0;
    chunk_size = stream->bytes_left;

    while (stream->bytes_left) {
        // update loader
        display_loader(250 + 750 * (firmware_block * IMAGE_CHUNK_SIZE + chunk_written) / (firmware_block * IMAGE_CHUNK_SIZE + firmware_remaining), 0, COLOR_BL_BLUE, COLOR_BLACK, 0, 0, 0);
        // read data
        if (!pb_read(stream, (pb_byte_t *)(chunk_buffer + chunk_written), (stream->bytes_left > BUFSIZE) ? BUFSIZE : stream->bytes_left)) {
            chunk_size = 0;
            return false;
        }
        chunk_written += BUFSIZE;
    }

    return true;
}

static image_header hdr;

extern secbool load_vendor_header_keys(const uint8_t * const data, vendor_header * const vhdr);

secbool compare_to_current_vendor_header(const vendor_header * const new_vhdr)
{
    vendor_header current_vhdr;
    if (sectrue != load_vendor_header_keys((const uint8_t *)FIRMWARE_START, &current_vhdr)) {
        return secfalse;
    }
    // TODO: less strict rules
    return sectrue * (0 == memcmp(new_vhdr, &current_vhdr, sizeof(vendor_header)));
}

int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size, uint8_t *buf)
{
    MSG_RECV_INIT(FirmwareUpload);
    MSG_RECV_CALLBACK(payload, _read_payload);
    secbool r = MSG_RECV(FirmwareUpload);

    if (sectrue != r || chunk_size != chunk_requested) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_DataError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid chunk size");
        MSG_SEND(Failure);
        return -1;
    }

    uint32_t firstskip = 0;
    if (firmware_block == 0) {
        vendor_header vhdr;
        if (sectrue != load_vendor_header_keys(chunk_buffer, &vhdr)) {
            MSG_SEND_INIT(Failure);
            MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
            MSG_SEND_ASSIGN_STRING(message, "Invalid vendor header");
            MSG_SEND(Failure);
            return -2;
        }
        if (sectrue != load_image_header(chunk_buffer + vhdr.hdrlen, FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub, &hdr)) {
            MSG_SEND_INIT(Failure);
            MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
            MSG_SEND_ASSIGN_STRING(message, "Invalid firmware header");
            MSG_SEND(Failure);
            return -3;
        }

        if (sectrue != compare_to_current_vendor_header(&vhdr)) {
            uint8_t sectors_storage[] = {
                FLASH_SECTOR_STORAGE_1,
                FLASH_SECTOR_STORAGE_2,
            };
            ensure(flash_erase_sectors(sectors_storage, 2, NULL), NULL);
            uint8_t sectors_pin[] = {
                FLASH_SECTOR_PIN_AREA,
            };
            ensure(flash_erase_sectors(sectors_pin, 2, NULL), NULL);
        }

        firstskip = IMAGE_HEADER_SIZE + vhdr.hdrlen;
    }

    if (sectrue != check_single_hash(hdr.hashes + firmware_block * 32, chunk_buffer + firstskip, chunk_size - firstskip)) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Invalid chunk hash");
        MSG_SEND(Failure);
        return -4;
    }

    if (sectrue != flash_unlock()) {
        MSG_SEND_INIT(Failure);
        MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
        MSG_SEND_ASSIGN_STRING(message, "Could not unlock flash");
        MSG_SEND(Failure);
        return -5;
    }

    // TODO: fix writing to non-continous area
    const uint32_t * const src = (const uint32_t * const)chunk_buffer;
    for (int i = 0; i < chunk_size / sizeof(uint32_t); i++) {
        if (sectrue != flash_write_word(FIRMWARE_START + firmware_block * IMAGE_CHUNK_SIZE + i * sizeof(uint32_t), src[i])) {
            MSG_SEND_INIT(Failure);
            MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ProcessError);
            MSG_SEND_ASSIGN_STRING(message, "Could not write data");
            MSG_SEND(Failure);
            flash_lock();
            return -6;
        }
    }

    flash_lock();

    firmware_remaining -= chunk_requested;
    firmware_block++;

    if (firmware_remaining > 0) {
        chunk_requested = (firmware_remaining > IMAGE_CHUNK_SIZE) ? IMAGE_CHUNK_SIZE : firmware_remaining;
        MSG_SEND_INIT(FirmwareRequest);
        MSG_SEND_ASSIGN_VALUE(offset, firmware_block * IMAGE_CHUNK_SIZE);
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
    if (sectrue != flash_erase_sectors(sectors, 2 + 6 + 4 + 7 + 1, progress_wipe)) {
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
