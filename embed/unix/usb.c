/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/poll.h>
#include <fcntl.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>

#include "usb.h"
#include "touch.h"

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func);

#define ensure(expr, msg) (((expr) == sectrue) ? (void)0 : __fatal_error(#expr, msg, __FILE__, __LINE__, __func__))

// emulator opens UDP server on TREZOR_UDP_PORT port
// and emulates HID/WebUSB interface TREZOR_UDP_IFACE
// gracefully ignores all other USB interfaces

#define TREZOR_UDP_IFACE  0
#define TREZOR_UDP_PORT   21324

static usb_iface_type_t emulator_usb_iface_type = USB_IFACE_TYPE_DISABLED;

static int sock = -1;
static struct sockaddr_in si_me, si_other;
static socklen_t slen = 0;

void usb_init(const usb_dev_info_t *dev_info) {
    (void)dev_info;
}

void usb_deinit(void) {
}

void usb_start(void) {
    // start server only if interface 0 is either HID or WebUSB
    if (emulator_usb_iface_type == USB_IFACE_TYPE_HID || emulator_usb_iface_type == USB_IFACE_TYPE_WEBUSB) {
        sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        ensure(sectrue * (sock >= 0), NULL);

        fcntl(sock, F_SETFL, O_NONBLOCK);

        si_me.sin_family = AF_INET;
        const char *ip = getenv("TREZOR_UDP_IP");
        if (ip) {
            si_me.sin_addr.s_addr = inet_addr(ip);
        } else {
            si_me.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        }
        const char *port = getenv("TREZOR_UDP_PORT");
        if (port) {
            si_me.sin_port = htons(atoi(port));
        } else {
            si_me.sin_port = htons(TREZOR_UDP_PORT);
        }

        ensure(sectrue * (0 == bind(sock, (struct sockaddr*)&si_me, sizeof(si_me))), NULL);
    }
}

void usb_stop(void) {
}

secbool usb_hid_add(const usb_hid_info_t *info) {
    // store iface type if it is the emulated iface
    if (info->iface_num == TREZOR_UDP_IFACE) {
        emulator_usb_iface_type = USB_IFACE_TYPE_HID;
    }
    return sectrue;
}

secbool usb_webusb_add(const usb_webusb_info_t *info) {
    // store iface type if it is the emulated iface
    if (info->iface_num == TREZOR_UDP_IFACE) {
        emulator_usb_iface_type = USB_IFACE_TYPE_WEBUSB;
    }
    return sectrue;
}

secbool usb_vcp_add(const usb_vcp_info_t *info) {
    return sectrue;
}

static secbool usb_emulated_can_read(uint8_t iface_num) {
    struct pollfd fds[] = {
        { sock, POLLIN, 0 },
    };
    int r = poll(fds, 1, 0);
    return sectrue * (r > 0);
}

secbool usb_hid_can_read(uint8_t iface_num) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_HID) {
        return secfalse;
    }
    return usb_emulated_can_read(iface_num);
}

secbool usb_webusb_can_read(uint8_t iface_num) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_WEBUSB) {
        return secfalse;
    }
    return usb_emulated_can_read(iface_num);
}

static secbool usb_emulated_can_write(uint8_t iface_num) {
    struct pollfd fds[] = {
        { sock, POLLOUT, 0 },
    };
    int r = poll(fds, 1, 0);
    return sectrue * (r > 0);
}

secbool usb_hid_can_write(uint8_t iface_num) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_HID) {
        return secfalse;
    }
    return usb_emulated_can_write(iface_num);
}

secbool usb_webusb_can_write(uint8_t iface_num) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_WEBUSB) {
        return secfalse;
    }
    return usb_emulated_can_write(iface_num);
}

static int usb_emulated_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
    struct sockaddr_in si;
    socklen_t sl = sizeof(si);
    ssize_t r = recvfrom(sock, buf, len, MSG_DONTWAIT, (struct sockaddr *)&si, &sl);
    if (r < 0) {
        return r;
    }
    si_other = si;
    slen = sl;
    static const char *ping_req = "PINGPING";
    static const char *ping_resp = "PONGPONG";
    if (r == strlen(ping_req) && 0 == memcmp(ping_req, buf, strlen(ping_req))) {
        if (slen > 0) {
            sendto(sock, ping_resp, strlen(ping_resp), MSG_DONTWAIT, (const struct sockaddr *)&si_other, slen);
        }
        return 0;
    }
    return r;
}

int usb_hid_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_HID) {
        return 0;
    }
    return usb_emulated_read(iface_num, buf, len);
}

int usb_webusb_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_WEBUSB) {
        return 0;
    }
    return usb_emulated_read(iface_num, buf, len);
}

static int usb_emulated_write(uint8_t iface_num, const uint8_t *buf, uint32_t len)
{
    ssize_t r = len;
    if (slen > 0) {
        r = sendto(sock, buf, len, MSG_DONTWAIT, (const struct sockaddr *)&si_other, slen);
    }
    return r;
}

int usb_hid_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_HID) {
        return 0;
    }
    return usb_emulated_write(iface_num, buf, len);
}

int usb_webusb_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
    if (iface_num != TREZOR_UDP_IFACE || emulator_usb_iface_type != USB_IFACE_TYPE_WEBUSB) {
        return 0;
    }
    return usb_emulated_write(iface_num, buf, len);
}

void pendsv_kbd_intr(void) {
}

void mp_hal_set_vcp_iface(int iface_num) {
}
