#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include "aes.h"

#include <stm32u5xx_hal_cryp.h>
#include <stm32u5xx_hal_cryp_ex.h>

#ifdef KERNEL_MODE
static CRYP_HandleTypeDef hcryp = {0};

uint32_t g_key[32 / 4] = {0};

int hwgcm_init_and_key(/* initialise mode and set key  */
                       const unsigned char key[], unsigned long key_len) {
  __HAL_RCC_AES_CLK_ENABLE();

  hcryp.Instance = AES;
  hcryp.Init.Algorithm = CRYP_AES_GCM_GMAC;
  hcryp.Init.DataType = CRYP_DATATYPE_8B;
  hcryp.Init.DataWidthUnit = CRYP_DATAWIDTHUNIT_BYTE;
  hcryp.Init.HeaderWidthUnit = CRYP_HEADERWIDTHUNIT_BYTE;
  hcryp.Init.KeyMode = CRYP_KEYMODE_NORMAL;
  hcryp.Init.KeySelect = CRYP_KEYSEL_SW;
  hcryp.Init.pKey = g_key;
  hcryp.Init.KeyIVConfigSkip = CRYP_KEYIVCONFIG_ONCE;

  switch (key_len) {
    case 16:
      hcryp.Init.KeySize = CRYP_KEYSIZE_128B;
      memcpy(g_key, key, 16);
      break;
    case 32:
      hcryp.Init.KeySize = CRYP_KEYSIZE_256B;
      memcpy(g_key, key, 32);
      break;
    default:
      return -1;
  }

  HAL_CRYP_Init(&hcryp);

  return 0;
}

int hwgcm_end(void) { return 0; }

int hwgcm_init_message(/* initialise a new message     */
                       const unsigned char iv[], /* the initialisation vector */
                       unsigned long iv_len) {
  hcryp.Init.pInitVect = (uint32_t*)iv;
  return 0;
}

int hwgcm_auth_header(/* authenticate the header      */
                      const unsigned char hdr[], /* the header buffer */
                      unsigned long hdr_len) {
  hcryp.Init.Header = (uint32_t*)hdr;
  hcryp.Init.HeaderSize = hdr_len;
  return 0;
}

int hwgcm_encrypt(                      /* encrypt & authenticate data  */
                  unsigned char data[], /* the data buffer              */
                  unsigned long data_len) {
  HAL_CRYP_Encrypt(&hcryp, (uint32_t*)data, data_len, (uint32_t*)data,
                   HAL_MAX_DELAY);
  return 0;
}

int hwgcm_decrypt(                      /* authenticate & decrypt data  */
                  unsigned char data[], /* the data buffer              */
                  unsigned long data_len) {
  HAL_CRYP_Decrypt(&hcryp, (uint32_t*)data, data_len, (uint32_t*)data,
                   HAL_MAX_DELAY);
  return 0;
}

int hwgcm_compute_tag(                     /* compute authentication tag   */
                      unsigned char tag[], /* the buffer for the tag       */
                      unsigned long tag_len) {
  HAL_CRYPEx_AESGCM_GenerateAuthTAG(&hcryp, (uint32_t*)tag, HAL_MAX_DELAY);
  return 0;
}

// ret_type gcm_auth_data(/* authenticate ciphertext data */
//                        const unsigned char data[], /* the data buffer */
//                        unsigned long data_len, /* and its length in bytes */
//                        hw_aes_ctx ctx[1]) {
//   return 0;
// }
//
// ret_type gcm_crypt_data(                      /* encrypt or decrypt data */
//                         unsigned char data[], /* the data buffer */ unsigned
//                         long data_len, /* and its length in bytes */
//                         hw_aes_ctx ctx[1]) {
//   return 0;
// }

#endif
