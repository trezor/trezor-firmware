#pragma once

#include <arpa/inet.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

/// Emulator datagram socket, for USB and BLE. Currently uses UDP but can be
/// possibly switched to unix datagram sockets.
typedef struct {
  /// Port number.
  uint16_t port;
  /// Socket file descriptor.
  int sock;
  /// Emulator host+port.
  struct sockaddr_in si_me;
  /// Address of the other side of the connection. Set based on the last packet
  /// received.
  struct sockaddr_in si_other;
  /// Length of si_other. Before first packet is received this is 0 meaning we
  /// don't know the addres of the other side.
  socklen_t slen;
} emu_sock_t;

void sock_init(emu_sock_t *sock);

void sock_start(emu_sock_t *sock, const char *ip, uint16_t port);

void sock_stop(emu_sock_t *sock);

bool sock_can_send(emu_sock_t *sock);

bool sock_can_recv(emu_sock_t *sock);

ssize_t sock_sendto(emu_sock_t *sock, const void *data, size_t len);

ssize_t sock_recvfrom(emu_sock_t *sock, uint8_t *data, size_t max_len);
