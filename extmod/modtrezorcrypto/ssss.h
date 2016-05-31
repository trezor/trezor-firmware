#ifndef __SSSS_H__
#define __SSSS_H__

#include <stdbool.h>
#include "bignum.h"

bool ssss_split(const bignum256 *secret, int m, int n, bignum256 *shares);
bool ssss_combine(const bignum256 *shares, int n, bignum256 *secret);

#endif
