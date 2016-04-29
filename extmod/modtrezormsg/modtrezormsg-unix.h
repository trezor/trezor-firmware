#include <arpa/inet.h>
#include <sys/socket.h>
#include <fcntl.h>
#include <assert.h>

#define TREZOR_PORT 21324

static int s;
static struct sockaddr_in si_me, si_other;
static socklen_t slen = 0;

void msg_init(void)
{
    s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    assert(s != -1);

    fcntl(s, F_SETFL, O_NONBLOCK);

    si_me.sin_family = AF_INET;
    si_me.sin_port = htons(TREZOR_PORT);
    si_me.sin_addr.s_addr = htonl(INADDR_ANY);

    int b;
    b = bind(s, (struct sockaddr*)&si_me, sizeof(si_me));
    assert(b != -1);
}

#define RECV_BUFLEN 64

const uint8_t *msg_recv(void)
{
    static uint8_t buf[RECV_BUFLEN];
    struct sockaddr_in si;
    socklen_t sl;
    memset(buf, 0, sizeof(buf));
    int len = recvfrom(s, buf, RECV_BUFLEN, MSG_DONTWAIT, (struct sockaddr *)&si, &sl);
    if (len < 0) {
        return 0;
    }
    si_other = si;
    slen = sl;
    return buf;
}

int msg_send(uint8_t *buf, size_t len)
{
    int r = -1;
    if (slen) {
        r = sendto(s, buf, len, MSG_DONTWAIT, (const struct sockaddr *)&si_other, slen);
    }
    return r;
}

// from modtrezorui:
uint32_t trezorui_poll_sdl_event(void);

#define msg_poll_ui_event trezorui_poll_sdl_event
