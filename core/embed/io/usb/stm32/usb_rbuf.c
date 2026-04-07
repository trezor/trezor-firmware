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

#include <trezor_rtl.h>

#include <sys/irq.h>

#include "usb_rbuf.h"

void usb_rbuf_init(usb_rbuf_t *b, uint8_t *buf, size_t buf_size) {
  b->buf = buf;
  b->cap = buf_size;
  b->used = 0;
  b->rptr = b->buf;
  b->wptr = b->buf;
}

void usb_rbuf_reset(usb_rbuf_t *b) {
  irq_key_t irq_key = irq_lock();
  b->used = 0;
  b->rptr = b->buf;
  b->wptr = b->buf;
  irq_unlock(irq_key);
}

size_t usb_rbuf_used_bytes(usb_rbuf_t *b) {
  irq_key_t irq_key = irq_lock();
  size_t size = b->used;
  irq_unlock(irq_key);
  return size;
}

size_t usb_rbuf_unused_bytes(usb_rbuf_t *b) {
  irq_key_t irq_key = irq_lock();
  size_t size = b->cap - b->used;
  irq_unlock(irq_key);
  return size;
}

bool usb_rbuf_is_empty(usb_rbuf_t *b) { return usb_rbuf_used_bytes(b) == 0; }

bool usb_rbuf_is_full(usb_rbuf_t *b) { return usb_rbuf_unused_bytes(b) == 0; }

size_t usb_rbuf_read(usb_rbuf_t *b, uint8_t *buf, size_t buf_size) {
  irq_key_t irq_key = irq_lock();
  size_t to_read = MIN(buf_size, b->used);
  size_t first_part = MIN(to_read, b->cap - (b->rptr - b->buf));
  memcpy(buf, b->rptr, first_part);
  size_t second_part = to_read - first_part;
  memcpy(buf + first_part, b->buf, second_part);
  b->rptr += first_part;
  if (b->rptr == b->buf + b->cap) {
    b->rptr = b->buf + second_part;
  }
  b->used -= to_read;
  irq_unlock(irq_key);
  return to_read;
}

size_t usb_rbuf_write(usb_rbuf_t *b, const uint8_t *data, size_t data_size) {
  irq_key_t irq_key = irq_lock();
  size_t to_write = MIN(data_size, b->cap - b->used);
  size_t first_part = MIN(to_write, b->cap - (b->wptr - b->buf));
  memcpy(b->wptr, data, first_part);
  size_t second_part = to_write - first_part;
  memcpy(b->buf, data + first_part, second_part);
  b->wptr += first_part;
  if (b->wptr == b->buf + b->cap) {
    b->wptr = b->buf + second_part;
  }
  b->used += to_write;
  irq_unlock(irq_key);
  return to_write;
}
