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

#include "alloc_only.h"
#include "common.h"
#include "memzero.h"

extern uint32_t _heap_start;
extern uint32_t _heap_end;

uint32_t * alloc_memory;

void * alloc_only(uint16_t size){

  void * ptr = NULL;

  size_t aligned_size = size;
  if (size % 4 != 0) {
    aligned_size++;
  }

  if((alloc_memory + aligned_size) <= &_heap_end){
    ptr = alloc_memory;
    alloc_memory += aligned_size;
  }

  return ptr;
}

void alloc_only_init(bool clear) {
  alloc_memory = &_heap_start;


  if (clear) {
    size_t len = (&_heap_end - &_heap_start);
    memzero(alloc_memory, len);
  }
}
