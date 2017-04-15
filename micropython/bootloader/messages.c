#include <assert.h>
#include <string.h>

#include "usb.h"
#include "version.h"

#include "protobuf.h"
#include "messages.h"

void send_msg_Success(int iface)
{
    // response: Success message (id 2), payload len 0
    PB_CTX ctx;
    pb_start(&ctx, 2);
    usb_hid_write_blocking(iface, pb_build(&ctx), 64, 1);
}

void send_msg_Failure(int iface)
{
    // response: Failure message (id 3), payload len 2
    //           - code = 99 (Failure_FirmwareError)
    PB_CTX ctx;
    pb_start(&ctx, 3);
    pb_add_varint(&ctx, "\x08", 99);
    usb_hid_write_blocking(iface, pb_build(&ctx), 64, 1);
}

void send_msg_Features(int iface, bool firmware_present)
{
    // response: Features message (id 17), payload len 22
    //           - vendor = "trezor.io"
    //           - major_version = VERSION_MAJOR
    //           - minor_version = VERSION_MINOR
    //           - patch_version = VERSION_PATCH
    //           - bootloader_mode = True
    //           - firmware_present = True/False
    PB_CTX ctx;
    pb_start(&ctx, 17);
    pb_add_string(&ctx, "\x0a", "trezor.io");
    pb_add_varint(&ctx, "\x10", VERSION_MAJOR);
    pb_add_varint(&ctx, "\x18", VERSION_MINOR);
    pb_add_varint(&ctx, "\x20", VERSION_PATCH);
    pb_add_bool(&ctx, "\x28", true);
    pb_add_bool(&ctx, "\x90\x01", firmware_present);
    usb_hid_write_blocking(iface, pb_build(&ctx), 64, 1);
}

void send_msg_FirmwareRequest(int iface, uint32_t offset, uint32_t length)
{
    // response: FirmwareRequest message (id 8), payload len X
    //           - offset = offset
    //           - length = length
    PB_CTX ctx;
    pb_start(&ctx, 8);
    pb_add_varint(&ctx, "\x08", offset);
    pb_add_varint(&ctx, "\x10", length);
    usb_hid_write_blocking(iface, pb_build(&ctx), 64, 1);
}
