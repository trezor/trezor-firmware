#include "ed25519-donna/ed25519.h"
#include "libtropic.h"
#include "libtropic_common.h"
#include "lt_l2.h"
#include <stdio.h>

// Model
uint8_t trezor_privkey[] = {0xf0, 0xc4, 0xaa, 0x04, 0x8f, 0x00, 0x13, 0xa0,
                            0x96, 0x84, 0xdf, 0x05, 0xe8, 0xa2, 0x2e, 0xf7,
                            0x21, 0x38, 0x98, 0x28, 0x2b, 0xa9, 0x43, 0x12,
                            0xf3, 0x13, 0xdf, 0x2d, 0xce, 0x8d, 0x41, 0x64};
// Physical
// uint8_t trezor_privkey[] ={0xd0,0x99,0x92,0xb1,0xf1,0x7a,0xbc,0x4d,0xb9,0x37,0x17,0x68,0xa2,0x7d,0xa0,0x5b,0x18,0xfa,0xb8,0x56,0x13,0xa7,0x84,0x2c,0xa6,0x4c,0x79,0x10,0xf2,0x2e,0x71,0x6b};

// uint8_t tropic_pubkey[] = {0x31, 0xE9, 0x0A, 0xF1, 0x50, 0x45, 0x10, 0xEE,
//                            0x4E, 0xFD, 0x79, 0x13, 0x33, 0x41, 0x48, 0x15,
//                            0x89, 0xA2, 0x89, 0x5C, 0xC5, 0xFB, 0xB1, 0x3E,
//                            0xD5, 0x71, 0x1C, 0x1E, 0x9B, 0x81, 0x98, 0x72};


// Trezor 20
// uint8_t tropic_pubkey[] = {0xB9, 0x21, 0xD3, 0x58, 0x9F, 0x96, 0x34, 0x7A, 0x1A, 0x05, 0x5A, 0x10, 0x98, 0xAC, 0xCA, 0xAD, 0xDF, 0xE4, 0xA9, 0x3B, 0x1E, 0xA2, 0x12, 0x4A, 0x9D, 0x9B, 0xFE, 0xB8, 0xA8, 0x2E, 0x4D, 0x0D};

// uint8_t tropic_pubkey[] = {
//     0xE3, 0xCA, 0x81, 0x6E, 0x81, 0x37, 0xD7, 0x18,
//     0xA2, 0x30, 0xFB, 0x67, 0x1F, 0xA7, 0x90, 0xCA,
//     0x8E, 0x44, 0x37, 0x7C, 0x74, 0xFF, 0x68, 0xBE,
//     0x9A, 0x7A, 0xDF, 0xBF, 0x4D, 0xB9, 0xB5, 0x53
// };

// Model
  uint8_t tropic_pubkey[] = {
          0x31, 0xE9, 0x0A, 0xF1, 0x50, 0x45, 0x10, 0xEE,
          0x4E, 0xFD, 0x79, 0x13, 0x33, 0x41, 0x48, 0x15,
          0x89, 0xA2, 0x89, 0x5C, 0xC5, 0xFB, 0xB1, 0x3E,
          0xD5, 0x71, 0x1C, 0x1E, 0x9B, 0x81, 0x98, 0x72
      };

#include "libtropic.h"
#include "ed25519-donna/ed25519.h"
#include "lt_aesgcm.h"
#include "lt_x25519.h"
#include "lt_sha256.h"
#include "lt_hkdf.h"
#include "lt_l3_api_structs.h"
#include "lt_l3.h"
#include "lt_l2_api_structs.h"
#include "stdint.h"
#include "stdbool.h"
#include "rand.h"
#define NONCE_SIZE 12
#define KEY_SIZE 32

#define L3_R_MEM_DATA_WRITE_WRITE_FAIL      0x10u


lt_ret_t lt_l2_transfer(lt_handle_t *h);
lt_ret_t lt_l2_read(lt_handle_t *h, uint8_t *data, size_t data_max_length, size_t *data_length);
lt_ret_t lt_l2_write(lt_handle_t *h, const uint8_t *data, size_t data_length);
lt_ret_t lt_l3_read(lt_handle_t *h, uint8_t *data, size_t data_max_length, size_t *data_length);
void send_data(uint8_t *data, size_t data_length);
void receive_data(uint8_t *data, size_t data_max_length, size_t *data_length);
lt_ret_t lt_l3_write(lt_handle_t *h, const uint8_t *data, size_t max_data_length, size_t *data_length);

void request_data(uint8_t *input, size_t input_length, uint8_t *output, size_t *output_length);

