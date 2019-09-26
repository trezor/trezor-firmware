#ifndef __BEAM_MISC__
#define __BEAM_MISC__

#include "definitions.h"
#include "kernel.h"
#include "rangeproof.h"

#define ANSI_COLOR_RED "\x1b[31m"
#define ANSI_COLOR_GREEN "\x1b[32m"
#define ANSI_COLOR_YELLOW "\x1b[33m"
#define ANSI_COLOR_BLUE "\x1b[34m"
#define ANSI_COLOR_MAGENTA "\x1b[35m"
#define ANSI_COLOR_CYAN "\x1b[36m"
#define ANSI_COLOR_RESET "\x1b[0m"

#define DEBUG_PRINT(msg, arr, len)                                         \
  printf(ANSI_COLOR_CYAN "Line=%u" ANSI_COLOR_RESET ", Msg=%s ", __LINE__, \
         msg);                                                             \
  printf(ANSI_COLOR_YELLOW);                                               \
  for (size_t i = 0; i < len; i++) {                                       \
    printf("%02x", arr[i]);                                                \
  }                                                                        \
  printf(ANSI_COLOR_RESET "\n");

#define CMP_SIMPLE(a, b) \
  if (a < b) return -1;  \
  if (a > b) return 1;

#define CMP_BY_FUN(a, b, cmp_fun)      \
  {                                    \
    const int cmp_res = cmp_fun(a, b); \
    if (cmp_res != 0) return cmp_res;  \
  }

#define CMP_MEMBER(member, other_member) CMP_SIMPLE(member, other_member)

#define CMP_PTRS(a, b, cmp_fun) \
  if (a) {                      \
    if (!b) return 1;           \
    int n = cmp_fun(a, b);      \
    if (n) return n;            \
  } else if (b)                 \
    return -1;

void test_set_buffer(void* data, uint32_t size, uint8_t value);

void transaction_init(transaction_t* transaction);
void transaction_free(transaction_t* transaction);
void transaction_free_outputs(tx_outputs_vec_t* outputs);
void signature_init(ecc_signature_t* signature);
void point_init(point_t* point);
void key_idv_init(key_idv_t* kidv);
void packed_key_id_init(packed_key_id_t* kid);
void tx_element_init(tx_element_t* tx_element);
void tx_input_init(tx_input_t* input);
void tx_output_init(tx_output_t* output);
void tx_output_free(tx_output_t* output);
void kernel_init(tx_kernel_t* kernel);
void HKdf_init(HKdf_t* kdf);

int bigint_cmp(const uint8_t* pSrc0, uint32_t nSrc0, const uint8_t* pSrc1,
               uint32_t nSrc1);
int point_cmp(const point_t* lhs, const point_t* rhs);
int tx_element_cmp(const tx_element_t* lhs, const tx_element_t* rhs);
int signature_cmp(const ecc_signature_t* lhs, const ecc_signature_t* rhs);
int kernel_cmp(const tx_kernel_t* lhs, const tx_kernel_t* rhs);

void get_seed_kid_from_commitment(const point_t* commitment, uint8_t* seed,
                                  const HKdf_t* kdf);

#endif  // __BEAM_MISC__
