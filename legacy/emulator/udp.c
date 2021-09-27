/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <arpa/inet.h>
#include <errno.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

#define TREZOR_UDP_PORT 21324

struct usb_socket {
  int fd;
  struct sockaddr_in from;
  socklen_t fromlen;
};

static struct usb_socket usb_main;
static struct usb_socket usb_debug;

static struct pollfd usb_fds[2];

static int socket_setup(int port) {
  int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (fd < 0) {
    perror("Failed to create socket");
    exit(1);
  }

  struct sockaddr_in addr = {0};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

  if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
    perror("Failed to bind socket");
    exit(1);
  }

  return fd;
}

static size_t socket_write(struct usb_socket *sock, const void *buffer,
                           size_t size) {
  if (sock->fromlen > 0) {
    ssize_t n = sendto(sock->fd, buffer, size, MSG_DONTWAIT,
                       (const struct sockaddr *)&sock->from, sock->fromlen);
    if (n < 0 || ((size_t)n) != size) {
      perror("Failed to write socket");
      return 0;
    }
  }

  return size;
}

static size_t socket_read(struct usb_socket *sock, void *buffer, size_t size) {
  sock->fromlen = sizeof(sock->from);
  ssize_t n = recvfrom(sock->fd, buffer, size, MSG_DONTWAIT,
                       (struct sockaddr *)&sock->from, &sock->fromlen);

  if (n < 0) {
    if (errno != EAGAIN && errno != EWOULDBLOCK) {
      perror("Failed to read socket");
    }
    return 0;
  }

  static const char msg_ping[] = {'P', 'I', 'N', 'G', 'P', 'I', 'N', 'G'};
  static const char msg_pong[] = {'P', 'O', 'N', 'G', 'P', 'O', 'N', 'G'};

  if (n == sizeof(msg_ping) &&
      memcmp(buffer, msg_ping, sizeof(msg_ping)) == 0) {
    socket_write(sock, msg_pong, sizeof(msg_pong));
    return 0;
  }

  return n;
}

void emulatorSocketInit(void) {
  usb_main.fd = socket_setup(TREZOR_UDP_PORT);
  usb_main.fromlen = 0;
  usb_fds[0].fd = usb_main.fd;
  usb_fds[0].events = POLLIN;

  usb_debug.fd = socket_setup(TREZOR_UDP_PORT + 1);
  usb_debug.fromlen = 0;
  usb_fds[1].fd = usb_debug.fd;
  usb_fds[1].events = POLLIN;
}

size_t emulatorSocketRead(int *iface, void *buffer, size_t size,
                          int timeout_ms) {
  if (poll(usb_fds, 2, timeout_ms) > 0) {
    if (usb_fds[0].revents & POLLIN) {
      *iface = 0;
      return socket_read(&usb_main, buffer, size);
    } else if (usb_fds[1].revents & POLLIN) {
      *iface = 1;
      return socket_read(&usb_debug, buffer, size);
    }
  }
  return 0;
}

size_t emulatorSocketWrite(int iface, const void *buffer, size_t size) {
  if (iface == 0) {
    return socket_write(&usb_main, buffer, size);
  }
  if (iface == 1) {
    return socket_write(&usb_debug, buffer, size);
  }
  return 0;
}
