/*
 * Copyright (c) Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <string.h>
#include <stdlib.h>
#include <sys/types.h>

#include STM32_HAL_H

#include "common.h"
#include "display.h"
#include "flash.h"
#include "mini_printf.h"
#include "rng.h"
#include "sbu.h"
#include "sdcard.h"
#include "secbool.h"
#include "touch.h"
#include "usb.h"

enum { VCP_IFACE = 0x00 };

static void vcp_intr(void)
{
    display_clear();
    ensure(secfalse, "vcp_intr");
}

static void vcp_puts(const char *s, size_t len)
{
    int r = usb_vcp_write_blocking(VCP_IFACE, (const uint8_t *) s, len, -1);
    (void)r;
}

static char vcp_getchar(void)
{
    uint8_t c = 0;
    int r = usb_vcp_read_blocking(VCP_IFACE, &c, 1, -1);
    (void)r;
    return (char)c;
}

static void vcp_readline(char *buf, size_t len)
{
    for (;;) {
        char c = vcp_getchar();
        if (c == '\r') {
            vcp_puts("\r\n", 2);
            break;
        }
        if (c < 32 || c > 126) {  // not printable
            continue;
        }
        if (len > 1) {  // leave space for \0
            *buf = c;
            buf++;
            len--;
            vcp_puts(&c, 1);
        }
    }
    if (len > 0) {
        *buf = '\0';
    }
}

static void vcp_printf(const char *fmt, ...)
{
    static char buf[128];
    va_list va;
    va_start(va, fmt);
    int r = mini_vsnprintf(buf, sizeof(buf), fmt, va);
    va_end(va);
    vcp_puts(buf, r);
    vcp_puts("\r\n", 2);
}

static void usb_init_all(void)
{
    enum {
        VCP_PACKET_LEN = 64,
        VCP_BUFFER_LEN = 1024,
    };

    static const usb_dev_info_t dev_info = {
        .vendor_id     = 0x1209,
        .product_id    = 0x53C1,
        .release_num   = 0x0002,
        .manufacturer  = (const uint8_t *)"SatoshiLabs",
        .product       = (const uint8_t *)"TREZOR",
        .serial_number = (const uint8_t *)"",
    };

    static uint8_t tx_packet[VCP_PACKET_LEN];
    static uint8_t tx_buffer[VCP_BUFFER_LEN];
    static uint8_t rx_packet[VCP_PACKET_LEN];
    static uint8_t rx_buffer[VCP_BUFFER_LEN];

    static const usb_vcp_info_t vcp_info = {
        .tx_packet        = tx_packet,
        .tx_buffer        = tx_buffer,
        .rx_packet        = rx_packet,
        .rx_buffer        = rx_buffer,
        .tx_buffer_len    = VCP_BUFFER_LEN,
        .rx_buffer_len    = VCP_BUFFER_LEN,
        .rx_intr_fn       = vcp_intr,
        .rx_intr_byte     = 3,  // Ctrl-C
        .iface_num        = VCP_IFACE,
        .data_iface_num   = 0x01,
        .ep_cmd           = 0x82,
        .ep_in            = 0x81,
        .ep_out           = 0x01,
        .polling_interval = 10,
        .max_packet_len   = VCP_PACKET_LEN,
    };

    usb_init(&dev_info);
    ensure(usb_vcp_add(&vcp_info), "usb_vcp_add");
    usb_start();
}

static void test_border(void)
{
    enum {
        W  = 2,
        RX = DISPLAY_RESX,
        RY = DISPLAY_RESY,
    };
    display_clear();
    display_bar(0,    0,    RX, W,  0xFFFF);
    display_bar(0,    RY-W, RX, W,  0xFFFF);
    display_bar(0,    0,    W,  RY, 0xFFFF);
    display_bar(RX-W, 0,    W,  RY, 0xFFFF);
    display_refresh();
    vcp_printf("OK");
}

static void test_display(const char *colors)
{
    display_clear();

    size_t l = strlen(colors);
    size_t w = DISPLAY_RESX / l;

    for (size_t i = 0; i < l; i++) {
        uint16_t c = 0x0000;  // black
        switch (colors[i]) {
            case 'R': c = 0xF800; break;
            case 'G': c = 0x07E0; break;
            case 'B': c = 0x001F; break;
            case 'W': c = 0xFFFF; break;
        }
        display_bar(i * w, 0, i * w + w, 240, c);
    }
    display_refresh();
    vcp_printf("OK");
}

static secbool touch_click_timeout(uint32_t *touch, uint32_t timeout_ms)
{
    uint32_t deadline = HAL_GetTick() + timeout_ms;
    uint32_t r = 0;

    while (touch_read());
    while ((touch_read() & TOUCH_START) == 0) {
        if (HAL_GetTick() > deadline) return secfalse;
    }
    while (((r = touch_read()) & TOUCH_END) == 0) {
        if (HAL_GetTick() > deadline) return secfalse;
    }
    while (touch_read());

    *touch = r;
    return sectrue;
}

static void test_touch(const char *args)
{
    int column = args[0] - '0';
    int timeout = args[1] - '0';

    display_clear();
    switch (column) {
        case 1: display_bar(0, 0, 120, 120, 0xFFFF); break;
        case 2: display_bar(120, 0, 120, 120, 0xFFFF); break;
        case 3: display_bar(120, 120, 120, 120, 0xFFFF); break;
        default: display_bar(0, 120, 120, 120, 0xFFFF); break;
    }
    display_refresh();

    uint32_t evt = 0;
    if (touch_click_timeout(&evt, timeout * 1000)) {
        uint32_t x = (evt >> 12) & 0xFFF;
        uint32_t y = (evt >> 0) & 0xFFF;
        vcp_printf("OK %d %d", x, y);
    } else {
        vcp_printf("ERROR TIMEOUT");
    }
    display_clear();
    display_refresh();
}

static void test_pwm(const char *args)
{
    int v = atoi(args);

    display_backlight(v);
    display_refresh();
    vcp_printf("OK");
}

static void test_sd(void)
{
#define BLOCK_SIZE (32 * 1024)
    static uint32_t buf1[BLOCK_SIZE / sizeof(uint32_t)];
    static uint32_t buf2[BLOCK_SIZE / sizeof(uint32_t)];

    if (sectrue != sdcard_is_present()) {
        vcp_printf("ERROR NOCARD");
        return;
    }

    ensure(sdcard_power_on(), NULL);
    if (sectrue != sdcard_read_blocks(buf1, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
        vcp_printf("ERROR sdcard_read_blocks (0)");
        goto power_off;
    }
    for (int j = 1; j <= 2; j++) {
        for (int i = 0; i < BLOCK_SIZE / sizeof(uint32_t); i++) {
            buf1[i] ^= 0xFFFFFFFF;
        }
        if (sectrue != sdcard_write_blocks(buf1, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
            vcp_printf("ERROR sdcard_write_blocks (%d)", j);
            goto power_off;
        }
        if (sectrue != sdcard_read_blocks(buf2, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
            vcp_printf("ERROR sdcard_read_blocks (%d)", j);
            goto power_off;
        }
        if (0 != memcmp(buf1, buf2, sizeof(buf1))) {
            vcp_printf("ERROR DATA MISMATCH");
            goto power_off;
        }
    }
    vcp_printf("OK");

power_off:
    sdcard_power_off();
}

static void test_sbu(const char *args)
{
    secbool sbu1 = sectrue * (args[0] == '1');
    secbool sbu2 = sectrue * (args[1] == '1');
    sbu_set(sbu1, sbu2);
    vcp_printf("OK");
}

static void test_otp_read(void)
{
    uint8_t data[32];
    memset(data, 0, sizeof(data));
    ensure(flash_otp_read(0, 0, data, sizeof(data)), NULL);

    // strip trailing 0xFF
    for (size_t i = 0; i < sizeof(data); i++) {
        if (data[i] == 0xFF) {
            data[i] = 0x00;
            break;
        }
    }

    // use (null) for empty data
    if (data[0] == 0x00) {
        vcp_printf("OK (null)");
    } else {
        vcp_printf("OK %s", (const char *) data);
    }
}

static void test_otp_write(const char *args)
{
    char data[32];
    memset(data, 0, sizeof(data));
    strncpy(data, args, sizeof(data) - 1);
    ensure(flash_otp_write(0, 0, (const uint8_t *) data, sizeof(data)), NULL);
    ensure(flash_otp_lock(0), NULL);
    vcp_printf("OK");
}

static secbool startswith(const char *s, const char *prefix)
{
    return sectrue * (0 == strncmp(s, prefix, strlen(prefix)));
}

#define BACKLIGHT_NORMAL 150

int main(void)
{
    display_orientation(0);
    sdcard_init();
    touch_init();
    sbu_init();
    usb_init_all();

    display_clear();

    char dom[32];
    // format: TREZOR2-YYMMDD
    if (sectrue == flash_otp_read(0, 0, (uint8_t *)dom, 32) && 0 == memcmp(dom, "TREZOR2-", 8) && dom[31] == 0) {
        display_qrcode(DISPLAY_RESX / 2, DISPLAY_RESY / 2, dom, strlen(dom), 4);
        display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 30, dom + 8, -1, FONT_BOLD, COLOR_WHITE, COLOR_BLACK, 0);
    }

    display_fade(0, BACKLIGHT_NORMAL, 1000);

    char line[128];

    for (;;) {
        vcp_readline(line, sizeof(line));

        if (startswith(line, "PING")) {
            vcp_printf("OK");

        } else if (startswith(line, "BORDER")) {
            test_border();

        } else if (startswith(line, "DISP ")) {
            test_display(line + 5);

        } else if (startswith(line, "TOUCH ")) {
            test_touch(line + 6);

        } else if (startswith(line, "PWM ")) {
            test_pwm(line + 4);

        } else if (startswith(line, "SD")) {
            test_sd();

        } else if (startswith(line, "SBU ")) {
            test_sbu(line + 4);

        } else if (startswith(line, "OTP READ")) {
            test_otp_read();

        } else if (startswith(line, "OTP WRITE ")) {
            test_otp_write(line + 10);

        } else {
            vcp_printf("UNKNOWN");
        }
    }

    return 0;
}