int main() {
    lt_handle_t ctx = {0};
    session_state_t handshake_ctx = {0};

    lt_ret_t ret = LT_OK;

    uint8_t buffer[10000] = {0};
    size_t length = 0;


    ret = lt_out__session_start(&ctx, PAIRING_KEY_SLOT_INDEX_0, &handshake_ctx);
    if (ret != LT_OK) {
        printf("Error creating handshake request: %d\n", ret);
        return ret;
    }

    lt_l2_read(&ctx, buffer, sizeof(buffer), &length);
    send_data(buffer, length);

    receive_data(buffer, sizeof(buffer), &length);
    lt_l2_write(&ctx, buffer, length);

    uint8_t trezor_pubkey[KEY_SIZE] = {0};
    lt_X25519_scalarmult(trezor_privkey, trezor_pubkey);
    ret = lt_in__session_start(&ctx, tropic_pubkey, PAIRING_KEY_SLOT_INDEX_0, trezor_privkey, trezor_pubkey, &handshake_ctx);
    if (ret != LT_OK) {
        printf("Error handling handshake response: %d\n", ret);
        return ret;
    }
    printf("Handshake successful\n");

    ret = lt_out__ecc_key_erase(&ctx, ECC_SLOT_0);
    if (ret != LT_OK) {
        printf("Error creating ECC key erase request: %d\n", ret);
        return ret;
    }
    lt_l3_read(&ctx, buffer, sizeof(buffer), &length);
    send_data(buffer, length);

    ret = lt_out__ecc_key_generate(&ctx, ECC_SLOT_0, CURVE_P256);
    if (ret != LT_OK) {
        printf("Error creating ECC key generate request: %d\n", ret);
        return ret;
    }
    lt_l3_read(&ctx, buffer, sizeof(buffer), &length);
    send_data(buffer, length);

    ret = lt_out__ecc_key_read(&ctx, ECC_SLOT_0);
    if (ret != LT_OK) {
        printf("Error creating ECC key read request: %d\n", ret);
        return ret;
    }
    lt_l3_read(&ctx, buffer, sizeof(buffer), &length);
    send_data(buffer, length);

    ret = lt_out__ecc_key_erase(&ctx, ECC_SLOT_1);
    if (ret != LT_OK) {
        printf("Error creating ECC key erase request: %d\n", ret);
        return ret;
    }
    lt_l3_read(&ctx, buffer, sizeof(buffer), &length);
    send_data(buffer, length);

    uint8_t private_key[32] = {1};
    ret = lt_out__ecc_key_store(&ctx, ECC_SLOT_1, CURVE_P256, private_key);
    if (ret != LT_OK) {
        printf("Error creating ECC key store request: %d\n", ret);
        return ret;
    }
    lt_l3_read(&ctx, buffer, sizeof(buffer), &length);
    send_data(buffer, length);

    // **************

    receive_data(buffer, sizeof(buffer), &length);
    lt_l3_write(&ctx, buffer, sizeof(buffer), &length);
    ret = lt_in__ecc_key_erase(&ctx);
    if (ret != LT_OK) {
        printf("Error handling first ECC key erase response: %d\n", ret);
        return ret;
    }

    receive_data(buffer, sizeof(buffer), &length);
    lt_l3_write(&ctx, buffer, sizeof(buffer), &length);
    ret = lt_in__ecc_key_generate(&ctx);
    if ( ret != LT_OK) {
        printf("Error handling ECC key generate response: %d\n", ret);
        return ret;
    }

    receive_data(buffer, sizeof(buffer), &length);
    lt_l3_write(&ctx, buffer, sizeof(buffer), &length);
    uint8_t public_key[64] = {0};
    size_t key_length = sizeof(public_key);
    lt_ecc_curve_type_t curve;
    ecc_key_origin_t origin;
    ret = lt_in__ecc_key_read(&ctx, public_key, key_length, &curve, &origin);
    if (ret != LT_OK) {
        printf("Error handling ECC key read response: %d\n", ret);
        return ret;
    }
    printf("Public key: ");
    for (size_t i = 0; i < key_length; i++) {
        printf("%02x", public_key[i]);
    }
    printf("\n");

    receive_data(buffer, sizeof(buffer), &length);
    lt_l3_write(&ctx, buffer, sizeof(buffer), &length);
    ret = lt_in__ecc_key_erase(&ctx);
    if (ret != LT_OK) {
        printf("Error handling second ECC key erase response: %d\n", ret);
        return ret;
    }

    receive_data(buffer, sizeof(buffer), &length);
    lt_l3_write(&ctx, buffer, sizeof(buffer), &length);
    ret = lt_in__ecc_key_store(&ctx);
    if ( ret != LT_OK) {
        printf("Error handling ECC key store response: %d\n", ret);
        return ret;
    }
}
