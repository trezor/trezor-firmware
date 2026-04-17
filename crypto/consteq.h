#ifndef __CONSTEQ_H__
#define __CONSTEQ_H__

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool consteq(const uint8_t *sec, size_t seclen, const uint8_t *pub,
             size_t publen);
#endif
