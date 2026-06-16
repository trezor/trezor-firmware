/* Trezor randombytes shim for SPHINCS+ reference code.
 *
 * The upstream randombytes.c reads /dev/urandom via POSIX open/read/sleep,
 * which doesn't link on the embedded firmware target. SPHINCS+ here is only
 * used through *_seed_keypair (deterministic from the wallet seed), so this
 * function is currently never called at runtime — but the symbol must still
 * resolve. Route it through Trezor's vetted RNG to be safe if that changes.
 *
 * Each variant wrapper has `#define randombytes spx_<variant>_randombytes`,
 * so this defines a unique symbol per translation unit.
 */
#include "../rand.h"
#include "randombytes.h"

void randombytes(unsigned char *x, unsigned long long xlen) {
    random_buffer((uint8_t *)x, (size_t)xlen);
}
