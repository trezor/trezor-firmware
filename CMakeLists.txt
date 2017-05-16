cmake_minimum_required(VERSION 2.8)

set(SOURCES address.c aes/aescrypt.c aes/aeskey.c aes/aes_modes.c aes/aestab.c base32.c base58.c bignum.c bip32.c bip39.c ecdsa.c hmac.c nist256p1.c pbkdf2.c rand.c ripemd160.c secp256k1.c sha2.c sha3.c ed25519-donna/ed25519.c ed25519-donna/ed25519-sha3.c ed25519-donna/ed25519-keccak.c)

add_library(TrezorCrypto STATIC ${SOURCES})

target_include_directories(TrezorCrypto PUBLIC .)
target_include_directories(TrezorCrypto PUBLIC ed25519-donna)

# disable sequence point warnings where they are expected
set_source_files_properties(aeskey.c PROPERTIES
                            COMPILE_FLAGS -Wno-sequence-point)

target_compile_options(TrezorCrypto PRIVATE "-std=c99")

if(MSVC)
  set_source_files_properties(${SOURCES} PROPERTIES LANGUAGE CXX)
endif(MSVC)

# Build trezor-crypto tests (requires OpenSSL)
if (TREZOR_CRYPTO_TESTS)
    add_executable(test_check test_check.c)
    target_link_libraries(test_check TrezorCrypto check rt pthread m crypto)
    add_test(NAME trezor-crypto COMMAND test_check)

    add_executable(test_openssl test_openssl.c)
    target_link_libraries(test_openssl TrezorCrypto check rt pthread m crypto)
    add_test(NAME trezor-crypto-openssl COMMAND test_openssl 100)
endif()
