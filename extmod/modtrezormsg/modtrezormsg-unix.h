#include <arpa/inet.h>
#include <sys/socket.h>
#include <fcntl.h>
#include <assert.h>
#include <stdlib.h>

#define TREZOR_UDP_PORT 21324

static int s;
static struct sockaddr_in si_me, si_other;
static socklen_t slen = 0;

void msg_init(void)
{
    s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    assert(s != -1);

    fcntl(s, F_SETFL, O_NONBLOCK);

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

    int b;
    b = bind(s, (struct sockaddr*)&si_me, sizeof(si_me));
    assert(b != -1);
}

ssize_t msg_recv(uint8_t *iface, uint8_t *buf, size_t len)
{
    struct sockaddr_in si;
    socklen_t sl = sizeof(si);
    memset(buf, 0, len);
    *iface = 0; // TODO: return proper interface
    ssize_t r = recvfrom(s, buf, len, MSG_DONTWAIT, (struct sockaddr *)&si, &sl);
    if (r < 0) {
        return r;
    }
    si_other = si;
    slen = sl;
    return r;
}

ssize_t msg_send(uint8_t iface, const uint8_t *buf, size_t len)
{
    (void)iface; // TODO: ignore interface for now
    ssize_t r = len;
    if (slen > 0) {
        r = sendto(s, buf, len, MSG_DONTWAIT, (const struct sockaddr *)&si_other, slen);
    }
    return r;
}

// from modtrezorui:
uint32_t trezorui_poll_event(void);

#define msg_poll_ui_event trezorui_poll_event
