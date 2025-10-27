#include "io/unix/sock.h"
#include "trezor_rtl.h"

#include <string.h>

void sock_init(emu_sock_t *sock) {
  memset(sock, 0, sizeof(*sock));
  sock->sock = -1;
}

void sock_start(emu_sock_t *sock, const char *ip, uint16_t port) {
  sock->port = port;
  sock->sock = socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK, IPPROTO_UDP);

  ensure(sectrue * (sock->sock >= 0), NULL);

  int ret = fcntl(sock->sock, F_SETFL, O_NONBLOCK);
  ensure(sectrue * (ret != -1), NULL);

  sock->si_me.sin_family = AF_INET;
  sock->si_me.sin_addr.s_addr = ip ? inet_addr(ip) : htonl(INADDR_LOOPBACK);
  sock->si_me.sin_port = htons(sock->port);

  ret = bind(sock->sock, (struct sockaddr *)&(sock->si_me),
             sizeof(struct sockaddr_in));
  ensure(sectrue * (ret == 0), NULL);
}

void sock_stop(emu_sock_t *sock) {
  if (sock->sock >= 0) {
    close(sock->sock);
    sock->sock = -1;
  }
}

bool sock_can_send(emu_sock_t *sock) {
  if (sock->slen == 0) {
    return true;
  }
  struct pollfd fds[] = {
      {sock->sock, POLLOUT, 0},
  };
  int r = poll(fds, 1, 0);
  return (r > 0);
}

bool sock_can_recv(emu_sock_t *sock) {
  struct pollfd fds[] = {
      {sock->sock, POLLIN, 0},
  };
  int r = poll(fds, 1, 0);
  return (r > 0);
}

ssize_t sock_sendto(emu_sock_t *sock, const void *data, size_t len) {
  if (sock->slen > 0) {
    ssize_t r = sendto(sock->sock, data, len, MSG_DONTWAIT,
                       (const struct sockaddr *)&(sock->si_other), sock->slen);
    if (r != len) {
      return -1;
    }
    return r;
  }
  return len;
}

ssize_t sock_recvfrom(emu_sock_t *sock, uint8_t *data, size_t max_len) {
  struct sockaddr_in si;
  socklen_t sl = sizeof(si);
  memset(data, 0, max_len);
  ssize_t r = recvfrom(sock->sock, data, max_len, MSG_DONTWAIT,
                       (struct sockaddr *)&si, &sl);
  if (r <= 0) {
    return 0;
  }

  sock->si_other = si;
  sock->slen = sl;
  return r;
}
