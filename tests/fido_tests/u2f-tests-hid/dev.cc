// Copyright Google Inc. All rights reserved.
//
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file or at
// https://developers.google.com/open-source/licenses/bsd

// Thin shim to allow abstracting away from hid_* calls to
// a set or read/write pipes w/ a particular interface.
#include <assert.h>
#include <endian.h>
#include <fcntl.h>
#include <string.h>

#include <string>

#include "u2f_util.h"

bool DEV_opened(struct U2Fob* device) {
  return device->dev != NULL || (device->fd_in != -1 && device->fd_out != -1);
}

void DEV_close(struct U2Fob* device) {
  if (device->dev) {
    hid_close(device->dev);
    device->dev = NULL;
  }
  if (device->fd_in != -1) {
    close(device->fd_in);
    device->fd_in = -1;
  }
  if (device->fd_out != -1) {
    close(device->fd_out);
    device->fd_out = -1;
  }
}

void DEV_open_path(struct U2Fob* device) {
  std::string path(device->path);
  if (path[path.size() - 1] == '-') {
    device->fd_in = open((path + "out").c_str(), O_RDONLY);
    device->fd_out = open((path + "in").c_str(), O_RDWR);
  } else {
    device->dev = hid_open_path(device->path);
  }
}

void DEV_quit(struct U2Fob* device) {
  if (device->dev) return;

  struct {
    uint32_t cmd;
    uint32_t len;
    uint32_t mode;
  } data;

  data.cmd = htole32(2);  // kReset
  data.len = htole32(4);
  data.mode = htole32(3);  // kResetQuit
  assert(write(device->fd_out, (const void*)&data, sizeof(data)) == sizeof(data));
}

int DEV_write(struct U2Fob* device, const uint8_t* src, size_t n) {
  assert(n == 65);

  if (device->dev != NULL) return hid_write(device->dev, src, n);

  struct {
    uint32_t cmd;
    uint32_t len;
    uint8_t data[64];
  } data;

  static_assert(sizeof(data) == 64 + 8);

  data.cmd = htole32(4);  // k64ByteWrite
  data.len = htole32(64);
  memcpy(data.data, src + 1, 64);

  int nwritten = write(device->fd_out, (const void*)&data, sizeof(data));
  assert(nwritten == sizeof(data));
  usleep(1500);  // delay a bit to mimic HID transport.
  return 65;
}

int DEV_read_timeout(struct U2Fob* device, uint8_t* dst, size_t n,
                     int timeout) {
  assert(n == 64);

  if (device->dev != NULL)
    return hid_read_timeout(device->dev, dst, n, timeout);

  struct {
    uint32_t cmd;
    uint32_t len;
  } data;

  static_assert(sizeof(data) == 8);

  data.cmd = htole32(5);  // k64ByteRead
  data.len = htole32(0);

  uint64_t t0, t1;
  float dt;
  U2Fob_deltaTime(&t0);

  // Poll until timeout
  do {
    assert(write(device->fd_out, (uint8_t*)&data, sizeof(data)) ==
           sizeof(data));
    assert(read(device->fd_in, (uint8_t*)&data, sizeof(data)) == sizeof(data));

    assert(data.cmd == htole32(5));
    if (data.len == htole32(64)) break;

    assert(data.len == 0);

    usleep(100);

    t1 = t0;
    dt = U2Fob_deltaTime(&t1);
  } while (dt < timeout / 1000.0);

  if (data.len == 0) return 0;

  assert(data.len == htole32(64));
  assert(read(device->fd_in, dst, 64) == 64);
  return 64;
}

int DEV_touch(struct U2Fob* device) {
  if (device->dev != NULL) return 0;

  struct {
    uint32_t cmd;
    uint32_t len;
    uint32_t number;
  } data;

  static_assert(sizeof(data) == 12);

  data.cmd = htole32(6);  // kRaiseInterrupt
  data.len = htole32(sizeof(uint32_t));
  data.number = htole32(199);  // touch toggle handler

  assert(write(device->fd_out, (uint8_t*)&data, sizeof(data)) == sizeof(data));
  return 1;
}
