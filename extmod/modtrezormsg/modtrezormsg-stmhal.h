#include <usrsw.h>

void msg_init(void)
{
}

ssize_t msg_recv(uint8_t *iface, uint8_t *buf, size_t len)
{
    return 0;
}

ssize_t msg_send(uint8_t iface, const uint8_t *buf, size_t len)
{
    return -1;
}

// this should match values used in trezorui_poll_sdl_event() in modtrezorui/display-unix.h
uint32_t msg_poll_ui_event(void)
{
    static int lp = 0;
    uint32_t r = 0;
    int p = switch_get();
    if (lp == 0 && p == 1) {
        r = 0x00010000; // touch start
    } else
    if (lp == 1 && p == 1) {
        r = 0x00020000; // touch move
    }
    if (lp == 1 && p == 0) {
        r = 0x00040000; // touch end
    }
    lp = p;
    return r;
}
