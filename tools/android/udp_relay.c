// Relay the emulator's UDP ports over TCP, which `adb forward` can carry.
//
// Usage: udp-relay <base port> <count>
//
// For each port, this listens on TCP 127.0.0.1:<port> and forwards datagrams
// to the firmware's UDP 127.0.0.1:<port>. Over TCP, each datagram is preceded
// by its length as a 16-bit big-endian integer. Like the firmware, the relay
// replies to the latest peer: a new TCP connection replaces the previous one.

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_PORTS 8
#define MAX_DATAGRAM 65535

typedef struct {
  int listener;
  int conn;
  int udp;
  uint8_t buf[2 + MAX_DATAGRAM];
  size_t len;
} relay_t;

static int open_socket(int type, int port, int listening) {
  int fd = socket(AF_INET, type, 0);
  if (fd < 0) {
    return -1;
  }
  struct sockaddr_in addr = {
      .sin_family = AF_INET,
      .sin_port = htons(port),
      .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
  };
  int one = 1;
  setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
  int ret = listening ? bind(fd, (struct sockaddr *)&addr, sizeof(addr))
                      : connect(fd, (struct sockaddr *)&addr, sizeof(addr));
  if (ret < 0 || (listening && listen(fd, 1) < 0)) {
    close(fd);
    return -1;
  }
  return fd;
}

static void drop_conn(relay_t *relay) {
  if (relay->conn >= 0) {
    close(relay->conn);
    relay->conn = -1;
  }
  relay->len = 0;
}

static int write_all(int fd, const uint8_t *data, size_t len) {
  while (len > 0) {
    ssize_t n = send(fd, data, len, MSG_NOSIGNAL);
    if (n < 0 && errno == EINTR) {
      continue;
    }
    if (n <= 0) {
      return -1;
    }
    data += n;
    len -= n;
  }
  return 0;
}

// Forward complete TCP frames as datagrams.
static void read_conn(relay_t *relay) {
  ssize_t n = recv(relay->conn, relay->buf + relay->len,
                   sizeof(relay->buf) - relay->len, 0);
  if (n <= 0) {
    drop_conn(relay);
    return;
  }
  relay->len += n;
  while (relay->len >= 2) {
    size_t frame = 2 + ((relay->buf[0] << 8) | relay->buf[1]);
    if (relay->len < frame) {
      break;
    }
    // The firmware may not be listening yet; losing a datagram is fine.
    send(relay->udp, relay->buf + 2, frame - 2, 0);
    relay->len -= frame;
    memmove(relay->buf, relay->buf + frame, relay->len);
  }
}

static void read_udp(relay_t *relay) {
  uint8_t frame[2 + MAX_DATAGRAM];
  ssize_t n = recv(relay->udp, frame + 2, MAX_DATAGRAM, 0);
  if (n < 0 || relay->conn < 0) {
    return;
  }
  frame[0] = n >> 8;
  frame[1] = n & 0xff;
  if (write_all(relay->conn, frame, 2 + n) < 0) {
    drop_conn(relay);
  }
}

int main(int argc, char **argv) {
  int base = argc == 3 ? atoi(argv[1]) : 0;
  int count = argc == 3 ? atoi(argv[2]) : 0;
  if (base <= 0 || count <= 0 || count > MAX_PORTS || base + count > 65536) {
    fprintf(stderr, "Usage: %s <base port> <count 1-%d>\n", argv[0], MAX_PORTS);
    return 2;
  }

  static relay_t relays[MAX_PORTS];
  for (int i = 0; i < count; i++) {
    relays[i].listener = open_socket(SOCK_STREAM, base + i, 1);
    relays[i].udp = open_socket(SOCK_DGRAM, base + i, 0);
    relays[i].conn = -1;
    if (relays[i].listener < 0 || relays[i].udp < 0) {
      perror("udp-relay");
      return 1;
    }
  }
  printf("udp-relay ready\n");
  fflush(stdout);

  for (;;) {
    struct pollfd fds[3 * MAX_PORTS];
    for (int i = 0; i < count; i++) {
      fds[3 * i] = (struct pollfd){.fd = relays[i].listener, .events = POLLIN};
      fds[3 * i + 1] = (struct pollfd){.fd = relays[i].conn, .events = POLLIN};
      fds[3 * i + 2] = (struct pollfd){.fd = relays[i].udp, .events = POLLIN};
    }
    if (poll(fds, 3 * count, -1) < 0) {
      if (errno == EINTR) {
        continue;
      }
      perror("poll");
      return 1;
    }
    for (int i = 0; i < count; i++) {
      relay_t *relay = &relays[i];
      if (fds[3 * i].revents & POLLIN) {
        int conn = accept(relay->listener, NULL, NULL);
        if (conn >= 0) {
          int one = 1;
          setsockopt(conn, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
          drop_conn(relay);
          relay->conn = conn;
        }
      } else if (fds[3 * i + 1].revents & (POLLIN | POLLHUP | POLLERR)) {
        read_conn(relay);
      }
      if (fds[3 * i + 2].revents & POLLIN) {
        read_udp(relay);
      }
    }
  }
}
