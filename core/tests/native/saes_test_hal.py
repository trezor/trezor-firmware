"""ECB-only SAES HAL model shared by native driver tests."""

HAL_MODEL = r"""#include <trezor_bsp.h>
#include <stdio.h>
#include "aes/aes.h"
#include "aes/aesgcm.h"
#include "driver_under_test.c"
AES_TypeDef fake_saes;
static uint32_t loaded_key[8];
static bool decrypt_prepared;
static uint8_t test_key[32];
static unsigned blocks, fail_at, resets, reset_failure_at;
static bool distinct_rng;
int HAL_CRYP_Init(CRYP_HandleTypeDef*h){fake_saes.SR=AES_SR_KEYVALID;return HAL_OK;}
uint32_t ticks_timeout(uint32_t n){return n;}
bool ticks_expired(uint32_t n){return false;}
secbool secure_aes_init(void){
 memset(loaded_key,0,sizeof(loaded_key));
 return ++resets==reset_failure_at ? secfalse : sectrue;
}
void rng_fill_buffer_strong(void*p,size_t n){
 static uint32_t generation; ++generation; assert(n==32);uint32_t*words=p;
 for(unsigned i=0;i<8;i++){
  uint32_t little;memcpy(&little,test_key+4*i,4);words[i]=__builtin_bswap32(little)^(distinct_rng ? generation : 0);
 }
}
int HAL_CRYPEx_WrapKey(CRYP_HandleTypeDef*h,uint32_t*in,uint32_t*out,uint32_t t){
 memcpy(out,in,32);return HAL_OK;
}
int HAL_CRYPEx_UnwrapKey(CRYP_HandleTypeDef*h,uint32_t*in,uint32_t t){
 memcpy(loaded_key,in,32);decrypt_prepared=false;return HAL_OK;
}
int HAL_CRYP_GetConfig(CRYP_HandleTypeDef*h,CRYP_ConfigTypeDef*c){*c=h->Init;return HAL_OK;}
int HAL_CRYP_SetConfig(CRYP_HandleTypeDef*h,CRYP_ConfigTypeDef*c){
 /* Model the U5 SAES capability, not the more capable regular AES engine. */
 if(c->Algorithm!=CRYP_AES_ECB)return HAL_ERROR;
 assert(c->KeyMode==CRYP_KEYMODE_NORMAL && c->KeySelect==CRYP_KEYSEL_NORMAL && !c->pKey);
 h->Init=*c;return HAL_OK;
}

static int block_cipher(uint32_t *in, uint32_t n, uint32_t *out, bool encrypt){
 assert(n && n<=160 && n%16==0);
 if(++blocks==fail_at)return HAL_ERROR;
 uint8_t key[32], input[160], output[160];
 for(unsigned i=0;i<8;i++)saes_put_be32(key+4*i,loaded_key[i]);
 for(unsigned i=0;i<n/4;i++)saes_put_be32(input+4*i,in[i]);
 if(encrypt){
  aes_encrypt_ctx ctx;assert(!aes_encrypt_key256(key,&ctx));
  for(unsigned i=0;i<n;i+=16)assert(!aes_encrypt(input+i,output+i,&ctx));
  memzero(&ctx,sizeof(ctx));
 }else{
  assert(!decrypt_prepared);decrypt_prepared=true;
  aes_decrypt_ctx ctx;assert(!aes_decrypt_key256(key,&ctx));
  for(unsigned i=0;i<n;i+=16)assert(!aes_decrypt(input+i,output+i,&ctx));
  memzero(&ctx,sizeof(ctx));
 }
 for(unsigned i=0;i<n/4;i++)out[i]=saes_be32(output+4*i);
 memzero(key,sizeof(key));memzero(input,sizeof(input));memzero(output,sizeof(output));
 return HAL_OK;
}
int HAL_CRYP_Encrypt(CRYP_HandleTypeDef*h,uint32_t*i,uint32_t n,uint32_t*o,uint32_t t){
 assert(h->Init.Algorithm==CRYP_AES_ECB);return block_cipher(i,n,o,true);
}
int HAL_CRYP_Decrypt(CRYP_HandleTypeDef*h,uint32_t*i,uint32_t n,uint32_t*o,uint32_t t){
 assert(h->Init.Algorithm==CRYP_AES_ECB);return block_cipher(i,n,o,false);
}

#include <stdlib.h>
void __attribute__((noreturn)) system_exit_error(const char *title,const char *message,const char *footer){abort();}
"""
