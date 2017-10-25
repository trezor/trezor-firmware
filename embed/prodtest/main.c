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
#include "rng.h"
#include "sbu.h"
#include "sdcard.h"
#include "touch.h"
#include "usb.h"
#include "mini_printf.h"

enum {
    VCP_IFACE = 0x00,
};

static void vcp_intr(void)
{
    display_clear();
    shutdown();
}

static void vcp_puts(const char *s, size_t len)
{
    for (;;) {
        if (usb_vcp_write_blocking(VCP_IFACE, (const uint8_t *)s, len, 1000) > 0) {
            break;
        }
    }
}

static char vcp_getchar(void)
{
    uint8_t c;
    for (;;) {
        if (usb_vcp_read_blocking(VCP_IFACE, &c, 1, 1000) > 0) {
            break;
        }
    }
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
        if (c < 32 || c > 126) {
            continue;
        }
        if (len > 1) {  // leave space for \0
            *buf = c;
            buf++;
            len--;
        }
        vcp_puts(&c, 1);
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
        .rx_intr_byte     = 3, // Ctrl-C
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

static void test_display(const char *colors)
{
    display_clear();

    size_t l = strlen(colors);
    size_t w = 240 / l;

    for (size_t i = 0; i < l; i++) {
        uint16_t c;
        switch (colors[i]) {
        case 'R': c = 0xF800; break;
        case 'G': c = 0x07E0; break;
        case 'B': c = 0x001F; break;
        case 'W': c = 0xFFFF; break;
        default: c = 0x0000; break;
        }
        display_bar(i * w, 0, i * w + w, 240, c);
    }
    display_refresh();
    vcp_printf("OK");
}

static bool touch_click_timeout(uint32_t *touch, uint32_t timeout_ms)
{
    uint32_t deadline = HAL_GetTick() + timeout_ms;
    uint32_t r;

    while (touch_read()) { }
    while ((touch_read() & TOUCH_START) == 0) {
        if (HAL_GetTick() > deadline) {
            return false;
        }
    }
    while (((r = touch_read()) & TOUCH_END) == 0) {
        if (HAL_GetTick() > deadline) {
            return false;
        }
    }
    while (touch_read()) { }

    *touch = r;
    return true;
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

    uint32_t click;

    if (touch_click_timeout(&click, timeout * 1000)) {
        vcp_printf("OK %d %d", 0, 0);
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
    if (!sdcard_is_present()) {
        vcp_printf("ERROR NOCARD");
        return;
    }
    sdcard_power_on();
    static uint8_t buf1[8 * 1024];
    if (!sdcard_read_blocks(buf1, 0, 0)) {
        vcp_printf("ERROR sdcard_read_blocks");
        return;
    }
    if (!sdcard_write_blocks(buf1, 0, 0)) {
        vcp_printf("ERROR sdcard_write_blocks");
        return;
    }
    static uint8_t buf2[8 * 1024];
    if (!sdcard_read_blocks(buf2, 0, 0)) {
        vcp_printf("ERROR sdcard_read_blocks");
        return;
    }
    if (memcmp(buf1, buf2, sizeof(buf1)) != 0) {
        vcp_printf("ERROR DATA MISMATCH");
    }
    sdcard_power_off();
    vcp_printf("OK");
}

static void test_sbu(const char *args)
{
    bool sbu1 = args[0] == '1';
    bool sbu2 = args[1] == '1';
    sbu_set(sbu1, sbu2);
    vcp_printf("OK");
}

static void test_otp_read(void)
{
    uint8_t data[32];
    flash_otp_read(0, 0, data, sizeof(data));

    vcp_printf("OK %s", (const char *)data);
}

static void test_otp_write(const char *args)
{
    char data[32];
    memset(data, 0, sizeof(data));
    strcpy(data, args);

    flash_otp_write(0, 0, (const uint8_t *)data, sizeof(data));
    flash_otp_lock(0);
    vcp_printf("OK");
}

static bool startswith(const char *s, const char *prefix)
{
    return strncmp(s, prefix, strlen(prefix)) == 0;
}

int main(void)
{
    display_orientation(0);
    display_backlight(255);
    sdcard_init();
    touch_init();
    sbu_init();
    usb_init_all();

    display_clear();

    char line[128];

    for (;;) {
        vcp_readline(line, sizeof(line));

        if (startswith(line, "PING")) {
            vcp_printf("OK");

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
