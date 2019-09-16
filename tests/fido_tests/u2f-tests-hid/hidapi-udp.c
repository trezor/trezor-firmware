/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "hidapi.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <arpa/inet.h>

int hid_init(void) {
  return 0;
}

int hid_exit(void) {
  return 0;
}

hid_device *hid_open_path(const char *path) {

  int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (fd < 0) {
    fprintf(stderr, "Failed to create socket\n");
    return NULL;
  }

  hid_device *d = malloc(sizeof(hid_device));
  memset(d, 0, sizeof(hid_device));
  d->fd = fd;

  d->other.sin_family = AF_INET;
  d->other.sin_port = htons(atoi(path));
  d->other.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  d->slen = sizeof(d->other);

  return d;
}

void hid_close(hid_device *device) {
  if (device && device->fd) {
    close(device->fd);
  }
  if (device) {
    free(device);
  }
}

int hid_write(hid_device *device, const unsigned char *data, size_t length) {
  if (!device) {
    fprintf(stderr, "Device can't be NULL\n");
    return -1;
  }
  if (length != 65) {
    fprintf(stderr, "Invalid packet size\n");
    return -1;
  }
  ssize_t n = sendto(device->fd, data + 1, length - 1, 0, (const struct sockaddr *)&(device->other), device->slen);
  if (n < 0 || ((size_t)n) != length - 1) {
    fprintf(stderr, "Failed to write socket\n");
    return -1;
  }
  usleep(1500);
  return length;
}

int hid_read_timeout(hid_device *device, unsigned char *data, size_t length, int milliseconds) {
  if (!device) {
    fprintf(stderr, "Device can't be NULL\n");
    return -1;
  }
  for (int i = 0; i < milliseconds; i++) {
    usleep(1500);
    ssize_t n = recvfrom(device->fd, data, length, MSG_DONTWAIT, (struct sockaddr *)&(device->other), &(device->slen));
    if (n < 0) {
      if (errno == EAGAIN && errno == EWOULDBLOCK) { // timeout tick
        continue;
      } else {
        fprintf(stderr, "Failed to read socket\n");
        return -1;
      }
    } else {
      return n;
    }
  }
  return 0;
}
