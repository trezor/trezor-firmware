#ifndef SECURE_API_H
#define SECURE_API_H

#include <stdint.h>
#include <stddef.h>


#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
#define CMSE_NONSECURE_CALL __attribute__((cmse_nonsecure_call))
#else
#define CMSE_NONSECURE_CALL
#endif

int secure_get_secret(void);

typedef void (*secure_enum_callback_t)(void* context,
                                       int secret) CMSE_NONSECURE_CALL;

void secure_enumerate_secrets(secure_enum_callback_t callback,
                              void* callback_context);


typedef void (*secure_callback_t)(void * context);

void secure_another_function(secure_callback_t * callback, void * context);


int secure_process_buff(const uint8_t * in_ptr, size_t in_size,
                           uint8_t * out_ptr, size_t out_size);


#endif  // SECURE_API_H
