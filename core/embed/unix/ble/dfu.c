//
//  main.c
//  nrf52-dfu
//
//  Sample host application to demonstrate the usage of our C library for the
//  Nordic firmware update protocol.
//
//  Created by Andreas Schweizer on 30.11.2018.
//  Copyright © 2018-2019 Classy Code GmbH
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
//

#include "dfu.h"
#include <stdint.h>

static uint32_t binsize = 0;
static uint32_t uploaded_total = 0;

void dfu_init(void) {}

dfu_result_t dfu_update_init(uint8_t *data, uint32_t len, uint32_t binary_len) {
  binsize = binary_len;
  uploaded_total = 0;
  return DFU_NEXT_CHUNK;
}

dfu_result_t dfu_update_chunk(uint8_t *data, uint32_t len) {
  uploaded_total += len;
  if (uploaded_total >= binsize) {
    return DFU_SUCCESS;
  } else {
    return DFU_NEXT_CHUNK;
  }
}

dfu_result_t dfu_update_do(uint8_t *datfile, uint32_t datfile_len,
                           uint8_t *binfile, uint32_t binfile_len) {
  return DFU_SUCCESS;
}
