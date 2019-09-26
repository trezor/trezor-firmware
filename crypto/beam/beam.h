#ifndef __TREZOR_CRYPTO_BEAM_H__
#define __TREZOR_CRYPTO_BEAM_H__

#if !USE_BEAM
#error "Compile with -DUSE_BEAM=1"
#endif

int test_tx_kernel(void);

// __TREZOR_CRYPTO_BEAM_H__
#endif
