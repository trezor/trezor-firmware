cmake_minimum_required(VERSION 2.6)

set(SOURCES aescrypt.c aeskey.c aes_modes.c aestab.c base58.c bignum.c bip32.c bip39.c ecdsa.c hmac.c nist256p1.c pbkdf2.c rand.c ripemd160.c secp256k1.c sha2.c)

# disable sequence point warnings where they are expected
set_source_files_properties(aeskey.c PROPERTIES
                            COMPILE_FLAGS -Wno-sequence-point)

if(MSVC)
  set_source_files_properties(${SOURCES} PROPERTIES LANGUAGE CXX)
endif(MSVC)

add_library(TrezorCrypto STATIC ${SOURCES})

# Build trezor-crypto tests (requires OpenSSL)
if (TREZOR_CRYPTO_TESTS)
    add_executable(tests tests.c)
    target_link_libraries(tests TrezorCrypto check rt pthread m crypto)
    add_test(NAME trezor-crypto COMMAND tests)

    add_executable(test-openssl test-openssl.c)
    target_link_libraries(test-openssl TrezorCrypto check rt pthread m crypto)
    add_test(NAME trezor-crypto-openssl COMMAND test-openssl 100)
endif()