#include "options.h"

#if !OPTIMIZE_SIZE_ED25519
/* multiples of the base point in packed {ysubx, xaddy, t2d} form */
extern const uint8_t ALIGN(16) ge25519_niels_base_multiples[256][96];
#endif
