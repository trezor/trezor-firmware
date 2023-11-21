#include "secure_api.h"

#include STM32_HAL_H

// When returning from or calling a callback from Secure to Non-Secure,
// all registers (r0-15, s0-31) are overwritten by constants, except
// for those that contain important information.

__attribute__((cmse_nonsecure_entry)) int secure_get_secret() {
  return 987654321;
}

__attribute__((cmse_nonsecure_entry)) void secure_enumerate_secrets(
    secure_enum_callback_t callback, void* callback_context) {
  for (int i = 0; i < 5; i++) {
    callback(callback_context, i);
  }
}

typedef __attribute__((cmse_nonsecure_call)) secure_callback_t ns_secure_callback_t;

__attribute__((cmse_nonsecure_entry)) void secure_another_func(
    secure_callback_t callback, void* callback_context) {

  // make non-secure callback from normal function ptr
  ns_secure_callback_t ns_callback = (ns_secure_callback_t) cmse_nsfptr_create(callback);

  ns_callback(callback_context);
}


static inline const void * cmse_check_inbuff(const void * ptr, size_t size) {
  return cmse_check_address_range((void *)ptr, size, CMSE_MPU_READ | CMSE_MPU_NONSECURE | CMSE_AU_NONSECURE);
}

static inline void * cmse_check_outbuff( void * ptr, size_t size) {
  return cmse_check_address_range(ptr, size, CMSE_MPU_READWRITE | CMSE_MPU_NONSECURE | CMSE_AU_NONSECURE);
}


__attribute__((cmse_nonsecure_entry))
int secure_process_buff(const uint8_t * in_ptr, size_t in_size,
                           uint8_t * out_ptr, size_t out_size) {

  if (! cmse_check_inbuff(in_ptr, in_size)) {
    return -1;
  }

  if (! cmse_check_outbuff(out_ptr, out_size)) {
    return -2;
  }

  return 0;
}



