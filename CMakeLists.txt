cmake_minimum_required(VERSION 2.6)

set(SOURCES aescrypt.c aeskey.c aes_modes.c aestab.c base58.c bignum.c bip32.c bip39.c ecdsa.c hmac.c pbkdf2.c rand.c ripemd160.c secp256k1.c sha2.c)
if(MSVC)
  set_source_files_properties(${SOURCES} PROPERTIES LANGUAGE CXX)
endif(MSVC)
add_library(TrezorCrypto STATIC ${SOURCES})

# disable sequence point warning because of AES code
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wno-sequence-point")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-sequence-point")
add_executable(tests tests.c)
target_link_libraries(tests TrezorCrypto check rt pthread m crypto)
add_test(NAME trezor-crypto COMMAND tests)

add_executable(test-openssl test-openssl.c)
target_link_libraries(test-openssl TrezorCrypto check rt pthread m crypto)
add_test(NAME trezor-crypto-openssl COMMAND test-openssl 100)
