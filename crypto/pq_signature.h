#ifndef __PQ_SIGNATURE_H__
#define __PQ_SIGNATURE_H__

#define CONCATENATE_1(x, y) x##_##y
#define CONCATENATE(x, y) CONCATENATE_1(x, y)

#define ADD_PQ_SIGNATURE_PREFIX(function_name) \
  CONCATENATE(PQ_SIGNATURE_PREFIX, function_name)

#define crypto_sign_keypair ADD_PQ_SIGNATURE_PREFIX(crypto_sign_keypair)
#define crypto_sign ADD_PQ_SIGNATURE_PREFIX(crypto_sign)
#define crypto_sign_signature ADD_PQ_SIGNATURE_PREFIX(crypto_sign_signature)
#define crypto_sign_open ADD_PQ_SIGNATURE_PREFIX(crypto_sign_open)
#define crypto_sign_verify ADD_PQ_SIGNATURE_PREFIX(crypto_sign_verify)
#define CRYPTO_PUBLICKEYBYTES ADD_PQ_SIGNATURE_PREFIX(CRYPTO_PUBLICKEYBYTES)
#define CRYPTO_SECRETKEYBYTES ADD_PQ_SIGNATURE_PREFIX(CRYPTO_SECRETKEYBYTES)
#define CRYPTO_BYTES ADD_PQ_SIGNATURE_PREFIX(CRYPTO_BYTES)

#endif
