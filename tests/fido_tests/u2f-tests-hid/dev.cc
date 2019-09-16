// Copyright Google Inc. All rights reserved.
//
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file or at
// https://developers.google.com/open-source/licenses/bsd

// Thin shim to allow abstracting away from hid_* calls to
// a set or read/write pipes w/ a particular interface.
#include <assert.h>
#include "u2f_util.h"

bool DEV_opened(struct U2Fob* device) {
  return device->dev != NULL;
}

void DEV_close(struct U2Fob* device) {
  if (device->dev) {
    hid_close(device->dev);
    device->dev = NULL;
  }
  if (device->dev_debug) {
    hid_close(device->dev_debug);
    device->dev_debug = NULL;
  }
}

void DEV_open_path(struct U2Fob* device) {
  device->dev = hid_open_path(device->path);
  if (atoi(device->path) != 21325) {
    device->dev_debug = hid_open_path("21325");
  } else {
    device->dev_debug = NULL;
  }
}

int DEV_write(struct U2Fob* device, const uint8_t* src, size_t n) {
  assert(n == 65);
  return hid_write(device->dev, src, n);
}

int DEV_read_timeout(struct U2Fob* device, uint8_t* dst, size_t n,
                     int timeout) {
  assert(n == 64);
  return hid_read_timeout(device->dev, dst, n, timeout);
}

int DEV_touch(struct U2Fob* device) {
  if (!device->dev_debug) {
    return 0;
  }
  sleep(1);
  // send DebugLinkDecision{yes_no=True} to DebugLink interface
  hid_write(device->dev_debug, (const uint8_t *)"\x00?##\x00" "d\x00\x00\x00\x02\x08\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 65);
  sleep(1);
  return 1;
}
